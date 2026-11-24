"""Conservative retrieval quality policy; labels never prove live eligibility."""
import datetime as dt
from collections import Counter

STATUS_KEYS=('review_status','审核状态','事实状态','核验状态','时效状态','当前有效性','有效性状态','版本状态')
DATE_KEYS=('valid_until','生效结束','下次复核日期')
DENIED=('rejected','stale','expired','pending_human_review','pending_review','pending','unreviewed','未核验','待审核','未审核','已拒绝','已过期','已失效','待核验','待当季核验','待正式数据','monitoring','date_not_published','not_published')
VERIFIED={'machine_validated','human_approved','verified','current_official','current_official_decision_ready','已核验','有效','稳定','模板'}

def iso_date(value):
    try:return dt.date.fromisoformat(str(value))
    except (ValueError,TypeError):return None

def record_quality(record, as_of):
    values=[str(record.get(k,'')).strip().lower() for k in STATUS_KEYS if record.get(k)]
    for value in values:
        if any(token in value for token in DENIED):
            return {'allowed':False,'status':'excluded','reason':'review_or_validity_block','actionable':False}
    for key in ('valid_from','生效开始'):
        start=iso_date(record.get(key))
        if start and start>as_of:
            return {'allowed':False,'status':'excluded','reason':'not_yet_effective','actionable':False}
    dates=[]; ambiguous_date=False
    for key in DATE_KEYS:
        raw=record.get(key)
        if raw:
            date=iso_date(raw)
            if date is None:ambiguous_date=True
            elif date<as_of:return {'allowed':False,'status':'excluded','reason':'expired_date','actionable':False}
            else:dates.append(date)
    historical=any('historical' in v or '历史' in v or 'secondary' in v for v in values)
    verified=any(v in VERIFIED for v in values)
    state='historical_reference' if historical else 'verified_snapshot' if verified else 'unknown'
    if ambiguous_date and not historical:state='unknown'
    return {'allowed':True,'status':state,'reason':None,
            'actionable':bool(verified and dates and not historical and not ambiguous_date),
            'needs_live_verification':True}

def document_quality(doc,sources,claims,as_of=None):
    as_of=as_of or dt.datetime.now(dt.timezone.utc).date()
    f=dict(doc.get('fields',{}))
    for key in (*STATUS_KEYS,*DATE_KEYS):
        if key in doc:f[key]=doc[key]
    result=record_quality(f,as_of)
    if not result['allowed']:return result
    if doc.get('sheet')=='06_招聘岗位':
        checked=iso_date(f.get('最后核验日期',f.get('last_verified_at')))
        if checked and (as_of-checked).days>14:
            return {'allowed':False,'status':'excluded','reason':'job_review_older_than_14_days','actionable':False}
        if checked is None:result.update(status='unknown',actionable=False)
    linked=[];missing=False
    for sid in doc.get('source_ids',[]):
        if sid not in sources:missing=True
        else:linked.append(sources[sid])
    for cid in doc.get('claim_ids',[]):
        if cid not in claims:missing=True
        else:
            value=claims[cid];linked.extend(value if isinstance(value,list) else [value])
    for record in linked:
        if not isinstance(record,dict):missing=True;continue
        child=record_quality(record,as_of)
        if not child['allowed']:return dict(child,reason='linked_'+child['reason'])
        if child['status']=='historical_reference':result.update(status='historical_reference',actionable=False)
        elif child['status']=='unknown':result['actionable']=False
    if missing:result.update(status='unknown',actionable=False)
    result['needs_live_verification']=True
    return result

def filter_documents(documents,sources,claims,as_of=None):
    allowed=set();quality={};counts=Counter()
    for i,doc in enumerate(documents):
        q=document_quality(doc,sources,claims,as_of);quality[i]=q
        if q['allowed']:allowed.add(i);counts[q['status']]+=1
        else:counts[q['reason']]+=1
    return allowed,quality,{'total_documents':len(documents),'eligible_documents':len(allowed),
                           'excluded_documents':len(documents)-len(allowed),'counts':dict(counts),
                           'unknown_is_not_verified':True,'historical_is_reference_only':True}
