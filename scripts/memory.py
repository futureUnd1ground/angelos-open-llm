"""Private bounded conversation memory, isolated by endpoint, model and persona."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

def file(config,endpoint):
    folder=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'angelos-open-llm'
    if folder.is_symlink():raise ValueError('Memory directory must not be a symlink')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700);folder.chmod(0o700)
    identity=json.dumps([endpoint,config.get('model',''),config.get('persona','angel')])
    path=folder/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
    if path.is_symlink():raise ValueError('Memory file must not be a symlink')
    return path

def dialogue(messages):
    return [{'role':m['role'],'content':m['content'][:8192]} for m in messages if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str) and m['content'].strip()][-80:]

def load(config,endpoint):
    path=file(config,endpoint)
    if not path.exists():return []
    if path.stat().st_mode&0o077:raise ValueError('Memory file permissions must be 600')
    with path.open('rb') as stream:data=stream.read(4*1024*1024+1)
    if len(data)>4*1024*1024:raise ValueError('Conversation memory is too large')
    rows=json.loads(data)
    if not isinstance(rows,list):raise ValueError('Invalid conversation memory')
    return dialogue(rows)

def save(config,endpoint,messages):
    path=file(config,endpoint)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as temp:
        try:
            os.chmod(temp.name,0o600);json.dump(dialogue(messages),temp,ensure_ascii=False);temp.close();os.replace(temp.name,path)
        finally:
            if Path(temp.name).exists():Path(temp.name).unlink()

def forget(config,endpoint):file(config,endpoint).unlink(missing_ok=True)
