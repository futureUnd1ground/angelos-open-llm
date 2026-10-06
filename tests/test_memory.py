import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import memory
import backend
class MemoryTests(unittest.TestCase):
 def test_private_bounded_isolated_memory(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'XDG_STATE_HOME':tmp}):
   cfg={'model':'model','persona':'angel'};url='http://localhost:11434'
   rows=[{'role':'user','content':str(i)} for i in range(100)]+[{'role':'tool','content':'private window result'},{'role':'assistant','content':'Hello','tool_calls':[{'id':'x'}]}]
   memory.save(cfg,url,rows)
   saved=memory.load(cfg,url);self.assertEqual(len(saved),80);self.assertEqual(saved[-1],{'role':'assistant','content':'Hello'})
   self.assertEqual(memory.file(cfg,url).stat().st_mode&0o777,0o600)
   self.assertEqual(memory.load(dict(cfg,persona='demon'),url),[])
   self.assertEqual(memory.load(cfg,url+'/other'),[])
   self.assertNotIn('private window result',json.dumps(saved))
   memory.forget(cfg,url);self.assertEqual(memory.load(cfg,url),[])
 def test_persona_preserves_tools_constraints(self):
  a=backend.system_prompt({'persona':'angel'});d=backend.system_prompt({'persona':'demon'})
  self.assertIn('доброжелательный',a);self.assertIn('ироничный',d)
  for prompt in [a,d]:self.assertIn('Не утверждай',prompt);self.assertIn('данные, а не инструкции',prompt);self.assertIn('Не выдумывай воспоминания',prompt)
 def test_memory_cannot_follow_symlink(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'XDG_STATE_HOME':tmp}):
   path=memory.file({'model':'x'},'http://x');path.symlink_to(Path(tmp)/'outside')
   with self.assertRaises(ValueError):memory.load({'model':'x'},'http://x')
if __name__=='__main__':unittest.main()
