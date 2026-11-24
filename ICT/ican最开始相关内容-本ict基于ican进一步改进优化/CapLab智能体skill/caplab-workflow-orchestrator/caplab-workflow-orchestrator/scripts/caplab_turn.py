#!/usr/bin/env python3
"""Persist receive -> resolve turns, without modifying the five-stage state.

Use the SAME isolated workspace/session ledger for begin and finish. begin saves
receipts before generation; finish is the sole validated response-file outlet.
"""
from __future__ import annotations
import argparse
import copy
import json
import re
from pathlib import Path
from caplab_state import atomic_json, state_lock
from caplab_guards import language_errors

FIELDS = ('task', 'deliverable', 'acceptance_criteria', 'time_budget', 'failure_adjustment')
TIRED = re.compile(r'我累了|今天到这|先到这里|不聊了|先休息')
ACCEPT = re.compile(r'可以|同意|就这样|好[的啊]?|愿意|试试')
PLAN = re.compile(r'行动计划|两周任务|具体做什么|怎么算完成|安排.*任务|制定.*计划')


def empty():
    return {'schema_version': '1.0.0', 'revision': 0, 'turns': [], 'commitments': [], 'proposals': [], 'commitment_open': False}


def refresh(state):
    state['commitment_open'] = any(c['status'] in {'open', 'deferred'} for c in state['commitments'])


def begin(state, user_text, extra_intents=()):
    state = copy.deepcopy(state)
    # Unfinished prior turns cannot disappear when interrupted by a new message.
    for turn in state['turns']:
        for receipt in turn['received_intents']:
            if receipt['id'] not in turn['handled_intents'] and receipt['id'] not in turn['deferred_intents']:
                turn['deferred_intents'][receipt['id']] = '上一轮中断，下次继续'
    n = len(state['turns']) + 1
    # Clause receipts are conservative coverage, not a claim of perfect NLU.
    clauses = [v.strip() for v in re.split(r'[，,。；;\n]|(?:然后|再把|同时)', user_text) if v.strip()]
    clauses += [v for v in extra_intents if v not in clauses]
    turn = {'id': f'TURN-{n:06}', 'received_intents': [{'id': f'INT-{n:06}-{i}', 'text': text} for i, text in enumerate(clauses)],
            'handled_intents': {}, 'deferred_intents': {}, 'status': 'received'}
    tired = bool(TIRED.search(user_text))
    if tired:
        turn['deferred_intents'] = {r['id']: '用户暂停，下次继续' for r in turn['received_intents']}
        for c in state['commitments']:
            if c['status'] == 'open':
                c.update(status='deferred', reason='用户暂停，下次继续')
    else:
        accepted = [p for p in state['proposals'] if p['status'] == 'proposed'] if re.match(r'^(可以|同意|好[的啊]?|愿意|试试|就这样)(?:[，,。！!\s]|$)', user_text.strip()) else []
        accepted = accepted if '都' in user_text else accepted[-1:]
        tasks = [p['task'] for p in accepted]
        if PLAN.search(user_text + ' '.join(extra_intents)) and not tasks and not re.search(r'不想|不要|不需要', user_text):
            tasks.append(user_text)
        for p in accepted:
            p['status'] = 'accepted'
        for task in tasks:
            state['commitments'].append({'id': f'COM-{len(state["commitments"])+1:06}', 'status': 'open',
                **{field: task if field == 'task' else '' for field in FIELDS}, 'reason': '', 'origin_turn': turn['id']})
    state['turns'].append(turn)
    state['revision'] += 1
    refresh(state)
    return state


def validate_intents(turn, response):
    errors = []
    ids = [r['id'] for r in turn['received_intents']]
    handled, deferred = turn['handled_intents'], turn['deferred_intents']
    if set(handled) & set(deferred) or set(ids) != set(handled) | set(deferred):
        errors.append('every received intent must enter handled XOR deferred')
    for ident, quote in handled.items():
        if not isinstance(quote, str) or not quote.strip() or quote not in response:
            errors.append(f'{ident}: handled requires an actual response excerpt')
    if deferred and not re.search(r'下次|下一步|稍后|暂缓|延期|先休息|之后继续', response):
        errors.append('deferred intents require a brief user-visible notice')
    if any(not isinstance(reason, str) or not reason.strip() for reason in deferred.values()):
        errors.append('deferred intent requires reason')
    return errors


def validate_commitments(previous, current):
    errors = []
    old = {c['id']: c for c in previous}
    new = {c['id']: c for c in current}
    if len(new) != len(current) or not set(old) <= set(new):
        errors.append('commitment silently dropped or duplicate ID')
    for ident, c in new.items():
        if c['status'] not in {'open', 'defined', 'deferred'}:
            errors.append(f'{ident}: invalid commitment status')
        if c['status'] == 'open':
            errors.append(f'{ident}: define the minimum plan or explicitly defer')
        if c['status'] == 'defined' and any(not isinstance(c.get(f), str) or not c[f].strip() for f in FIELDS):
            errors.append(f'{ident}: task, deliverable, acceptance_criteria, time_budget, failure_adjustment required')
        if c['status'] == 'deferred' and not c.get('reason', '').strip():
            errors.append(f'{ident}: defer reason required')
    return errors


def finish(state, resolution):
    state = copy.deepcopy(state)
    if resolution.get('base_revision') != state['revision']:
        raise ValueError('stale turn resolution')
    turn = state['turns'][-1]
    if turn['status'] != 'received':
        raise ValueError('turn already finished')
    response = resolution['response']
    turn['handled_intents'] = resolution.get('handled_intents', {})
    turn['deferred_intents'] = resolution.get('deferred_intents', turn['deferred_intents'])
    old = copy.deepcopy(state['commitments'])
    updates = resolution.get('commitment_updates', {})
    if set(updates) - {c['id'] for c in old}:
        raise ValueError('unknown commitment update')
    for c in state['commitments']:
        update = updates.get(c['id'], {})
        if set(update) - set(FIELDS) - {'status', 'reason'}:
            raise ValueError('commitment identity/origin cannot be rewritten')
        c.update(update)
    errors = validate_intents(turn, response) + validate_commitments(old, state['commitments'])
    for c in state['commitments']:
        if c['id'] in updates and c['status'] == 'defined' and any(c[f] not in response for f in FIELDS):
            errors.append(f'{c["id"]}: minimum plan must be delivered to user, not only saved internally')
    if any(c['status'] == 'deferred' for c in state['commitments']) and not re.search(r'下次|下一步|暂缓|延期|之后继续', response):
        errors.append('deferred commitment requires brief notice')
    # A response claiming ready needs a current artifact, never a submitted status string.
    delivery = 'draft_only'
    if resolution.get('artifact_dir'):
        from resume_pipeline import verify
        from argparse import Namespace
        prior = json.loads((Path(resolution['artifact_dir']) / 'build-report.json').read_text())
        if prior.get('delivery_status') != 'ready' or prior.get('visual_reviewed') is not True:
            raise ValueError('artifact has not passed prior content and visual review')
        report = verify(Namespace(output_dir=Path(resolution['artifact_dir']),
            sources_dir=Path(resolution['sources_dir']), pdfinfo='pdfinfo', pdftotext='pdftotext',
            visual_reviewed=True, content_reviewed=True))
        delivery = report['delivery_status']
    mode = resolution.get('mode', 'conversation')
    if mode not in {'conversation', 'industry', 'interview'}:
        errors.append('invalid response mode')
    errors += language_errors(response, mode, delivery)
    if errors:
        raise ValueError('; '.join(errors))
    proposed = resolution.get('proposed_actions', [])
    if not proposed:
        proposed = [v for v in re.split(r'[。\n]', response) if PLAN.search(v) and re.search(r'建议|可以|我们|试试', v)]
    for task in proposed:
        if not isinstance(task, str) or not task.strip() or task not in response:
            raise ValueError('proposed action must quote the actual assistant response')
        state['proposals'].append({'task': task, 'status': 'proposed', 'turn_id': turn['id']})
    turn.update(status='finished', response=response)
    state['revision'] += 1
    refresh(state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='isolated session/SAVE ledger directory')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    p = sub.add_parser('begin')
    p.add_argument('--input', type=Path, required=True, help='raw current user UTF-8 message')
    p.add_argument('--intents', type=Path, help='optional additional extracted intent strings JSON')
    p = sub.add_parser('finish')
    p.add_argument('--resolution', type=Path, required=True)
    p.add_argument('--response-output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with state_lock(args.root):
            path = args.root / 'turn-ledger.json'
            state = json.loads(path.read_text()) if path.exists() else empty()
            if args.command == 'begin':
                extra = json.loads(args.intents.read_text()) if args.intents else []
                state = begin(state, args.input.read_text(), extra)
                atomic_json(path, state)
            elif args.command == 'finish':
                # Never leave an earlier accepted response in the output on failure.
                args.response_output.unlink(missing_ok=True)
                resolution = json.loads(args.resolution.read_text())
                state = finish(state, resolution)
                atomic_json(path, state)
                args.response_output.write_text(state['turns'][-1]['response'], encoding='utf-8')
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
