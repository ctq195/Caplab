from __future__ import annotations
import argparse
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from fixtures import ready_intake, event, make_index
import caplab_state as state
import caplab_profile as profile

ROOT = Path(__file__).resolve().parents[1]


def patch(current, section, value, actor=None):
    return dict(patch_id=f"PAT-{current['id_registry']['PAT'] + 1:06d}",
                actor_skill=actor or state.SECTION_OWNERS[section], skill_version=state.SKILL_VERSION,
                base_revision=current['revision'], operation='propose_patch',
                changes=[dict(op='set', path=f'/sections/{section}', value=value)],
                referenced_ids=[], requires_confirmation=True, summary='synthetic migration check')


def confirmed_state():
    current = state.empty_state()
    current['sections']['intake'] = ready_intake()
    current['section_meta']['intake']['status'] = 'confirmed'
    state.update_registry(current, current['sections'])
    return current


class ProfileGateTests(unittest.TestCase):
    def test_fully_confirmed_profile_is_valid(self):
        self.assertEqual(state.validate_state(confirmed_state()), [])

    def test_old_ready_flags_do_not_bypass_fact_gate(self):
        current = state.empty_state()
        current['sections']['intake'] = {'intake_ready': True, 'confirmation_status': 'confirmed'}
        self.assertEqual(state.route_for(current)[0], 'profile_intake')
        self.assertTrue(state.validate_patch(patch(current, 'profile', {}), current))

    def test_missing_declined_and_unread_facts_block(self):
        for status in ['unconfirmed', 'declined', 'conflicted']:
            with self.subTest(status=status):
                intake = ready_intake(); intake['personal_facts']['gender']['status'] = status
                self.assertTrue(profile.intake_errors(intake))
        intake = ready_intake(); intake['sources'][0]['read_status'] = 'failed'
        self.assertTrue(profile.intake_errors(intake))

    def test_age_reference_and_education_chronology(self):
        for key, value in [('age', dict(value=20, status='confirmed', source_ids=['SRC-000001'], as_of=None)),
                           ('enrollment_year', dict(value=2029, status='confirmed', source_ids=['SRC-000001']))]:
            intake = ready_intake(); intake['personal_facts'][key] = value
            self.assertTrue(profile.intake_errors(intake))
        intake = ready_intake(); intake['personal_facts']['birth_date'] = dict(value='2000-01-01', status='confirmed', source_ids=['SRC-000001'])
        self.assertTrue(profile.intake_errors(intake))

    def test_preparation_allowed_but_formal_exam_needs_policy(self):
        intake = ready_intake(); ev = event()
        self.assertEqual(profile.timeline_errors([ev], intake, True), [])
        ev['kind'] = 'exam'
        self.assertTrue(profile.timeline_errors([ev], intake, True))
        intake['sources'].append(dict(source_id='SRC-000002', source_type='public_source', title='合成资格政策', read_status='success', applicable_period='2026'))
        ev.update(eligibility_status='verified', rule_source_ids=['SRC-000002'])
        self.assertEqual(profile.timeline_errors([ev], intake, True), [])
        ev['related_graduation_year'] = 2027
        self.assertTrue(profile.timeline_errors([ev], intake, True))

    def test_date_precision_and_calendar_invalid(self):
        for date, precision in [('2026-02-30', 'day'), ('2026-01-01', 'year'), ('2026-13', 'month')]:
            ev = event(); ev.update(date=date, precision=precision)
            self.assertTrue(profile.timeline_errors([ev], ready_intake()))

    def test_invalid_timeline_rejected_before_confirmation(self):
        current = confirmed_state(); ev = event(); ev['kind'] = 'exam'
        value = dict(profile_ready=True, confirmation_status='confirmed', decision_timeline=[ev])
        self.assertTrue(state.validate_patch(patch(current, 'profile', value), current))

    def test_accepted_timeline_cannot_have_unconfirmed_event(self):
        current = confirmed_state(); ev = event(); ev['status'] = 'unconfirmed'
        current['sections']['path_decision'] = dict(accepted=True, decision_timeline=[ev])
        self.assertTrue(state.validate_state(current))

    def test_v1_dialogue_fields_remain_supported(self):
        current = confirmed_state(); value = dict(profile_ready=True, confirmation_status='confirmed',
            dialogic_self_understanding=dict(method='event_grounded_reflective_dialogue', clinical_use=False))
        self.assertEqual(state.validate_patch(patch(current, 'profile', value), current), [])


class StateLifecycleV211Tests(unittest.TestCase):
    """Lifecycle against the v2.1.1 CLI: init -> propose -> confirm -> apply -> rollback."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / '.caplab' / 'state'
        make_index(self.workspace / '.caplab' / 'knowledge_index')
        self.run_cli('init', '--root', str(self.root), '--allow-temporary')

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/caplab_state.py'), args[0], *args[1:]],
                                capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def apply_value(self, section, value):
        current = state.load_state(self.root)
        p = patch(current, section, value)
        path = self.workspace / 'patch.json'; path.write_text(json.dumps(p))
        self.run_cli('propose', '--root', str(self.root), '--patch', str(path))
        self.run_cli('confirm', '--root', str(self.root), '--patch-id', p['patch_id'], '--decision', 'confirm', '--text', 'synthetic confirmation')
        self.run_cli('apply', '--root', str(self.root), '--patch-id', p['patch_id'])
        return state.load_state(self.root)

    def test_initialize_then_confirm_then_correct_invalidates_downstream(self):
        initial = state.load_state(self.root)
        self.assertIn('personal_facts', initial['sections']['intake'])
        self.apply_value('intake', ready_intake())
        self.apply_value('profile', dict(profile_ready=True, confirmation_status='confirmed'))
        corrected = ready_intake(); corrected['personal_facts']['graduation_year']['value'] = 2029
        current = self.apply_value('intake', corrected)
        self.assertEqual(current['section_meta']['profile']['status'], 'stale')
        self.assertEqual(state.route_for(current)[0], 'profile_confirmation')
        self.assertEqual(current['active_stage'], 'profile_confirmation')

    def test_invalid_proposal_creates_no_pending_confirmation(self):
        current = state.load_state(self.root)
        value = ready_intake(); value['personal_facts']['graduation_year']['value'] = 2020
        p = patch(current, 'intake', value)
        path = self.workspace / 'bad.json'; path.write_text(json.dumps(p))
        self.run_cli('propose', '--root', str(self.root), '--patch', str(path), ok=False)
        self.assertFalse(list((self.root / 'audit/pending').glob('*.json')))
        self.assertEqual(state.load_state(self.root)['revision'], 0)

    def test_rollback_keeps_new_gate_and_history(self):
        self.apply_value('intake', ready_intake())
        current = state.load_state(self.root)
        self.assertEqual(current['revision'], 1)
        before = (self.root / 'history/revision-000000.json').read_bytes()
        self.run_cli('rollback', '--root', str(self.root), '--revision', '0', '--text', 'synthetic rollback approval')
        current = state.load_state(self.root)
        self.assertEqual(current['revision'], 2)
        self.assertEqual(state.route_for(current)[0], 'profile_intake')
        self.assertEqual((self.root / 'history/revision-000000.json').read_bytes(), before)

    def test_unconfirmed_apply_cannot_write(self):
        current = state.load_state(self.root)
        p = patch(current, 'intake', ready_intake())
        path = self.workspace / 'patch.json'; path.write_text(json.dumps(p))
        self.run_cli('propose', '--root', str(self.root), '--patch', str(path))
        self.run_cli('apply', '--root', str(self.root), '--patch-id', p['patch_id'], ok=False)
        self.assertEqual(state.load_state(self.root)['revision'], 0)

    def test_contract_examples_run_all_five_stages(self):
        import re
        def example(name):
            text=(ROOT/'references/contracts'/(name+'-contract.md')).read_text()
            return json.loads(re.findall(r'```json\s*(.*?)```',text,re.S)[0])
        intake=example('intake');intake.update(ready_intake());intake['candidate_generation_needed']=False
        intake['candidate_paths']=[dict(path_id='PTH-000001',name='合成方向')]
        self.apply_value('intake',intake)
        value=example('profile');value.update(profile_ready=True,confirmation_status='confirmed');self.apply_value('profile',value)
        value=example('path');value.update(accepted=True,evidence_gaps=[dict(gap_id='GAP-000001',description='合成待验证问题')]);self.apply_value('path_decision',value)
        value=example('cycle');value.update(review_ready=True,execution_records=[dict(status='not_executed',reason='合成测试记录')]);self.apply_value('cycle_plan',value)
        value=example('review');value.update(cycle_status='not_executed',decision='adjust')
        current=state.load_state(self.root);p=patch(current,'reviews',value);p['changes'][0]['op']='append'
        file=self.workspace/'review.json';file.write_text(json.dumps(p))
        self.run_cli('propose','--root',str(self.root),'--patch',str(file))
        self.run_cli('confirm','--root',str(self.root),'--patch-id',p['patch_id'],'--decision','confirm','--text','synthetic review approval')
        self.run_cli('apply','--root',str(self.root),'--patch-id',p['patch_id'])
        self.run_cli('validate','--root',str(self.root));self.run_cli('route','--root',str(self.root))
        self.assertEqual(state.load_state(self.root)['revision'],5)

    def test_upgrade_preserves_history_and_rollback_keeps_new_gate(self):
        old=confirmed_state();old['schema_version']='1.0.0';old['sections']['intake'].pop('personal_facts')
        old['sections']['profile']=dict(profile_ready=True,confirmation_status='confirmed');old['section_meta']['profile']['status']='confirmed'
        state.atomic_json(state.state_path(self.root),old);state.save_revision(self.root,old)
        before=(self.root/'history/revision-000000.json').read_bytes()
        self.run_cli('upgrade-state','--root',str(self.root),'--text','synthetic upgrade approval')
        current=state.load_state(self.root);self.assertEqual(current['revision'],1);self.assertFalse(current['sections']['intake']['intake_ready'])
        self.assertEqual(current['section_meta']['profile']['status'],'stale');self.assertEqual((self.root/'history/revision-000000.json').read_bytes(),before)
        self.assertEqual((self.root/'audit/migrations/schema-1.0.0-revision-000000.json').read_bytes(),before)
        self.run_cli('upgrade-state','--root',str(self.root),'--text','synthetic idempotency');self.assertEqual(state.load_state(self.root)['revision'],1)
        self.run_cli('rollback','--root',str(self.root),'--revision','0','--text','synthetic rollback approval')
        current=state.load_state(self.root);self.assertEqual(current['revision'],2);self.assertEqual(state.route_for(current)[0],'profile_intake');self.assertEqual(current['schema_version'],'1.1.0')


if __name__ == '__main__':
    unittest.main()
