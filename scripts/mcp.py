#!/usr/bin/env python3
"""MCP stdio desktop tools; action access is an explicit startup option."""
import json
import sys
from tools import exported,execute,BY_NAME
ALLOW='--allow-actions' in sys.argv[1:]
def handle(req):
    method=req.get('method');params=req.get('params',{})
    if method=='initialize':return {'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'angelos-open-llm','version':'1.2.0'}}
    if method=='ping':return {}
    if method=='tools/list':return {'tools':[dict(name=t['function']['name'],description=t['function']['description'],inputSchema=t['function']['parameters']) for t in exported() if ALLOW or BY_NAME[t['function']['name']]['read_only']]}
    if method=='tools/call':
        try:
            name=params['name']
            if name not in BY_NAME:raise ValueError('Unknown tool')
            if not ALLOW and not BY_NAME[name]['read_only']:raise ValueError('Actions are disabled. Start with --allow-actions to enable them.')
            result=execute(name,params.get('arguments',{}))
            return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False)}],'isError':not result.get('ok',False)}
        except Exception as exc:return {'content':[{'type':'text','text':str(exc)}],'isError':True}
    raise ValueError('Method not found')
def main():
    while True:
        line=sys.stdin.buffer.readline(1048577)
        if not line:return
        if len(line)>1048576:return
        req=None
        try:
            req=json.loads(line)
            if not isinstance(req,dict):raise ValueError('Invalid request')
            if 'id' not in req:continue
            response={'jsonrpc':'2.0','id':req['id'],'result':handle(req)}
        except Exception as exc:response={'jsonrpc':'2.0','id':req.get('id') if isinstance(req,dict) else None,'error':{'code':-32601 if str(exc)=='Method not found' else -32600,'message':str(exc)}}
        print(json.dumps(response,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
