"""Synthetic fixtures; no real personal records."""
from caplab_profile import empty_personal


def ready_intake():
    personal = empty_personal()
    values = dict(gender='用户自述', age=20, education_level='本科', institution_name='测试院校',
                  institution_tier='本科院校', enrollment_year=2024, graduation_year=2028)
    for key, item in personal.items():
        item.update(status='confirmed', source_ids=['SRC-000001'])
        if key != 'key_timepoints':
            item['value'] = values[key]
    personal['age']['as_of'] = '2026-09-03'
    personal['institution_tier']['classification_basis'] = '用户提供的办学层次，非排名'
    return dict(decision_question='毕业前先验证什么方向？', personal_facts=personal,
                major=dict(name='测试专业', code=None, status='confirmed', source_ids=['SRC-000001']),
                sources=[dict(source_id='SRC-000001', source_type='user_statement', title='合成测试陈述', read_status='success')],
                conflicts=[], intake_ready=True, confirmation_status='confirmed')


def event():
    return dict(name='准备考试', kind='preparation', date='2026', precision='year', status='confirmed',
                source_ids=['SRC-000001'], related_graduation_year=2028,
                eligibility_status='not_applicable', rule_source_ids=[])


def make_index(root, tier="free", docs=None, sources=None, dense=False):
    """Small but complete signed test index; never a metadata-only readiness stub."""
    import json
    from pathlib import Path
    from caplab_rag import tokenize, build_inverted_index, compute_idf
    from caplab_index import seal_index
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    docs=docs if docs is not None else [dict(doc_id="test#1",sheet="测试表",row=1,entity_id="TEST1",title="软件工程",tags="",source_ids=[],claim_ids=[],fields={},text="软件工程",tokens=tokenize("软件工程"))]
    sources=sources or {}
    inverted=build_inverted_index(docs)
    values={"documents":docs,"sources":sources,"claims":{},"tags":{},"sparse_index":{"inverted_index":inverted,"idf":compute_idf(docs,inverted)},
            "index_meta":{"tier":tier,"kb_version":"test-1","document_count":len(docs),"source_count":len(sources),"claim_count":0,"dense_enabled":dense,"embedding_dimension":2 if dense else 0,"index_version":"3.0.0","created_at":"2026-09-20T00:00:00Z"}}
    for name,value in values.items():(root/(name+".json")).write_text(json.dumps(value,ensure_ascii=False))
    if dense:
        import numpy as np
        np.save(root/"embeddings.npy",np.ones((len(docs),2),dtype="float32"))
    seal_index(root)
    return root
