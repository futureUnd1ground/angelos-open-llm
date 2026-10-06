import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import backend as b
import runtime
import tools
import mcp

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':self.tmp.name});self.env.start()
        self.calls=[];self.responses=[]
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                owner.calls.append((self.path,None,self.headers.get('Authorization')))
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'models':[{'name':'qwen3:4b'}],'data':[{'id':'model'}]}).encode())
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.calls.append((self.path,body,self.headers.get('Authorization')))
                self.send_response(200);self.end_headers()
                if self.path=='/api/pull':
                    self.wfile.write(b'{"status":"pulling","completed":5,"total":10}\n{"status":"success"}\n');return
                msg=owner.responses.pop(0)
                self.wfile.write(json.dumps({'message':msg,'choices':[{'message':msg}]}).encode())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.cfg={'url':f'http://127.0.0.1:{self.server.server_port}','protocol':'ollama','model':'qwen3:4b','maxSteps':8}
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.env.stop();self.tmp.cleanup()
    def events(self,req):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):b.agent(req)
        return [json.loads(line) for line in out.getvalue().splitlines()]
    def call(self,name,args):return {'id':'call1','function':{'name':name,'arguments':args}}
    def test_native_read_cycle(self):
        self.responses=[{'tool_calls':[self.call('get_power',{})]},{'content':'Done'}]
        events=self.events({'config':self.cfg,'messages':[{'role':'user','content':'power?'}]})
        self.assertEqual(events[-1]['pending'],[])
        second=self.calls[1][1]['messages'][-1];self.assertEqual(second['role'],'tool');self.assertEqual(second['tool_name'],'get_power');self.assertNotIn('tool_call_id',second)
    def test_openai_wire(self):
        self.cfg['protocol']='openai';self.cfg['url']+='/v1'
        self.responses=[{'tool_calls':[self.call('get_power','{}')]},{'content':'Done'}]
        events=self.events({'config':self.cfg,'messages':[{'role':'user','content':'power?'}]})
        self.assertEqual(self.calls[0][0],'/v1/chat/completions')
        row=self.calls[1][1]['messages'][-1];self.assertEqual(row['tool_call_id'],'call1');self.assertNotIn('tool_name',row)
    def test_confirmation_and_rejection(self):
        self.responses=[{'tool_calls':[self.call('set_theme',{'mode':'dark'})]}]
        with patch.object(b,'execute') as execute:
            events=self.events({'config':self.cfg,'messages':[{'role':'user','content':'dark'}]})
            execute.assert_not_called()
            state=events[-1];self.assertEqual(len(state['pending']),1)
            self.responses=[{'content':'Rejected'}]
            events=self.events({'op':'resolve','config':self.cfg,'messages':state['messages'],'pending':state['pending'],'rounds':state['rounds'],'approved':False})
            execute.assert_not_called();self.assertEqual(events[-1]['pending'],[])
            self.assertIn('отклонено',self.calls[-1][1]['messages'][-1]['content'])
    def test_approval_auto_and_invalid_tool(self):
        self.responses=[{'tool_calls':[self.call('set_theme',{'mode':'dark'})]},{'content':'Done'}]
        self.cfg['autoActions']=True
        with patch.object(b,'execute',return_value={'ok':True,'result':'ok'}) as execute:
            self.events({'config':self.cfg,'messages':[{'role':'user','content':'dark'}]});execute.assert_called_once_with('set_theme',{'mode':'dark'})
        self.responses=[{'tool_calls':[self.call('run_shell',{'command':'rm -rf /'})]},{'content':'Cannot'}]
        with patch.object(b,'execute') as execute:
            self.events({'config':self.cfg,'messages':[{'role':'user','content':'hi'}]});execute.assert_not_called()
    def test_resolve_tampering_rejected(self):
        with self.assertRaises(ValueError):self.events({'op':'resolve','config':self.cfg,'messages':[],'pending':[self.call('set_theme',{'mode':'dark'})],'approved':True})
    def test_credentials_isolated_private(self):
        b.save_key(self.cfg,'secret-test');self.assertEqual(b.credential_file().stat().st_mode&0o777,0o600)
        b.models(self.cfg);self.assertEqual(self.calls[-1][2],'Bearer secret-test')
        other=dict(self.cfg,url=self.cfg['url']+'/other');b.models(other);self.assertIsNone(self.calls[-1][2])
        b.save_key(self.cfg,'');self.assertEqual(b.credentials(),{})
    def test_local_download_progress(self):
        events=[];runtime.pull(self.cfg,'qwen3:4b',lambda kind,**args:events.append({'type':kind,**args}),b.urllib.request.build_opener(b.NoRedirect()),'')
        self.assertEqual(events[0]['completed'],5);self.assertEqual(events[-1]['type'],'runtime')
        with self.assertRaises(ValueError):runtime.local_config(dict(self.cfg,url='https://example.com'))
    def test_invalid_arguments_and_readonly_mcp(self):
        for name,args in [('switch_workspace',{'workspace':True}),('set_theme',{'mode':'oops'}),('get_power',{'extra':1})]:
            with self.assertRaises(ValueError):tools.definition(name,args)
        names=[t['name'] for t in mcp.handle({'method':'tools/list'})['tools']]
        self.assertIn('get_windows',names);self.assertNotIn('set_theme',names)
        self.assertTrue(mcp.handle({'method':'tools/call','params':{'name':'set_theme','arguments':{'mode':'dark'}}})['isError'])
    def test_no_redirect_and_model_lists(self):
        with self.assertRaises(ValueError):b.NoRedirect().redirect_request(None,None,302,'',{},'https://other.test')
        self.assertEqual(b.models(self.cfg),['qwen3:4b']);self.cfg['protocol']='openai';self.assertEqual(b.models(self.cfg),['model'])
    def test_iteration_limit(self):
        self.cfg['maxSteps']=2;self.responses=[{'tool_calls':[self.call('get_power',{})]}]*2
        events=self.events({'config':self.cfg,'messages':[{'role':'user','content':'keep going'}]})
        self.assertEqual(len(self.calls),2);self.assertIn('предел',events[-2]['text'])
if __name__=='__main__':unittest.main()
