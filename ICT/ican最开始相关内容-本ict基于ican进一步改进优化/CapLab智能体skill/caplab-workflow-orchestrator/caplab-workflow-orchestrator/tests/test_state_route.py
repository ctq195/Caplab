from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from fixtures import ready_intake


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "caplab_state.py"
SPEC = importlib.util.spec_from_file_location("caplab_state", SCRIPT)
state_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(state_module)


def _intake_confirmed():
    intake = ready_intake()
    state = state_module.empty_state()
    state["sections"]["intake"] = intake
    state["section_meta"]["intake"]["status"] = "confirmed"
    state_module.update_registry(state, state["sections"])
    return state


class StateRouteTests(unittest.TestCase):
    def test_unconfirmed_profile_cannot_enter_path_convergence(self):
        state = _intake_confirmed()
        state["sections"]["profile"] = {"profile_ready": True, "confirmation_status": "draft"}
        state["section_meta"]["profile"]["status"] = "draft"
        stage, _ = state_module.route_for(state)
        self.assertEqual(stage, "profile_confirmation")

    def test_confirmed_profile_can_enter_path_convergence(self):
        state = _intake_confirmed()
        state["sections"]["profile"] = {"profile_ready": True, "confirmation_status": "confirmed"}
        state["section_meta"]["profile"]["status"] = "confirmed"
        stage, _ = state_module.route_for(state)
        self.assertEqual(stage, "path_convergence")


if __name__ == "__main__":
    unittest.main()
