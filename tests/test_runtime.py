import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runtime as r
class RuntimeTests(unittest.TestCase):
 def archive(self,members):
  raw=io.BytesIO()
  with tarfile.open(fileobj=raw,mode='w') as tar:
   for name,content,link in members:
    entry=tarfile.TarInfo(name);entry.mode=0o755
    if link:entry.type=tarfile.SYMTYPE;entry.linkname=link;tar.addfile(entry)
    else:entry.size=len(content);tar.addfile(entry,io.BytesIO(content))
  return subprocess.run(['zstd','-q','-c'],input=raw.getvalue(),capture_output=True,check=True).stdout
 def install(self,data,folder,digest=None):
  assets={'x86_64':('amd64',len(data),digest or hashlib.sha256(data).hexdigest())}
  with patch.dict(os.environ,{'XDG_DATA_HOME':folder}),patch.object(r.platform,'machine',return_value='x86_64'),patch.object(r,'binary',return_value=None),patch.object(r,'ASSETS',assets),patch.object(r.urllib.request,'urlopen',return_value=io.BytesIO(data)),patch.object(r.shutil,'disk_usage',return_value=type('Disk',(),{'free':10*1024**3})()):
   r.install(lambda *args,**kwargs:None)
 def test_pinned_archive_installs_executable(self):
  data=self.archive([('bin/ollama',b'#!/bin/sh\n',None),('lib/model.so',b'library',None),('lib/link.so',b'', 'model.so')])
  with tempfile.TemporaryDirectory() as tmp:
   self.install(data,tmp);base=Path(tmp)/'angelos-open-llm/runtime'
   self.assertTrue((base/'bin/ollama').stat().st_mode&0o100);self.assertEqual((base/'lib/link.so').read_bytes(),b'library')
 def test_checksum_and_escape_rejected(self):
  good=self.archive([('bin/ollama',b'bin',None)])
  bad=self.archive([('../escaped',b'oops',None)])
  link=self.archive([('lib/escape',b'', '../../../escape')])
  with tempfile.TemporaryDirectory() as tmp:
   for data,digest in [(good,'0'*64),(bad,None),(link,None)]:
    with self.assertRaises(ValueError):self.install(data,tmp,digest)
   self.assertFalse((Path(tmp)/'escaped').exists());self.assertFalse((Path(tmp)/'angelos-open-llm/runtime').exists())
 def test_existing_runtime_skips_network(self):
  with patch.object(r,'binary',return_value='/usr/bin/ollama'),patch.object(r.urllib.request,'urlopen') as request:
   r.install(lambda *args,**kwargs:None);request.assert_not_called()
if __name__=='__main__':unittest.main()
