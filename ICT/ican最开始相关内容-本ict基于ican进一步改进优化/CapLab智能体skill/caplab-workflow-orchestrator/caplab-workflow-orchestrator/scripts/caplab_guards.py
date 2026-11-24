"""Deterministic evidence, language and delivery gates (stdlib only).

Source authenticity is a host responsibility. These checks establish traceability,
not real-world truth. No model-supplied pass flag grants delivery permission.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

STRONG = re.compile(r'独立(?:设计|开发|架构)|从零(?:搭建|开发)|主导|牵头|负责整体|上线|落地|投入实际使用|生产环境|服务\s*\d+\s*用户|提升|降低|优化|获奖|排名|[一二三]等奖')
NUMBER = re.compile(r'\d+(?:\.\d+)?\s*(?:%|％|倍|\+)?|[一二三四五六七八九十百]+倍')
REJECTED = re.compile(r'反正没人查|编造|虚构|假装|捏造|随便写|没有证据|并未|尚未|没(?:有)?(?:上线|落地|获奖|独立|主导)|不是.*(?:独立|主导)')
TUTORIAL = re.compile(r'教程|跟着|照着|参照|照.*搭.*框')
INDEPENDENT = re.compile(r'独立(?:设计|开发|架构)|从零(?:搭建|开发)')
PSYCH = re.compile(r'你(?:的)?(?:真实动机|其实|本质上|就是在逃避)|你.*(?:逃避|害怕失败|动机)')
UNCERTAIN = re.compile(r'可能|或许|一种假设|尚不能|还不能|不能判断')
ABSOLUTE = re.compile(r'就是|都是|都要|统一|一定|不比.*少|本质上|其实只是')
SCOPE = re.compile(r'不少|部分|有些|某些|不同公司|不同岗位|因.*而异')
JOB = re.compile(r'测试岗|测试开发|自动化测试|行业|岗位|开发岗')
READY_WORDS = re.compile(r'直接.{0,6}(?:投|用)|可以.{0,4}投递|放心投|正式投递版|已可投递')


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def norm(text):
    return re.sub(r'\s+', '', text)


def body_fields(data):
    """Enumerate exactly the strings rendered by resume_pipeline.render_body."""
    for key in ('name', 'headline'):
        yield f'/candidate/{key}', data['candidate'][key]
    for i, value in enumerate(data['candidate']['contact']):
        yield f'/candidate/contact/{i}', value
    yield '/meta/target_job', data['meta']['target_job']
    for s, section in enumerate(data['sections']):
        base = f'/sections/{s}'
        yield base + '/title', section['title']
        for i, item in enumerate(section['items']):
            base_i = f'{base}/items/{i}'
            keys = ('title', 'date', 'subtitle', 'location') if section['type'] == 'entries' else ('label', 'text')
            for key in keys:
                if item.get(key):
                    yield f'{base_i}/{key}', item[key]
            if section['type'] == 'entries':
                for b, bullet in enumerate(item['bullets']):
                    yield f'{base_i}/bullets/{b}/text', bullet['text']


# Only layout headings are exempt; custom headings containing facts are checked.
LABELS = {'教育背景', '专业技能', '项目与竞赛经历', '项目经历', '实习经历', '工作经历', '技能', '编程', '数据分析', 'AI 应用', '联系方式', '求职意向'}


def load_sources(root):
    if root is None:
        return {}
    root = Path(root).resolve()
    sources = {}
    for path in sorted(root.glob('*.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        sid = record.get('source_id')
        if not isinstance(sid, str) or not sid or sid in sources:
            raise ValueError('invalid or duplicate source_id')
        if record.get('kind') not in {'user_input', 'user_confirmation', 'uploaded_material', 'external', 'derived'}:
            raise ValueError(f'{sid}: invalid source kind')
        if not isinstance(record.get('text'), str) or not record['text'].strip() or not record.get('locator'):
            raise ValueError(f'{sid}: text and original locator required')
        if record['kind'] == 'external' and not re.match(r'https://', record['locator']):
            raise ValueError(f'{sid}: external source requires HTTPS locator')
        sources[sid] = record
    return sources


def validate_evidence(data, sources):
    """Fail closed for every uncovered rendered field, including names and dates.

    Each binding quotes the complete rendered value from a source. Paraphrases
    require a separately recorded user confirmation of the final wording. This
    avoids pretending substring/keyword overlap proves semantic entailment.
    """
    errors = []
    bindings = data.get('fact_bindings', {})
    if not isinstance(bindings, dict):
        return ['fact_bindings must be an object']
    for path, value in body_fields(data):
        if value in LABELS and (path.endswith('/title') or path.endswith('/label')):
            continue
        binding = bindings.get(path, {})
        source = sources.get(binding.get('source_id')) if isinstance(binding, dict) else None
        if not source:
            errors.append(f'{path}: missing source; confirm or remove this field')
            continue
        if binding['source_id'] not in data.get('selected_evidence', []):
            errors.append(f'{path}: source not registered in selected_evidence')
        text = source.get('text', '')
        if REJECTED.search(text):
            errors.append(f'{path}: fabricated, negated or unresolved source cannot support a claim')
            continue
        if norm(value) not in norm(text):
            errors.append(f'{path}: wording/number/entity exceeds source; downgrade or confirm exact wording')
        if STRONG.search(value) and re.search(r'不允许|不能说|不代表|尚未|未曾|计划|假设|希望|目标是|如果', text):
            errors.append(f'{path}: hypothetical/negated strong fact is not achieved evidence')
        if INDEPENDENT.search(value) and TUTORIAL.search(text):
            errors.append(f'{path}: claim_strength > evidence_strength (tutorial)')
        if source.get('kind') == 'derived':
            calc = source.get('calculation', {})
            try:
                # No eval. Inputs reference literal numeric fields in other sources.
                values = []
                for operand in calc['inputs']:
                    original = sources[operand['source_id']]
                    number = operand['value']
                    if original['kind'] == 'derived' or REJECTED.search(original['text']) or str(number) not in original['text']:
                        raise ValueError('untraceable operand')
                    values.append(float(number))
                if len(values) != 2:
                    raise ValueError('two operands required')
                a, b = values
                result = {'difference': lambda: a-b, 'ratio': lambda: a/b,
                          'percent_change': lambda: (a-b)/b*100}[calc['operation']]()
                formatted = format(result, '.10g') + calc.get('unit', '')
                if value != formatted or text != formatted:
                    raise ValueError('derived output mismatch')
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                errors.append(f'{path}: derived result cannot be recomputed')
    rendered = '\n'.join(value for _, value in body_fields(data))
    for name, dimension in data.get('scorecard', {}).get('dimensions', {}).items():
        for evidence in dimension.get('evidence', []):
            if any(norm(token) not in norm(rendered) for token in NUMBER.findall(evidence)):
                errors.append(f'scorecard.{name}: metric absent from validated body cannot earn credit')
    return errors


def downgrade_tutorial(text, source_text):
    """Return original source wording, never invent a weaker accomplishment."""
    if INDEPENDENT.search(text) and TUTORIAL.search(source_text) and not REJECTED.search(source_text):
        return source_text
    return text


def language_errors(response, mode='conversation', delivery_status='draft_only'):
    errors = []
    for sentence in re.split(r'[。！？\n]', response):
        if PSYCH.search(sentence) and (not UNCERTAIN.search(sentence) or ABSOLUTE.search(sentence)):
            errors.append('psychological inference must explicitly preserve uncertainty')
        if JOB.search(sentence):
            if mode == 'interview' and not re.search(r'假设|岗位假设', sentence):
                errors.append('interview job claim requires explicit job assumption')
            elif mode in {'industry', 'conversation'} and (mode == 'industry' or ABSOLUTE.search(sentence)) and (not SCOPE.search(sentence) or ABSOLUTE.search(sentence)):
                errors.append('industry explanation requires limited scope without universal conclusion')
    if delivery_status != 'ready' and READY_WORDS.search(response):
        errors.append('delivery_status != ready: ready-to-submit wording blocked')
    return errors


def delivery_state(*, render_passed, evidence_errors, content_status, open_questions, score_passed):
    if content_status not in {'draft', 'reviewed', 'passed'}:
        raise ValueError('invalid content_status')
    ready = render_passed and not evidence_errors and content_status == 'passed' and not open_questions and score_passed
    return {'render_status': 'passed' if render_passed else 'failed',
            'evidence_status': 'blocked' if evidence_errors else 'passed',
            'content_status': content_status,
            'delivery_status': 'ready' if ready else ('draft_only' if evidence_errors or content_status == 'draft' else 'needs_completion')}
