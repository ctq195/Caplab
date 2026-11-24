"""Synthetic local fixtures; no live sources, Excel, or DuMate assertions."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import caplab_kb_autopilot as kb

DAY = '2026-10-12'


def fixture():
    config = kb.default_config()
    snapshot = {'tables': {name: [] for name in config['tables']}}
    permission = dict(access_label='synthetic-public-label', access_tier='free', permission_source='synthetic-fixture', permission_version='test-1', mask_mode='visible')
    snapshot['tables']['15_来源索引'] = [dict(source_id='KSRC-000001', url='https://example.invalid/source', source_type='web', published_at='2026-10-01', checked_at=DAY, grade='A', region='synthetic-region', **permission)]
    snapshot['tables']['02_人物案例'] = [dict(id='KPER-000001', title='Synthetic only', region='synthetic-region', **permission)]
    snapshot['tables']['16_事实来源'] = [dict(id='CLM-000001', entity_id='KPER-000001', field='synthetic_fact', statement='Synthetic fixture statement', source_id='KSRC-000001', scope='person', status='current', region='synthetic-region', **permission)]
    return config, snapshot


def semantic(snapshot, config):
    return {'snapshot_hash': kb.bindings(snapshot, config, DAY), 'items': [dict(id=row['id'], object_hash=kb.digest(row), gate=g, status='PASS', reason='Synthetic independent fixture review', evidence_scope='One synthetic object', claim_scope='Same synthetic object') for n, s, row in kb.content_rows(snapshot, config) if s['kind'] == 'claim' for g in ['G05', 'G06', 'G07', 'G08']]}


def approval(snapshot, config, rows):
    return {'snapshot_hash': kb.bindings(snapshot, config, DAY), 'items': [dict(id=ident, object_hash=kb.digest(row), decision='APPROVED', reviewer='Synthetic test operator', reason='Synthetic signed decision fixture') for ident, row in rows]}


class AutopilotTests(unittest.TestCase):
    def setUp(self):
        self.config, self.snapshot = fixture()

    def claim(self):
        return self.snapshot['tables']['16_事实来源'][0]

    def run_audit(self, semantic_input=None, approvals=None, old=None):
        return kb.audit(self.snapshot, self.config, DAY, semantic_input, approvals, old)

    def test_missing_semantic_cannot_claim_twelve(self):
        report = self.run_audit()
        self.assertEqual(report['32_数据质检']['Gate_Result'], 'REVIEW')
        self.assertEqual(report['32_数据质检']['Pass_Count'], 8)

    def test_complete_review_passes_and_source_missing_blocks(self):
        report = self.run_audit(semantic(self.snapshot, self.config))
        self.assertEqual(report['32_数据质检']['Gate_Result'], '12/12')
        self.claim()['source_id'] = 'MISSING'
        report = self.run_audit(semantic(self.snapshot, self.config))
        self.assertEqual(report['32_数据质检']['G01_Status'], 'FAIL')
        self.assertEqual(report['32_数据质检']['G11_Status'], 'FAIL')

    def test_old_hash_review_rejected_after_fact_change(self):
        review = semantic(self.snapshot, self.config)
        self.claim()['statement'] = 'A different synthetic statement'
        self.assertEqual(self.run_audit(review)['32_数据质检']['G05_Status'], 'REVIEW')

    def test_semantic_bound_to_date_and_config(self):
        review = semantic(self.snapshot, self.config)
        self.config['timezone'] = 'UTC'
        self.assertEqual(self.run_audit(review)['32_数据质检']['G06_Status'], 'REVIEW')
        self.config['timezone'] = 'Asia/Shanghai'
        result = kb.audit(self.snapshot, self.config, '2026-10-13', review)
        self.assertEqual(result['32_数据质检']['G06_Status'], 'REVIEW')

    def test_duplicate_review_does_not_count_as_pass(self):
        review = semantic(self.snapshot, self.config)
        review['items'].append(copy.deepcopy(review['items'][0]))
        self.assertEqual(self.run_audit(review)['32_数据质检']['G05_Status'], 'REVIEW')

    def test_policy_needs_actual_operator_record_and_rejects_stale_approval(self):
        self.claim()['scope'] = 'policy'
        review = semantic(self.snapshot, self.config)
        self.assertEqual(self.run_audit(review)['32_数据质检']['G12_Status'], 'REVIEW')
        sign = approval(self.snapshot, self.config, [('CLM-000001', self.claim())])
        self.assertEqual(self.run_audit(review, sign)['32_数据质检']['Gate_Result'], '12/12')
        self.claim()['statement'] = 'Changed after approval'
        self.assertEqual(self.run_audit(semantic(self.snapshot, self.config), sign)['32_数据质检']['G12_Status'], 'REVIEW')

    def test_grade_b_policy_review_can_pass_but_d_never_passes(self):
        self.claim()['scope'] = 'admission'
        source = self.snapshot['tables']['15_来源索引'][0]
        source['grade'] = 'B'
        sign = approval(self.snapshot, self.config, [('CLM-000001', self.claim())])
        self.assertEqual(self.run_audit(semantic(self.snapshot, self.config), sign)['32_数据质检']['Gate_Result'], '12/12')
        source['grade'] = 'D'
        self.assertEqual(self.run_audit(semantic(self.snapshot, self.config), sign)['32_数据质检']['G10_Status'], 'FAIL')

    def test_conflict_not_cured_by_approval_string(self):
        self.claim()['status'] = 'conflict'
        sign = approval(self.snapshot, self.config, [('CLM-000001', self.claim())])
        self.assertEqual(self.run_audit(semantic(self.snapshot, self.config), sign)['32_数据质检']['G10_Status'], 'REVIEW')

    def test_invalid_dates_urls_unknown_fields_and_orphans(self):
        source = self.snapshot['tables']['15_来源索引'][0]
        source['checked_at'] = '2026-02-30'
        source['url'] = 'https://'
        self.claim()['entity_id'] = 'MISSING'
        self.claim()['statement'] = ''
        result = self.run_audit()['32_数据质检']
        for gate in ['G02', 'G03', 'G04', 'G11']:
            self.assertEqual(result[gate + '_Status'], 'FAIL')

    def test_paid_source_and_entity_cannot_leak_through_free_claim(self):
        day = kb.dt.date.fromisoformat(DAY)
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'free', day), ['CLM-000001'])
        self.snapshot['tables']['15_来源索引'][0]['access_tier'] = 'paid'
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'free', day), [])
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'paid', day), ['CLM-000001'])
        self.snapshot['tables']['15_来源索引'][0]['access_tier'] = 'free'
        self.snapshot['tables']['02_人物案例'][0]['access_tier'] = 'paid'
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'free', day), [])
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'unknown', day), [])

    def test_expired_current_blocks_release_and_default_projection(self):
        self.claim()['valid_until'] = '2026-10-11'
        self.assertEqual(self.run_audit()['Regression_Result'], 'FAIL')
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'paid', kb.dt.date.fromisoformat(DAY)), [])

    def test_no_change_and_due_queue_are_separate(self):
        self.snapshot['tables']['36_周期监测总览'] = [dict(id='MON-1', object_id='CLM-000001', next_review=DAY)]
        result = kb.diff(self.snapshot, copy.deepcopy(self.snapshot), self.config, DAY)
        self.assertEqual(result['42_变更检测'], [])
        self.assertEqual(len(result['41_更新队列']), 1)

    def test_changed_removed_and_unverified_are_distinct(self):
        old = copy.deepcopy(self.snapshot)
        self.claim()['status'] = 'unverified'
        result = kb.diff(old, self.snapshot, self.config, DAY)
        self.assertEqual(result['42_变更检测'][0]['Change_Type'], 'UNVERIFIED')
        self.snapshot['tables']['16_事实来源'] = []
        result = kb.diff(old, self.snapshot, self.config, DAY)
        self.assertEqual(result['42_变更检测'][0]['Change_Type'], 'REMOVED')
        self.assertEqual(result['42_变更检测'][0]['Review_Status'], 'PENDING')

    def test_empty_and_unknown_table_cannot_publish(self):
        empty = {'tables': {n: [] for n in self.config['tables']}}
        self.assertEqual(kb.audit(empty, self.config, DAY)['32_数据质检']['Gate_Result'], 'BLOCKED')
        self.snapshot['tables']['unknown'] = []
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_missing_permission_never_defaults_to_public(self):
        self.claim()['access_label'] = 'UNKNOWN'
        result = self.run_audit(semantic(self.snapshot, self.config))
        self.assertFalse(result['19_评测与试算']['permission_lineage'])
        self.assertEqual(kb.visible_claims(self.snapshot, self.config, 'free', kb.dt.date.fromisoformat(DAY)), [])

    def test_malformed_claim_and_weakened_config_cannot_publish(self):
        self.claim()['statement'] = ['Wrong normalized type']
        result = self.run_audit(semantic(self.snapshot, self.config))
        self.assertEqual(result['32_数据质检']['G04_Status'], 'FAIL')
        self.config['tables']['16_事实来源']['required'].remove('statement')
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_privacy_never_archives_public_snapshot(self):
        self.claim()['full_profile'] = {'phone': 'SYNTHETIC'}
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_candidate_archive_rechecks_never_overwrites_and_keeps_production_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'KB'
            kb.init(root)
            with self.assertRaises(ValueError):
                kb.init(root)
            blocked = kb.archive(root, self.snapshot, self.config, 'v0.1.0', DAY)
            self.assertEqual(blocked['status'], 'blocked')
            self.assertFalse((root / 'releases/v0.1.0').exists())
            review = semantic(self.snapshot, self.config)
            result = kb.archive(root, self.snapshot, self.config, 'v0.1.0', DAY, review)
            self.assertEqual(result['status'], 'candidate_archived')
            self.assertEqual(result['report']['43_版本发布'][0]['Added_Count'], 3)
            saved = (root / 'releases/v0.1.0/snapshot.json').read_bytes()
            with self.assertRaises(ValueError):
                kb.archive(root, self.snapshot, self.config, 'v0.1.0', DAY, review)
            self.snapshot['tables']['15_来源索引'][0]['access_tier'] = 'paid'
            blocked = kb.archive(root, self.snapshot, self.config, 'v0.2.0', DAY, semantic(self.snapshot, self.config))
            self.assertEqual(blocked['status'], 'blocked')
            self.assertEqual((root / 'releases/v0.1.0/snapshot.json').read_bytes(), saved)
            self.assertFalse((root / '.caplab/state').exists())
            self.assertFalse((root / '.caplab/knowledge_index').exists())
            self.assertEqual(json.loads((root / 'last-candidate.json').read_text())['version'], 'v0.1.0')


if __name__ == '__main__':
    unittest.main()
