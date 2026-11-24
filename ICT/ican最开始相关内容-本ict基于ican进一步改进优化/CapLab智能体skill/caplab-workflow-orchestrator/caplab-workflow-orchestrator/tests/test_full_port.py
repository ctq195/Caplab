"""Synthetic runtime regressions for the complete V0.7-to-V1 port."""
import copy
import unittest
import caplab_state as state
import caplab_knowledge as knowledge
from fixtures import ready_intake
from test_migration import confirmed_state, patch


class FullPortTests(unittest.TestCase):
    def request(self):
        return dict(request_id='KREQ-000001',request_purpose='direction_discovery',
                    major=dict(name='计算机科学与技术',status='confirmed'),grade_stage='year_1',
                    candidate_path_ids=[],region='中国大陆',time_window='2026-2027',
                    retrieval_modes=['direction_discovery'],evidence_gaps=[])

    def test_direction_discovery_requires_explicit_context(self):
        request=self.request();self.assertEqual(knowledge.validate_request(request),[])
        for key in ('request_purpose','grade_stage'):
            invalid=copy.deepcopy(request);invalid.pop(key)
            self.assertTrue(knowledge.validate_request(invalid))
        request['request_purpose']='path_validation'
        self.assertTrue(knowledge.validate_request(request))

    def test_legacy_v1_request_remains_valid(self):
        request=self.request();request.pop('request_purpose');request.pop('grade_stage')
        request['retrieval_modes']=['background_similar','goal_oriented']
        self.assertEqual(knowledge.validate_request(request),[])

    def test_sensitive_v070_and_v1_fields_rejected(self):
        for field in ('psychological_context','psychological_observations','psychological_hypotheses',
                      'emotional_state','support_preferences','personal_facts','dialogic_self_understanding'):
            with self.subTest(field=field):
                request=self.request();request[field]={}
                self.assertTrue(knowledge.validate_request(request))

    def test_cold_start_stays_under_intake(self):
        current=confirmed_state();current['sections']['intake'].update(candidate_paths=[],candidate_generation_needed=True)
        self.assertEqual(state.route_for(current)[0],'profile_intake')
        self.assertEqual(state.auxiliary_for(current),'caplab-cold-start')
        self.assertNotIn('caplab-cold-start',state.STAGES)
        self.assertTrue(state.validate_patch(patch(current,'profile',{'profile_ready':True}),current))

    def test_incomplete_facts_and_blocked_status_do_not_start_planning(self):
        current=state.empty_state();self.assertIsNone(state.auxiliary_for(current))
        current=confirmed_state();current['sections']['intake'].update(candidate_paths=[])
        current['workflow_status']='blocked'
        self.assertEqual(state.route_for(current)[0],'blocked');self.assertIsNone(state.auxiliary_for(current))
        current['workflow_status']='active';current['section_meta']['intake']['status']='stale'
        self.assertIsNone(state.auxiliary_for(current))

    def test_confirmed_handoff_can_finish_cold_start(self):
        current=confirmed_state();current['sections']['intake'].update(candidate_paths=[],candidate_generation_needed=True)
        incoming=copy.deepcopy(current['sections']['intake'])
        incoming.update(candidate_paths=[dict(path_id='PTH-000001',name='软件工程')],candidate_generation_needed=False)
        proposal=patch(current,'intake',incoming)
        self.assertEqual(state.validate_patch(proposal,current),[])
        projected=copy.deepcopy(current)
        for change in proposal['changes']:state.apply_change(projected,change)
        state.update_registry(projected,proposal)
        self.assertEqual(state.validate_state(projected),[])
        self.assertEqual(state.route_for(projected)[0],'profile_confirmation')
        self.assertIsNone(state.auxiliary_for(projected))

    def test_auxiliary_actors_cannot_write_main_state(self):
        current=confirmed_state()
        for actor in ('caplab-cold-start','caplab-job-resume','caplab-job-mock-interview'):
            self.assertTrue(state.validate_patch(patch(current,'intake',ready_intake(),actor=actor),current))

    def test_psychology_skip_and_stop_saving_are_valid_optional_context(self):
        for mode in ('skipped','stop_saving'):
            current=confirmed_state()
            current['sections']['profile']['psychological_context']=dict(mode=mode,observation_ids=[],hypothesis_ids=[],revision_requests=[])
            self.assertEqual(state.validate_state(current),[])
        current['sections']['profile']['psychological_context']['observation_ids']=['OBS-000999']
        self.assertTrue(state.validate_state(current))
