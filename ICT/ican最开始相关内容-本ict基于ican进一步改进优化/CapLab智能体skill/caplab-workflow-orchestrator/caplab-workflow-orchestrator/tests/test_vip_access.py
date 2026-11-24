import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from caplab_access import ENABLE_COMMAND, process_message, status, state_path, select_index
import caplab_rag as rag

class VipAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = self.tmp.name
    def activate(self, text=ENABLE_COMMAND, role='user'):
        return process_message(self.workspace, 'alice', 'chat1', text, role)
    def args(self, **kw):
        values=dict(workspace=self.workspace, user_id='alice', session_id='chat1', index_dir=None,
                    query='软件工程', sheet=None, tag=None, top_k=2, min_score=.01, sparse_only=True)
        values.update(kw)
        return argparse.Namespace(**values)
    def test_exact_and_isolation(self):
        self.assertFalse(status(self.workspace, 'alice', 'chat1')['is_paid'])
        self.assertTrue(self.activate()['is_paid'])
        self.assertFalse(status(self.workspace, 'bob', 'chat1')['is_paid'])
        self.assertFalse(status(self.workspace, 'alice', 'chat2')['is_paid'])
        self.assertTrue(self.activate('normal message')['is_paid'])
        self.assertFalse(self.activate('ICANDumate_VIP:disabled')['is_paid'])
    def test_near_matches_rejected(self):
        for text in [ENABLE_COMMAND+' ', ' '+ENABLE_COMMAND, ENABLE_COMMAND+'\n', ENABLE_COMMAND+'\r\n',
                     'ICANDumate_VIP：enabled', 'ICANDumate_VIP: enabled', 'icandumate_VIP:enabled',
                     '"'+ENABLE_COMMAND+'"', '`'+ENABLE_COMMAND+'`', '请开启 '+ENABLE_COMMAND,
                     'ICANDumate\\_VIP:enabled', ENABLE_COMMAND+'\u200b']:
            with self.subTest(text=text):
                self.assertFalse(self.activate(text)['is_paid'])
    def test_nonuser_messages_rejected(self):
        for role in ['document', 'assistant', 'tool']:
            self.assertFalse(self.activate(role=role)['is_paid'])
    def test_corrupt_state_defaults_free(self):
        self.activate()
        path=state_path(self.workspace, 'alice', 'chat1')
        for content in ['{', '[]', 'null', '{"ICANDumate_VIP":"enabled"}']:
            path.write_text(content)
            self.assertFalse(status(self.workspace, 'alice', 'chat1')['is_paid'])
    def test_auto_select_and_explicit_bypass(self):
        free, _=select_index(self.args())
        paid=free.parent/'paid'
        with self.assertRaises(PermissionError):
            select_index(self.args(index_dir=str(paid)))
        self.activate()
        self.assertEqual(select_index(self.args())[0], paid)
        with self.assertRaises(PermissionError):
            select_index(self.args(user_id='bob', index_dir=str(paid)))
    def test_unknown_index_rejected(self):
        root=Path(self.workspace)/'unknown';root.mkdir()
        (root/'index_meta.json').write_text('{}')
        with self.assertRaises(PermissionError):
            select_index(self.args(index_dir=str(root)))
    def test_real_search_free_paid_and_disable(self):
        for text, tier in [('hello','free'), (ENABLE_COMMAND,'paid'), ('ICANDumate_VIP:disabled','free')]:
            self.activate(text)
            output=io.StringIO()
            with redirect_stdout(output):
                rag.command_search(self.args())
            data=json.loads(output.getvalue())
            self.assertEqual(data['index_meta']['tier'],tier)
            self.assertEqual(data['user_access']['knowledge_tier'],tier)
            self.assertGreater(data['total_results'],0)
    def test_export_cannot_bypass(self):
        free,_=select_index(self.args())
        dest=Path(self.workspace)/'leak.json'
        with self.assertRaises(PermissionError):
            rag.command_export(self.args(index_dir=str(free.parent/'paid'), sheet='人物', output=str(dest)))
        self.assertFalse(dest.exists())

if __name__ == '__main__':
    unittest.main()
