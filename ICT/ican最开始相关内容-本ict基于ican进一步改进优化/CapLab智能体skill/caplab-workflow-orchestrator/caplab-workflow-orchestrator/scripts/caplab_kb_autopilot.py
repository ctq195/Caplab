#!/usr/bin/env python3
"""Audit normalized KB snapshots; queue changes and archive LOCAL candidates.

No network, spreadsheet writes, scheduler, or production-index installation.
Semantic/human records are supplied by the host, not authenticated by this CLI.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import tempfile
import uuid
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from caplab_state import CapLabError, atomic_json, state_lock
from caplab_knowledge import private_key_errors

CONTENT = {'source', 'entity', 'claim', 'monitor'}
RISK_SCOPES = {'policy', 'admission', 'exam', 'deadline', 'permission'}
CURRENT_RULES = RISK_SCOPES | {'recruitment'}
LINEAGE = ['access_label', 'access_tier', 'permission_source', 'permission_version', 'mask_mode']
BASE_FIELDS = {
    'source': ['source_id', 'url', 'source_type', 'published_at', 'checked_at', 'grade', 'region'],
    'entity': ['id', 'title', 'region'],
    'claim': ['id', 'entity_id', 'field', 'statement', 'source_id', 'scope', 'status', 'region'],
    'monitor': ['id', 'object_id', 'next_review'],
}
RUNTIME = {
    '41_更新队列': ['Queue_ID', 'Object_ID', 'Priority', 'Trigger', 'Detected_Time', 'Due_Time', 'Status', 'Assigned_To', 'Search_Query', 'Expected_Change', 'Result_Change_ID'],
    '42_变更检测': ['Change_ID', 'Object_ID', 'OLD_Value', 'NEW_Value', 'OLD_Source_ID', 'NEW_Source_ID', 'OLD_Hash', 'NEW_Hash', 'Change_Type', 'Detection_Method', 'Detected_Time', 'Risk_Level', 'Review_Status'],
    '43_版本发布': ['Release_ID', 'Version', 'Release_Time', 'Trigger', 'Changed_Count', 'Added_Count', 'Updated_Count', 'Removed_Count', 'Gate_Result', 'Regression_Result', 'Human_Approver', 'Release_Scope', 'Changelog'],
    '44_异常待审': ['Exception_ID', 'Object_ID', 'Exception_Type', 'Severity', 'Description', 'Evidence', 'Suggested_Action', 'Human_Decision', 'Decision_By', 'Decision_Time', 'Closed'],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def known(value):
    return value is not None and (not isinstance(value, str) or value.strip() not in {'', 'UNKNOWN', 'N/A', '待定', '不详'})


def text_known(value):
    return isinstance(value, str) and known(value)


def default_config():
    def table(kind, pk, required, dates=(), dedupe=(), fk=None):
        return dict(kind=kind, id_field=pk, required=list(required), date_fields=list(dates), dedupe_fields=list(dedupe), foreign_keys=fk or {})
    tables = {
        '15_来源索引': table('source', 'source_id', ['source_id', 'url', 'source_type', 'published_at', 'checked_at', 'grade', 'region'] + LINEAGE, ['published_at', 'checked_at', 'valid_from', 'valid_until'], ['url']),
        '02_人物案例': table('entity', 'id', ['id', 'title', 'region'] + LINEAGE, dedupe=['title', 'region']),
        '16_事实来源': table('claim', 'id', ['id', 'entity_id', 'field', 'statement', 'source_id', 'scope', 'status', 'region'] + LINEAGE, ['valid_from', 'valid_until', 'next_review'], ['entity_id', 'field', 'statement'], {'entity_id': '@entity', 'source_id': '@source'}),
        '36_周期监测总览': table('monitor', 'id', ['id', 'object_id', 'next_review'], ['next_review'], fk={'object_id': '@content'}),
    }
    for name, columns in RUNTIME.items():
        tables[name] = table('governance', columns[0], columns)
    return {'schema_version': '1.0.0', 'tables': tables, 'timezone': 'Asia/Shanghai'}


def shape(snapshot, config):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('tables'), dict):
        raise ValueError('snapshot requires a tables object')
    tables = config.get('tables')
    if not isinstance(tables, dict) or not tables:
        raise ValueError('config requires table definitions')
    if set(snapshot['tables']) != set(tables):
        raise ValueError('snapshot tables must match configured tables; map every enabled workbook table')
    if not {'source', 'entity', 'claim', 'monitor'} <= {x.get('kind') for x in tables.values()}:
        raise ValueError('config must define source/entity/claim/monitor tables')
    for name, spec in tables.items():
        if spec.get('kind') not in CONTENT | {'governance'}:
            raise ValueError('unsupported table kind: ' + name)
        if not spec.get('id_field') or not isinstance(spec.get('required'), list) or spec['id_field'] not in spec['required']:
            raise ValueError('table requires a primary key and required fields: ' + name)
        if not isinstance(snapshot['tables'][name], list) or any(not isinstance(r, dict) for r in snapshot['tables'][name]):
            raise ValueError('each table must contain row objects: ' + name)
        expected_pk = 'source_id' if spec['kind'] == 'source' else 'id'
        if spec['kind'] in CONTENT and spec['id_field'] != expected_pk:
            raise ValueError('normalize workbook primary keys to ' + expected_pk)
        if spec['kind'] in CONTENT and not set(BASE_FIELDS[spec['kind']]) <= set(spec['required']):
            raise ValueError('config cannot omit normalized core fields: ' + name)
    return [(name, spec, row) for name, spec in tables.items() for row in snapshot['tables'][name]]


def content_rows(snapshot, config):
    return [(n, s, r) for n, s, r in shape(snapshot, config) if s['kind'] in CONTENT]


def bindings(snapshot, config, as_of):
    tables = {n: rows for n, rows in snapshot['tables'].items() if config['tables'][n]['kind'] in CONTENT}
    return digest({'tables': tables, 'config': config, 'as_of': as_of})


def normalized(value):
    return ' '.join(str(value).strip().lower().split())


def url_key(value):
    parts = urlsplit(str(value).strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True))), ''))


def active(row, as_of):
    if row.get('status', 'current') != 'current':
        return False
    for field, direction in [('valid_from', 1), ('valid_until', -1), ('next_review', -1)]:
        value = row.get(field)
        if known(value):
            try:
                day = dt.date.fromisoformat(value)
                if (direction == 1 and day > as_of) or (direction == -1 and day < as_of):
                    return False
            except (ValueError, TypeError):
                return False
    return True


def visible_claims(snapshot, config, tier, as_of):
    """Local candidate regression projection, NOT an alternative user RAG API."""
    if tier not in {'free', 'paid'}:
        return []
    rows = content_rows(snapshot, config)
    by_kind = {kind: {r.get(s['id_field']): r for _, s, r in rows if s['kind'] == kind} for kind in CONTENT}
    visible = []
    for ident, claim in by_kind['claim'].items():
        source = by_kind['source'].get(claim.get('source_id'))
        entity = by_kind['entity'].get(claim.get('entity_id'))
        lineage = [claim, source, entity]
        if not all(isinstance(r, dict) and active(r, as_of) and all(text_known(r.get(f)) for f in LINEAGE) for r in lineage):
            continue
        if any(r['access_tier'] not in {'free', 'paid'} or (tier == 'free' and r['access_tier'] == 'paid') for r in lineage):
            continue
        if source.get('grade') not in {'A', 'B', 'B-商业语境访谈'} or not known(source.get('checked_at')):
            continue
        visible.append(ident)
    return visible


def diff(old, new, config, as_of):
    def keyed(data):
        result = {}
        for name, spec, row in content_rows(data, config):
            ident = row.get(spec['id_field'])
            if not isinstance(ident, str) or not known(ident) or ident in result:
                raise ValueError('diff requires globally unique known content IDs')
            result[ident] = (name, spec, row)
        return result
    previous, current = keyed(old), keyed(new)
    changes, queue = [], []
    for ident in sorted(set(previous) | set(current)):
        before = previous.get(ident, (None, None, None))[2]
        after = current.get(ident, (None, None, None))[2]
        if before == after:
            continue
        row = after or before
        kind = 'REMOVED' if after is None else 'NEW' if before is None else {'expired': 'EXPIRED', 'conflict': 'CONFLICT', 'unverified': 'UNVERIFIED', 'removed': 'REMOVED'}.get(after.get('status'), 'UPDATED')
        permission_change = before is not None and after is not None and any(before.get(f) != after.get(f) for f in LINEAGE)
        risk = kind in {'REMOVED', 'EXPIRED', 'CONFLICT', 'UNVERIFIED'} or row.get('scope') in RISK_SCOPES or permission_change
        change_id = 'CHG-' + digest([ident, before, after])[:16]
        changes.append(dict(Change_ID=change_id, Object_ID=ident, OLD_Value=before, NEW_Value=after,
            OLD_Source_ID=(before or {}).get('source_id', 'UNKNOWN'), NEW_Source_ID=(after or {}).get('source_id', 'UNKNOWN'),
            OLD_Hash=digest(before) if before else 'UNKNOWN', NEW_Hash=digest(after) if after else 'UNKNOWN',
            Change_Type=kind, Detection_Method='normalized_snapshot_hash', Detected_Time=as_of,
            Risk_Level='P1' if risk else 'P3', Review_Status='PENDING' if risk else 'MACHINE_DETECTED'))
        queue.append(queue_row(ident, 'change:' + kind, as_of, 'P1' if risk else 'P3', change_id))
    queued = {q['Object_ID'] for q in queue}
    for _, spec, row in content_rows(new, config):
        if spec['kind'] != 'monitor':
            continue
        due = row.get('next_review')
        if not isinstance(due, str):
            raise ValueError('monitor next_review must be ISO date or UNKNOWN')
        if due == 'UNKNOWN':
            continue
        dt.date.fromisoformat(due)
        ident = row.get('object_id')
        if due <= as_of and ident not in queued:
            queue.append(queue_row(ident, 'due_review', as_of, 'P2', 'UNKNOWN', due))
            queued.add(ident)
    return {'42_变更检测': changes, '41_更新队列': queue,
            'counts': {k: sum(c['Change_Type'] == k for c in changes) for k in ['NEW', 'UPDATED', 'EXPIRED', 'REMOVED', 'CONFLICT', 'UNVERIFIED']}}


def queue_row(ident, trigger, day, priority, change, due=None):
    return dict(Queue_ID='QUE-' + digest([ident, trigger, day])[:16], Object_ID=ident, Priority=priority,
        Trigger=trigger, Detected_Time=day, Due_Time=due or day, Status='PENDING', Assigned_To='UNKNOWN',
        Search_Query='UNKNOWN', Expected_Change='UNKNOWN', Result_Change_ID=change)


def audit(snapshot, config, as_of, semantic=None, approvals=None, previous=None):
    if private_key_errors(snapshot) or (previous and private_key_errors(previous)):
        raise ValueError('private fields forbidden in public knowledge snapshots')
    day = dt.date.fromisoformat(as_of)
    rows = content_rows(snapshot, config)
    all_rows = shape(snapshot, config)
    snapshot_hash = bindings(snapshot, config, as_of)
    errors = {f'G{i:02}': [] for i in range(1, 13)}
    reviews = {f'G{i:02}': [] for i in range(1, 13)}
    sources = [r for _, s, r in rows if s['kind'] == 'source']
    claims = [r for _, s, r in rows if s['kind'] == 'claim']
    source_map = {r.get('source_id'): r for r in sources}
    ids = Counter(r.get(s['id_field']) for _, s, r in rows)
    kind_ids = {kind: {r.get(s['id_field']) for _, s, r in rows if s['kind'] == kind} for kind in CONTENT}
    object_hashes = {r.get(s['id_field']): digest(r) for _, s, r in rows}
    for name, spec, row in all_rows:
        ident = row.get(spec['id_field'])
        for field in spec['required']:
            value = row.get(field)
            if field in BASE_FIELDS.get(spec['kind'], []) and not isinstance(value, str):
                errors['G04'].append(f'{name}/{ident}: normalized {field} must be text')
            if value is None or (isinstance(value, str) and (not value.strip() or value in {'N/A', '待定', '不详'})):
                errors['G04'].append(f'{name}/{ident}: missing {field}; use value or UNKNOWN')
        if not isinstance(ident, str) or not known(ident):
            errors['G09'].append(f'{name}: unknown/non-string primary key')
        for field in spec.get('date_fields', []):
            if not known(row.get(field)):
                continue
            try:
                value = dt.date.fromisoformat(row[field])
                if not 1900 <= value.year <= day.year + 30:
                    raise ValueError('year outside configured business horizon')
                if field == 'checked_at' and value > day:
                    raise ValueError('checked_at is in future')
            except (ValueError, TypeError):
                errors['G03'].append(f'{ident}: invalid {field}')
        if known(row.get('valid_from')) and known(row.get('valid_until')) and str(row['valid_until']) < str(row['valid_from']):
            errors['G03'].append(f'{ident}: end before start')
        if spec['kind'] == 'source':
            url = row.get('url', '')
            try:
                parsed = urlsplit(url)
                local = row.get('source_type') in {'local_file', 'database'}
                valid = (local and isinstance(url, str) and (Path(url).is_absolute() or parsed.scheme == 'db')) or (parsed.scheme in {'http', 'https'} and bool(parsed.hostname) and not re.search(r'\s', url) and not parsed.username and not parsed.password)
            except (ValueError, TypeError):
                valid = False
            if not valid:
                errors['G02'].append(f'{ident}: invalid typed URL/path')
            if not known(row.get('checked_at')):
                errors['G10'].append(f'{ident}: source not verified')
        for field, target in spec.get('foreign_keys', {}).items():
            valid_ids = (set(ids) if target == '@content' else kind_ids.get(target[1:], set())) if target.startswith('@') else {r.get(config['tables'][target]['id_field']) for r in snapshot['tables'].get(target, [])}
            if not known(row.get(field)) or row[field] not in valid_ids or ids[row[field]] != 1:
                errors['G11'].append(f'{ident}: dangling/ambiguous {field}')
        if spec['kind'] == 'claim' and row.get('status') not in {'current', 'historical', 'expired', 'removed', 'conflict', 'unverified'}:
            errors['G04'].append(f'{ident}: invalid claim status')
    duplicate_rows = 0
    for name, spec in config['tables'].items():
        seen_ids, seen_keys = set(), set()
        for row in snapshot['tables'][name]:
            ident = row.get(spec['id_field'])
            duplicate = False
            if ident in seen_ids:
                errors['G09'].append(f'{name}/{ident}: duplicate primary key')
                duplicate = True
            seen_ids.add(ident)
            fields = spec.get('dedupe_fields', [])
            if fields:
                key = tuple(url_key(row.get(f, '')) if f == 'url' else normalized(row.get(f, '')) for f in fields)
                if key in seen_keys:
                    errors['G09'].append(f'{name}/{ident}: duplicate business key')
                    duplicate = True
                seen_keys.add(key)
            if duplicate and spec['kind'] in CONTENT:
                duplicate_rows += 1
    if any(count != 1 for count in ids.values()):
        errors['G11'].append('content IDs must be globally unique')
    for claim in claims:
        ident = claim.get('id')
        source = source_map.get(claim.get('source_id'))
        if not source or sum(s.get('source_id') == claim.get('source_id') for s in sources) != 1:
            errors['G01'].append(f'{ident}: source missing/nonunique')
        grade = (source or {}).get('grade')
        if grade not in {'A', 'B', 'B-商业语境访谈'}:
            errors['G10'].append(f'{ident}: evidence below B')
        elif claim.get('scope') in CURRENT_RULES and claim.get('status') == 'current' and grade != 'A':
            reviews['G10'].append(ident)
        if claim.get('status') in {'unverified', 'conflict'}:
            reviews['G10'].append(ident)
        for gate in ['G05', 'G06', 'G07', 'G08']:
            matches = [x for x in (semantic or {}).get('items', []) if x.get('id') == ident and x.get('gate') == gate and x.get('object_hash') == digest(claim)] if (semantic or {}).get('snapshot_hash') == snapshot_hash else []
            item = matches[0] if len(matches) == 1 else {}
            if item.get('status') == 'FAIL':
                errors[gate].append(f'{ident}: semantic FAIL')
            elif item.get('status') != 'PASS' or not all(text_known(item.get(f)) for f in ['reason', 'evidence_scope', 'claim_scope']):
                reviews[gate].append(ident)
        if not known(claim.get('region')) or not known((source or {}).get('region')):
            reviews['G07'].append(ident)
        if not known(claim.get('scope')):
            reviews['G08'].append(ident)
    changes = diff(previous, snapshot, config, as_of) if previous else {'41_更新队列': [], '42_变更检测': [], 'counts': {}}
    high_risk = {c['id']: digest(c) for c in claims if c.get('scope') in RISK_SCOPES or c.get('status') in {'conflict', 'unverified'}}
    high_risk.update({ident: object_hashes[ident] for ident in reviews['G10']})
    for change in changes['42_变更检测']:
        if change['Risk_Level'] == 'P1':
            high_risk[change['Object_ID']] = change['NEW_Hash'] if change['NEW_Value'] is not None else change['OLD_Hash']
    pending, approvers = [], set()
    for ident, obj_hash in high_risk.items():
        items = [x for x in (approvals or {}).get('items', []) if x.get('id') == ident and x.get('object_hash') == obj_hash] if (approvals or {}).get('snapshot_hash') == snapshot_hash else []
        item = items[0] if len(items) == 1 else {}
        if item.get('decision') == 'REJECTED':
            errors['G12'].append(f'{ident}: human rejected')
        elif item.get('decision') != 'APPROVED' or not all(text_known(item.get(f)) for f in ['reviewer', 'reason']):
            pending.append(ident)
        else:
            approvers.add(item['reviewer'])
    # Approval cannot make an unresolved conflict verified or supply missing sources.
    reviews['G10'] = [ident for ident in reviews['G10'] if ident in pending or any(c['id'] == ident and c.get('status') in {'conflict', 'unverified'} for c in claims)]
    permissions_ok = all(all(text_known(r.get(f)) for f in LINEAGE) and r.get('access_tier') in {'free', 'paid'} for _, s, r in rows if s['kind'] in {'source', 'entity', 'claim'})
    expired = [r for _, s, r in rows if s['kind'] in {'source', 'claim'} and r.get('status', 'current') == 'current' and not active(r, day)]
    free_ids = set(visible_claims(snapshot, config, 'free', day))
    paid_ids = set(visible_claims(snapshot, config, 'paid', day))
    entity_map = {r.get('id'): r for _, s, r in rows if s['kind'] == 'entity'}
    paid_only = {c.get('id') for c in claims if any(r.get('access_tier') == 'paid' for r in [c, source_map.get(c.get('source_id'), {}), entity_map.get(c.get('entity_id'), {})])}
    regression = {
        'schema_and_nonempty': bool(sources and claims and kind_ids['entity']),
        'primary_keys': not errors['G09'], 'foreign_keys': not errors['G11'],
        'source_coverage': not errors['G01'], 'unknown_convention': not errors['G04'],
        'duplicates': not errors['G09'], 'current_freshness': not expired and not errors['G03'],
        'permission_lineage': permissions_ok,
        'runtime_tables': all(name in config['tables'] and set(cols) <= set(config['tables'][name]['required']) for name, cols in RUNTIME.items()),
        'retrieval_permissions': not (free_ids & paid_only) and free_ids <= paid_ids,
    }
    errors['G12'].extend(key for key, ok in regression.items() if not ok)
    reviews['G12'].extend(pending)
    statuses = {g: 'FAIL' if errors[g] else 'REVIEW' if reviews[g] else 'PASS' for g in errors}
    result = 'BLOCKED' if 'FAIL' in statuses.values() else 'REVIEW' if 'REVIEW' in statuses.values() else '12/12'
    exceptions = []
    for gate in statuses:
        for reason in errors[gate] + [f'{x}: review required' for x in reviews[gate]]:
            exceptions.append(dict(Exception_ID='EXC-' + digest([gate, reason])[:16], Object_ID='UNKNOWN', Exception_Type=gate,
                Severity='P1' if errors[gate] else 'P2', Description=reason, Evidence=snapshot_hash,
                Suggested_Action='核对当前来源、字段或审核记录', Human_Decision='UNKNOWN', Decision_By='UNKNOWN', Decision_Time='UNKNOWN', Closed='NO'))
    ratio = lambda a, b: a / b if b else None
    required_values = [r.get(f) for _, s, r in rows for f in s['required']]
    qc = dict(Run_ID='QC-' + uuid.uuid4().hex[:12], Run_Time=now(), Gate_Result=result,
        Pass_Count=sum(v == 'PASS' for v in statuses.values()), Review_Count=sum(v == 'REVIEW' for v in statuses.values()), Fail_Count=sum(v == 'FAIL' for v in statuses.values()),
        Blocking_Reason=[g for g, status in statuses.items() if status != 'PASS'], Audit_ID='AUD-' + snapshot_hash[:16], **{g + '_Status': v for g, v in statuses.items()})
    return dict(Snapshot_Hash=snapshot_hash, Object_Hashes=object_hashes, As_Of=as_of,
        **{'32_数据质检': qc, '19_评测与试算': regression, '44_异常待审': exceptions},
        **changes, Regression_Result='PASS' if all(regression.values()) else 'FAIL', Human_Approvers=sorted(approvers),
        Coverage=dict(source_coverage=ratio(sum(sum(s.get('source_id') == c.get('source_id') for s in sources) == 1 for c in claims), len(claims)),
            core_completeness=ratio(sum(known(v) for v in required_values), len(required_values)), unknown_rate=ratio(sum(v == 'UNKNOWN' for v in required_values), len(required_values)),
            current_freshness=ratio(sum(active(c, day) for c in claims), len(claims)), duplicate_rate=ratio(duplicate_rows, len(rows)), duplicate_errors=len(errors['G09']), target_matrix='pending_configuration'),
        Excel_Status='pending_host_write', Index_Status='not_installed', Scheduler_Status='not_configured',
        Regression_Scope='local_snapshot_projection_only',
        Gate_Details={g: {'errors': errors[g], 'review': reviews[g]} for g in errors})


def init(root):
    if root.exists():
        raise ValueError('init refuses an existing KB_ROOT')
    root.mkdir(parents=True)
    for name in ['config', 'workbook', 'sources/raw', 'sources/normalized', 'snapshots', 'reports', 'releases']:
        (root / name).mkdir(parents=True, exist_ok=True)
    config = default_config()
    atomic_json(root / 'config/schema.json', config)
    atomic_json(root / 'snapshots/empty.json', {'tables': {n: [] for n in config['tables']}})
    return {'status': 'initialized_empty', 'KB_ROOT': str(root), 'scheduler_status': 'not_configured'}


def archive(root, snapshot, config, version, as_of, semantic=None, approvals=None):
    if not re.fullmatch(r'v\d+\.\d+\.\d+', version):
        raise ValueError('version must be vX.Y.Z')
    with state_lock(root):
        pointer = root / 'last-candidate.json'
        prior_version = read(pointer)['version'] if pointer.exists() else None
        if prior_version and not re.fullmatch(r'v\d+\.\d+\.\d+', prior_version):
            raise ValueError('invalid last-candidate pointer')
        previous = read(root / 'releases' / prior_version / 'snapshot.json') if prior_version else {'tables': {n: [] for n in config['tables']}}
        report = audit(snapshot, config, as_of, semantic, approvals, previous)
        if report['32_数据质检']['Gate_Result'] != '12/12':
            return {'status': 'blocked', 'report': report}
        destination = root / 'releases' / version
        if destination.exists():
            raise ValueError('candidate version already exists; never overwrite')
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.candidate-', dir=destination.parent))
        try:
            counts = report['counts']
            record = dict(Release_ID='REL-' + uuid.uuid4().hex[:12], Version=version, Release_Time=now(), Trigger='local_candidate',
                Changed_Count=sum(counts.values()), Added_Count=counts.get('NEW', 0), Updated_Count=counts.get('UPDATED', 0), Removed_Count=counts.get('REMOVED', 0),
                Gate_Result='12/12', Regression_Result=report['Regression_Result'], Human_Approver=report['Human_Approvers'] or ['NOT_REQUIRED'],
                Release_Scope='local_candidate_only', Changelog=counts)
            report['43_版本发布'] = [record]
            for name, value in [('snapshot.json', snapshot), ('schema.json', config), ('report.json', report), ('release.json', record)]:
                atomic_json(staging / name, value)
            staging.rename(destination)
            atomic_json(pointer, {'version': version, 'snapshot_hash': report['Snapshot_Hash']})
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        return {'status': 'candidate_archived', 'version': version, 'path': str(destination), 'report': report}


def summary(output):
    report = output.get('report', output)
    qc = report.get('32_数据质检', {})
    counts = report.get('counts', {})
    release = report.get('43_版本发布', [{}])[0]
    return '\n'.join([
        '# CapLab 知识库本次运行', '',
        'Version: ' + release.get('Version', 'unreleased_candidate'),
        'Status: ' + output.get('status', 'unknown'),
        'Gate_Result: ' + qc.get('Gate_Result', 'not_run'),
        'Regression_Result: ' + report.get('Regression_Result', 'not_run'),
        f'Added/Updated: {counts.get("NEW", 0)}/{counts.get("UPDATED", 0)}',
        f'Blocked_Gates（阻断或待审质检项）: {qc.get("Fail_Count", 0) + qc.get("Review_Count", 0)}',
        f'异常数量: {len(report.get("44_异常待审", []))}',
        'Excel: pending_host_write; Index: not_installed; Scheduler: not_configured', '',
        '本地快照结果；Excel 回写、联网核验、生产 RAG 安装与调度执行需宿主实际完成。', '',
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ['init', 'audit', 'update', 'release']:
        p = sub.add_parser(command)
        p.add_argument('--root', type=Path, required=True)
        if command != 'init':
            p.add_argument('--as-of', required=True)
        if command in {'audit', 'release'}:
            p.add_argument('--snapshot', type=Path, required=True)
            p.add_argument('--semantic', type=Path)
            p.add_argument('--approvals', type=Path)
        if command == 'audit':
            p.add_argument('--old', type=Path)
        if command == 'update':
            p.add_argument('--old', type=Path, required=True)
            p.add_argument('--new', type=Path, required=True)
        if command == 'release':
            p.add_argument('--version', required=True)
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        if args.command == 'init':
            output = init(root)
        else:
            dt.date.fromisoformat(args.as_of)
            config = read(root / 'config/schema.json')
            if args.command == 'update':
                old, new = read(args.old), read(args.new)
                if private_key_errors(old) or private_key_errors(new):
                    raise ValueError('private fields forbidden in public knowledge snapshots')
                output = diff(old, new, config, args.as_of)
                output['status'] = 'changes_detected'
            else:
                snapshot = read(args.snapshot)
                semantic = read(args.semantic) if args.semantic else None
                approvals = read(args.approvals) if args.approvals else None
                if args.command == 'release':
                    output = archive(root, snapshot, config, args.version, args.as_of, semantic, approvals)
                else:
                    output = audit(snapshot, config, args.as_of, semantic, approvals, read(args.old) if args.old else None)
                    output['status'] = 'audited'
            report_path = root / 'reports' / ('RUN-' + uuid.uuid4().hex + '.json')
            atomic_json(report_path, output)
            summary_path = report_path.with_suffix('.md')
            summary_path.write_text(summary(output), encoding='utf-8')
            output = {**output, 'report_path': str(report_path), 'summary_path': str(summary_path)}
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        report = output.get('report', output)
        return 1 if report.get('32_数据质检', {}).get('Gate_Result') in {'BLOCKED', 'REVIEW'} or output.get('status') == 'blocked' else 0
    except (CapLabError, ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
