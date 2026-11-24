import json
import tempfile
import unittest
from pathlib import Path

from caplab_test_archive import append_event, close_archive, create_archive, show_archive


class TestArchiveTests(unittest.TestCase):
    code = "31415926"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / ".caplab-test-archives"

    def tearDown(self):
        self.temporary.cleanup()

    def test_ids_increment_and_archives_are_separate(self):
        first = create_archive(self.root, self.code)
        second = create_archive(self.root, self.code)
        self.assertEqual(first["save_id"], "SAVE-000001")
        self.assertEqual(second["save_id"], "SAVE-000002")
        append_event(self.root, first["save_id"], "user", "first only", self.code)
        self.assertEqual(show_archive(self.root, second["save_id"], self.code)["transcript"], [])

    def test_append_and_close(self):
        save_id = create_archive(self.root, self.code)["save_id"]
        append_event(self.root, save_id, "user", "case input", self.code)
        self.assertEqual(show_archive(self.root, save_id, self.code)["transcript"][0]["text"], "case input")
        self.assertEqual(close_archive(self.root, save_id, self.code)["status"], "closed")
        with self.assertRaises(ValueError):
            append_event(self.root, save_id, "assistant", "late write", self.code)

    def test_metadata_never_links_formal_state(self):
        save_id = create_archive(self.root, self.code)["save_id"]
        metadata = json.loads((self.root / save_id / "session.json").read_text(encoding="utf-8"))
        self.assertIsNone(metadata["formal_state_link"])
        self.assertFalse(metadata["cross_test_memory_allowed"])

    def test_wrong_access_code_cannot_create_or_read(self):
        with self.assertRaises(PermissionError):
            create_archive(self.root, "00000000")
        save_id = create_archive(self.root, self.code)["save_id"]
        with self.assertRaises(PermissionError):
            show_archive(self.root, save_id, "00000000")


if __name__ == "__main__":
    unittest.main()
