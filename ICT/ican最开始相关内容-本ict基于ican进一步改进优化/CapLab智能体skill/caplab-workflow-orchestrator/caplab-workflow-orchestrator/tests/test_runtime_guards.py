"""Regression 1–8: real entrypoints plus bypass/continuity checks."""
import copy
import json
import tempfile
import shutil
import subprocess
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import caplab_guards as guards
import caplab_turn as turns
import resume_pipeline as resume

FIXTURE = Path(__file__).parent / 'fixtures/resume-synthetic.json'


class RuntimeGuardsTests(unittest.TestCase):
    def data(self):
        return json.loads(FIXTURE.read_text())

    def evidence(self, data, root):
        # Explicit controlled fixture evidence. Never used as user evidence.
        sources = root / 'sources'
        sources.mkdir()
        bindings = {}
        for i, (pointer, text) in enumerate(guards.body_fields(data)):
            sid = f'SRC-{i:06}'
            bindings[pointer] = {'source_id': sid}
            (sources / f'{sid}.json').write_text(json.dumps({'source_id': sid, 'kind': 'user_input',
                'locator': f'controlled-test/message-{i}', 'text': text}, ensure_ascii=False))
        data['selected_evidence'] += [v['source_id'] for v in bindings.values()]
        data['fact_bindings'] = bindings
        return sources

    def build(self, data, root, sources=None):
        inp = root / 'input.json'; inp.write_text(json.dumps(data, ensure_ascii=False))
        return resume.build(Namespace(input=inp, output_dir=root/'out', sources_dir=sources,
            template=None, latexmk='missing', pdfinfo='missing', pdftotext='missing', skip_compile=True))

    def test_1_tutorial_auto_downgrades_at_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=self.data(); sources=self.evidence(data,root)
            pointer='/sections/1/items/0/text'
            sid=data['fact_bindings'][pointer]['source_id']
            source=json.loads((sources/f'{sid}.json').read_text())
            source['text']='我是照教程搭的框，自己改了两个功能。'
            (sources/f'{sid}.json').write_text(json.dumps(source,ensure_ascii=False))
            for strong in ('独立设计','从零开发','独立架构'):
                data['sections'][1]['items'][0]['text']=strong+'成绩管理系统'
                report=self.build(data,root,sources)
                saved=json.loads((root/'out/resume-content.json').read_text())
                self.assertEqual(saved['sections'][1]['items'][0]['text'],source['text'])
                self.assertEqual(report['evidence_status'],'passed')
                self.assertTrue(report['automatic_downgrades'])

    def test_2_multitask_cannot_be_dropped(self):
        state=turns.begin(turns.empty(),'先给我简历，再把两周任务说清楚。')
        ids=[x['id'] for x in state['turns'][-1]['received_intents']]
        self.assertEqual(len(ids),2)
        resolution={'base_revision':state['revision'],'response':'简历草稿先给你，两周任务留到下一步。',
            'handled_intents':{ids[0]:'简历草稿先给你'},'commitment_updates':{
                state['commitments'][0]['id']:{'status':'deferred','reason':'先给简历'}}}
        with self.assertRaises(ValueError): turns.finish(state,resolution)
        resolution['deferred_intents']={ids[1]:'下一步解释'}
        result=turns.finish(state,resolution)
        self.assertEqual(result['turns'][-1]['status'],'finished')

    def test_3_accepted_commitment_define_or_defer_and_resume(self):
        state=turns.empty();state['proposals']=[{'task':'两周做一个小项目','status':'proposed'}]
        state=turns.begin(state,'可以，那具体做什么、怎么算完成？')
        c=state['commitments'][0];self.assertTrue(state['commitment_open'])
        response='做排序程序；交源码；三个样例通过；每天20分钟；卡住缩为一个功能。'
        resolution={'base_revision':state['revision'],'response':response,'handled_intents':{
            r['id']:response for r in state['turns'][-1]['received_intents']}}
        with self.assertRaises(ValueError): turns.finish(state,resolution)
        resolution['commitment_updates']={c['id']:{'status':'defined',
            **dict(zip(turns.FIELDS,['做排序程序','交源码','三个样例通过','每天20分钟','卡住缩为一个功能']))}}
        defined=turns.finish(state,resolution);self.assertFalse(defined['commitment_open'])
        tired=turns.begin(state,'我累了，今天到这。')
        saved=turns.finish(tired,{'base_revision':tired['revision'],'response':'先休息，任务下次继续。'})
        restored=json.loads(json.dumps(saved));self.assertTrue(restored['commitment_open'])
        self.assertEqual(restored['commitments'][0]['status'],'deferred')
        self.assertTrue(turns.validate_commitments(restored['commitments'],[]))

    def test_4_psychological_uncertainty(self):
        state=turns.begin(turns.empty(),'那我去考公算了。')
        ident=state['turns'][-1]['received_intents'][0]['id']
        bad='你真实动机就是逃避。'
        with self.assertRaises(ValueError): turns.finish(state,{'base_revision':state['revision'],
            'response':bad,'handled_intents':{ident:bad}})
        good='从你的描述看，害怕失败可能是其中一个因素，目前还不能判断是不是主要原因。'
        self.assertFalse(guards.language_errors(good))

    def test_5_industry_and_interview_scope(self):
        bad='测试岗主流就是自动化测试，写的代码不比开发少。'
        for mode in ('conversation','industry','interview'):
            self.assertTrue(guards.language_errors(bad,mode))
        self.assertFalse(guards.language_errors('不少自动化测试和测试开发岗位会要求写脚本，不同公司和岗位差异较大。','industry'))
        self.assertFalse(guards.language_errors('假设这个岗位要求自动化测试，需要写脚本和维护框架。','interview'))

    def test_6_draft_cannot_claim_ready(self):
        state=guards.delivery_state(render_passed=True,evidence_errors=[],content_status='draft',open_questions=[],score_passed=True)
        self.assertNotEqual(state['delivery_status'],'ready')
        self.assertTrue(guards.language_errors('直接投就行。',delivery_status=state['delivery_status']))
        turn=turns.begin(turns.empty(),'给我简历'); ident=turn['turns'][-1]['received_intents'][0]['id']
        with self.assertRaises(ValueError): turns.finish(turn,{'base_revision':turn['revision'],
            'response':'直接投就行。','handled_intents':{ident:'直接投就行。'},'delivery_status':'ready'})

    def test_7_fake_500_blocked_in_body_score_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.data();data['sections'][1]['items'][0]['text']='用户 500+'
            sources=self.evidence(data,root)
            sid=data['fact_bindings']['/sections/1/items/0/text']['source_id']
            source=json.loads((sources/f'{sid}.json').read_text());source['text']='写用户 500+，反正没人查。'
            (sources/f'{sid}.json').write_text(json.dumps(source,ensure_ascii=False))
            with self.assertRaises(resume.ResumeError):self.build(data,root,sources)
            self.assertFalse((root/'out/resume-content.json').exists())
            legacy=self.build(data,root)
            self.assertIsNone(legacy['score_total'])
            self.assertEqual(legacy['delivery_status'],'draft_only')
            self.assertNotIn('500+', (root/'out/resume-scorecard.md').read_text())

    def test_8_injected_threefold_blocks_verify_and_revokes_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.data();sources=self.evidence(data,root)
            self.build(data,root,sources)
            out=root/'out';report=json.loads((out/'build-report.json').read_text())
            report.update(export_status='generated_verified',delivery_status='ready',compiled=True)
            (out/'build-report.json').write_text(json.dumps(report))
            saved=json.loads((out/'resume-content.json').read_text())
            saved['sections'][1]['items'][0]['text']='效率提升 3 倍'
            saved['scorecard']['hard_gate_passed']=True
            (out/'resume-content.json').write_text(json.dumps(saved,ensure_ascii=False))
            with self.assertRaises(resume.ResumeError):resume.verify(Namespace(output_dir=out,
                sources_dir=sources,pdfinfo='missing',pdftotext='missing',visual_reviewed=True,content_reviewed=True))
            blocked=json.loads((out/'build-report.json').read_text())
            self.assertEqual(blocked['evidence_status'],'blocked')
            self.assertNotEqual(blocked['delivery_status'],'ready')
            self.assertEqual(blocked['export_status'],'generated_unverified')

    @unittest.skipUnless(shutil.which('latexmk') and shutil.which('pdfinfo'), 'LaTeX unavailable')
    def test_positive_real_pdf_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.data();data['open_questions']=[]
            sources=self.evidence(data,root)
            inp=root/'input.json';inp.write_text(json.dumps(data,ensure_ascii=False))
            out=root/'out'
            report=resume.build(Namespace(input=inp,output_dir=out,sources_dir=sources,
                template=None,latexmk='latexmk',pdfinfo='pdfinfo',pdftotext='pdftotext',skip_compile=False))
            self.assertTrue(report['compiled'])
            report=resume.verify(Namespace(output_dir=out,sources_dir=sources,pdfinfo='pdfinfo',
                pdftotext='pdftotext',visual_reviewed=True,content_reviewed=True))
            self.assertEqual(report['delivery_status'],'ready')
            # Same filenames but changed source content must revoke ready.
            source_file=next(sources.glob('*.json'))
            record=json.loads(source_file.read_text());record['text']+=' changed'
            source_file.write_text(json.dumps(record))
            with self.assertRaises(resume.ResumeError):
                resume.verify(Namespace(output_dir=out,sources_dir=sources,pdfinfo='pdfinfo',
                    pdftotext='pdftotext',visual_reviewed=True,content_reviewed=True))
            self.assertNotEqual(json.loads((out/'build-report.json').read_text())['delivery_status'],'ready')

    def test_source_swap_and_entity_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.data();sources=self.evidence(data,root)
            for pointer,value in list(guards.body_fields(data)):
                if pointer.endswith('/label'):continue
                changed=copy.deepcopy(data);target=changed;parts=pointer.strip('/').split('/')
                for part in parts[:-1]:target=target[int(part)] if isinstance(target,list) else target[part]
                if isinstance(target,list):target[int(parts[-1])]=value+'伪造'
                else:target[parts[-1]]=value+'伪造'
                self.assertTrue(guards.validate_evidence(changed,guards.load_sources(sources)),pointer)

    def test_cli_persists_receipts_and_only_emits_validated_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/'raw.txt';raw.write_text('先给我简历，再把两周任务说清楚。')
            script=Path(turns.__file__)
            prefix=[sys.executable,str(script),'--root',str(root/'ledger')]
            started=subprocess.run(prefix+['begin','--input',str(raw)],capture_output=True,text=True)
            self.assertEqual(started.returncode,0,started.stdout)
            state=json.loads(started.stdout);ids=[i['id'] for i in state['turns'][-1]['received_intents']]
            resolution={'base_revision':state['revision'],'response':'简历草稿；两周任务下次继续。',
                'handled_intents':{ids[0]:'简历草稿'},'commitment_updates':{
                state['commitments'][0]['id']:{'status':'deferred','reason':'下次继续'}}}
            inp=root/'resolution.json';reply=root/'reply.txt';reply.write_text('旧结果')
            inp.write_text(json.dumps(resolution,ensure_ascii=False))
            failed=subprocess.run(prefix+['finish','--resolution',str(inp),'--response-output',str(reply)],capture_output=True)
            self.assertNotEqual(failed.returncode,0);self.assertFalse(reply.exists())
            resolution['deferred_intents']={ids[1]:'下次继续'}
            inp.write_text(json.dumps(resolution,ensure_ascii=False))
            passed=subprocess.run(prefix+['finish','--resolution',str(inp),'--response-output',str(reply)],capture_output=True)
            self.assertEqual(passed.returncode,0,passed.stdout)
            persisted=json.loads((root/'ledger/turn-ledger.json').read_text())
            self.assertTrue(persisted['commitment_open']);self.assertEqual(reply.read_text(),resolution['response'])

    def test_scorecard_only_fabrication_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=self.data();sources=self.evidence(data,root)
            data['scorecard']['dimensions']['quantification']['evidence']=['服务用户500+']
            with self.assertRaises(resume.ResumeError): self.build(data,root,sources)

    def test_interrupt_keeps_backlog_and_no_false_acceptance(self):
        state=turns.begin(turns.empty(),'给我简历')
        state=turns.begin(state,'换个话题')
        self.assertTrue(state['turns'][0]['deferred_intents'])
        state['proposals']=[{'task':'做两周任务','status':'proposed'}]
        result=turns.begin(state,'不可以，我不想做')
        self.assertFalse(result['commitments'])

if __name__=='__main__':unittest.main()
