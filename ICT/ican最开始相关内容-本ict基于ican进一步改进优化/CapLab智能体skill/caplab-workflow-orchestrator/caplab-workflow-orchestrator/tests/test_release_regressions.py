import argparse, datetime as dt, io, json, os, shutil, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import numpy as np
import caplab_index as ix
import caplab_quality as q
import caplab_rag as rag
import caplab_state as state
import caplab_bootstrap as boot
import caplab_test_archive as a
from fixtures import make_index, ready_intake

class IndexTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.src=make_index(self.root/'src');self.dst=self.root/'dst'
 def test_install_idempotency(self):
  self.assertEqual(ix.install_index(self.src,self.dst)['status'],'installed');self.assertEqual(ix.install_index(self.src,self.dst)['status'],'reused')
 def test_legacy_backup(self):
  shutil.copytree(self.src,self.dst);(self.dst/ix.MANIFEST).unlink();b=ix.install_index(self.src,self.dst)['backup'];self.assertTrue((Path(b)/'documents.json').exists())
 def test_empty_metadata_not_ready(self):
  p=self.root/'knowledge_index';p.mkdir();(p/'index_meta.json').write_text('{}')
  with self.assertRaises(boot.BootstrapError):boot.require_ready(self.root)
 def test_missing_file_no_partial_install(self):
  (self.src/'documents.json').unlink()
  with self.assertRaises(ix.IndexError):ix.install_index(self.src,self.dst)
  self.assertFalse(self.dst.exists())
 def test_hash_mismatch(self):
  (self.src/'documents.json').write_text('[]')
  with self.assertRaises(ix.IndexError):ix.install_index(self.src,self.dst)
 def test_unknown_content_preserved(self):
  self.dst.mkdir();(self.dst/'user.txt').write_text('keep')
  with self.assertRaises(ix.IndexError):ix.install_index(self.src,self.dst)
  self.assertEqual((self.dst/'user.txt').read_text(),'keep')
 def test_copy_failure_preserves_old(self):
  ix.install_index(self.src,self.dst);before=(self.dst/ix.MANIFEST).read_bytes();make_index(self.src,tier='paid')
  with patch.object(ix.shutil,'copy2',side_effect=OSError('injected')):
   with self.assertRaises(OSError):ix.install_index(self.src,self.dst)
  self.assertEqual((self.dst/ix.MANIFEST).read_bytes(),before)
 def test_activation_failure_rolls_back(self):
  ix.install_index(self.src,self.dst);before=(self.dst/ix.MANIFEST).read_bytes();make_index(self.src,tier='paid');real=os.replace
  def replace(x,y):
   if '.stage-' in Path(x).name:raise OSError('injected')
   return real(x,y)
  with patch.object(ix.os,'replace',side_effect=replace):
   with self.assertRaises(OSError):ix.install_index(self.src,self.dst)
  self.assertEqual((self.dst/ix.MANIFEST).read_bytes(),before)
 def test_backup_restorable(self):
  ix.install_index(self.src,self.dst);make_index(self.src,tier='paid');b=ix.install_index(self.src,self.dst)['backup'];ix.install_index(b,self.dst);self.assertEqual(ix.validate_index(self.dst)['tier'],'free')
 def test_bad_vectors(self):
  make_index(self.src,dense=True);np.save(self.src/'embeddings.npy',np.ones((2,2),dtype='float32'))
  with self.assertRaises(ix.IndexError):ix.seal_index(self.src)
  (self.src/'embeddings.npy').write_bytes(b'broken')
  with self.assertRaises(ix.IndexError):ix.seal_index(self.src)
 def test_temporary_workspace_requires_flag(self):
  make_index(self.root/'knowledge_index')
  with self.assertRaises(boot.BootstrapError):boot.ensure_knowledge(self.root)
  self.assertEqual(boot.ensure_knowledge(self.root,allow_temporary=True)['status'],'reused')
 def test_sparse_without_vectors(self):self.assertFalse(ix.validate_index(self.src)['dense_enabled'])
 def test_symlink_refused(self):
  self.dst.symlink_to(self.src,target_is_directory=True)
  with self.assertRaises(ix.IndexError):ix.install_index(self.src,self.dst)
 def test_concurrent_install_refused(self):
  lock=self.root/'.dst.install.lock';lock.write_text('busy')
  with self.assertRaises(ix.IndexError):ix.install_index(self.src,self.dst)
  self.assertTrue(lock.exists())

class RecordingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'.caplab-test-archives';self.code='31415926';self.sid=a.create_archive(self.root,self.code)['save_id'];a.append_event(self.root,self.sid,'user','before',self.code)
 def test_pause_blocks_all_roles(self):
  p=self.root/self.sid/'transcript.jsonl';before=p.read_bytes();a.pause_archive(self.root,self.sid,self.code)
  for role in ('user','assistant','system_event'):
   with self.assertRaises(ValueError):a.append_event(self.root,self.sid,role,'sensitive',self.code)
  self.assertEqual(p.read_bytes(),before)
 def test_show_does_not_resume(self):
  a.pause_archive(self.root,self.sid,self.code);self.assertEqual(a.show_archive(self.root,self.sid,self.code)['metadata']['status'],'paused')
  with self.assertRaises(ValueError):a.append_event(self.root,self.sid,'user','no',self.code)
 def test_explicit_resume(self):
  a.pause_archive(self.root,self.sid,self.code)
  with self.assertRaises(ValueError):a.resume_archive(self.root,self.sid,self.code)
  a.resume_archive(self.root,self.sid,self.code,True);a.append_event(self.root,self.sid,'user','consented',self.code)
 def test_closed_cannot_resume(self):
  a.pause_archive(self.root,self.sid,self.code);a.close_archive(self.root,self.sid,self.code)
  with self.assertRaises(ValueError):a.resume_archive(self.root,self.sid,self.code,True)
 def test_independent_archive(self):
  a.pause_archive(self.root,self.sid,self.code);sid=a.create_archive(self.root,self.code)['save_id'];a.append_event(self.root,sid,'user','other context',self.code);self.assertEqual(a.show_archive(self.root,self.sid,self.code)['metadata']['status'],'paused')

class QualityTests(unittest.TestCase):
 day=dt.date(2026,9,20)
 def doc(self,fields):return dict(doc_id='d',sheet='test',fields=fields,source_ids=[],claim_ids=[])
 def test_blocked_statuses(self):
  for val in ('stale','rejected','pending_human_review','EXPIRED_FOR_ACTION','待当季核验','MONITORING'):
   with self.subTest(val=val):self.assertFalse(q.document_quality(self.doc({'时效状态':val}),{},{},self.day)['allowed'])
 def test_expiration_and_unknown_date(self):
  self.assertFalse(q.document_quality(self.doc({'valid_until':'2026-09-19'}),{},{},self.day)['allowed']);v=q.document_quality(self.doc({'valid_until':'2026年末'}),{},{},self.day);self.assertTrue(v['allowed']);self.assertFalse(v['actionable'])
 def test_history_reference_only(self):
  v=q.document_quality(self.doc({'核验状态':'HISTORICAL_VERIFIED'}),{},{},self.day);self.assertEqual(v['status'],'historical_reference');self.assertFalse(v['actionable'])
 def test_unknown_not_verified(self):
  v=q.document_quality(self.doc({}),{},{},self.day);self.assertEqual(v['status'],'unknown');self.assertFalse(v['actionable'])
 def test_valid_still_needs_live_check(self):
  v=q.document_quality(self.doc({'review_status':'human_approved','valid_until':'2026-12-31'}),{},{},self.day);self.assertTrue(v['allowed']);self.assertTrue(v['needs_live_verification'])
 def test_linked_rejection(self):
  d=self.doc({});d['source_ids']=['S'];self.assertFalse(q.document_quality(d,{'S':{'review_status':'stale'}},{},self.day)['allowed']);d['source_ids']=[];d['claim_ids']=['C'];self.assertFalse(q.document_quality(d,{}, {'C':[{'review_status':'rejected'}]},self.day)['allowed'])
 def test_future_effective_date(self):
  self.assertFalse(q.document_quality(self.doc({'valid_from':'2026-10-01','review_status':'human_approved'}),{},{},self.day)['allowed'])
 def test_job_14_days(self):
  d=self.doc({'最后核验日期':'2026-09-01'});d['sheet']='06_招聘岗位';self.assertFalse(q.document_quality(d,{},{},self.day)['allowed'])
 def test_both_channels_filter_before_top_k(self):
  from test_caplab_rag import document
  docs=[document(1,'软件 软件 软件','E1',''),document(2,'软件','E2','')];docs[0]['fields']={'review_status':'stale'};allowed,_,_=q.filter_documents(docs,{},{},self.day);inv=rag.build_inverted_index(docs)
  sparse=rag.search_index(docs,inv,rag.compute_idf(docs,inv),'软件',top_k=1,allowed_indices=allowed);dense=rag.dense_search(docs,np.array([[1.,0.],[.1,0.]]),np.array([1.,0.]),None,None,1,allowed_indices=allowed)
  self.assertEqual([v['doc_index'] for v in sparse],[1]);self.assertEqual([v['doc_index'] for v in dense],[1])
 def test_search_export_exclude_stale(self):
  from test_caplab_rag import document
  docs=[document(1,'软件工程','E1',''),document(2,'软件工程','E2','')];docs[0]['fields']={'review_status':'stale'}
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);idx=make_index(root/'idx',docs=docs);args=argparse.Namespace(index_dir=str(idx),workspace=t,user_id='u',session_id='s',query='软件工程',sheet='测试',tag=None,top_k=10,min_score=.01,sparse_only=True,output=str(root/'out.json'));out=io.StringIO()
   with redirect_stdout(out):rag.command_search(args)
   self.assertEqual([x['entity_id'] for x in json.loads(out.getvalue())['results']],['E2'])
   with redirect_stdout(io.StringIO()):rag.command_export(args)
   self.assertEqual([x['entity_id'] for x in json.loads((root/'out.json').read_text())],['E2'])

class VersionTests(unittest.TestCase):
 def test_current_and_old_versions(self):
  from test_migration import patch as mk
  st=state.empty_state();p=mk(st,'intake',ready_intake());self.assertEqual(p['skill_version'],'2.2.0');self.assertEqual(state.validate_patch(p,st),[])
  for v in ('1.4.0','2.0.0','2.0.1','2.0.2','2.1.0','2.1.1','9.0.0'):
   p['skill_version']=v;self.assertTrue(any('re-propose' in x for x in state.validate_patch(p,st)))
 def test_version_does_not_bypass_facts(self):
  from test_migration import patch as mk
  st=state.empty_state();value=ready_intake();value['personal_facts']['graduation_year']['value']=2020;self.assertTrue(state.validate_patch(mk(st,'intake',value),st))

if __name__=='__main__':unittest.main()
