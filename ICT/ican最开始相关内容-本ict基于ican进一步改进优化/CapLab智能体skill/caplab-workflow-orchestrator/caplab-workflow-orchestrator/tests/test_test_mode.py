import unittest

from caplab_test_mode import DEFAULT_CONFIG, classify, load_config


class TestModeCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(DEFAULT_CONFIG)

    def test_create_command_requires_payload_and_returns_create_action(self):
        result = classify(
            "上海师范大学商学院中法计算机测试存档 Save 31415926：这是第一轮很长的测试内容",
            self.config,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["action"], "create")
        self.assertIsNone(result["save_id"])
        self.assertEqual(result["test_input"], "这是第一轮很长的测试内容")
        self.assertFalse(result["formal_state_io_allowed"])

    def test_read_command_requires_full_save_id_and_code(self):
        result = classify("Read Save SAVE-000123 31415926：继续优化这份结果", self.config)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["action"], "read")
        self.assertEqual(result["save_id"], "SAVE-000123")
        self.assertEqual(result["test_input"], "继续优化这份结果")

    def test_fullwidth_input_is_normalized(self):
        result = classify("Ｒｅａｄ Ｓａｖｅ ＳＡＶＥ－０００１２３ ３１４１５９２６", self.config)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["save_id"], "SAVE-000123")

    def test_wrong_code_missing_id_and_missing_payload_are_rejected(self):
        invalid = (
            "Read Save SAVE-000123 00000000",
            "Read Save 000123 31415926",
            "Read Save SAVE-000123",
            "上海师范大学商学院中法计算机测试存档 Save 00000000：内容",
            "上海师范大学商学院中法计算机测试存档 Save 31415926：",
        )
        for value in invalid:
            with self.subTest(value=value):
                result = classify(value, self.config)
                self.assertEqual(result["mode"], "test_command_rejected")
                self.assertFalse(result["formal_state_io_allowed"])

    def test_legacy_loose_trigger_does_not_create_archive(self):
        result = classify("上海师范大学商学院中法计算机测试", self.config)
        self.assertEqual(result["mode"], "normal")


if __name__ == "__main__":
    unittest.main()
