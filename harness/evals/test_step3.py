import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT,read,digest,source_digest
from verify_step import command
class Step3(unittest.TestCase):
 def test_checks_registered_to_repo_local_script(self):
  for name in ('12-passes','observer-complete'):
   self.assertEqual(command(ROOT,name),[sys.executable,str(ROOT/'tools/verify.py'),'--check',name])
 def test_controller_provenance(self):
  receipt=read(ROOT/'governance/adapter-revision.json')
  for name,row in receipt['files'].items():
   self.assertEqual(digest((ROOT/name).read_bytes()),row['adapter_sha256'])
   self.assertEqual(digest((ROOT/'qa-features/governance/source'/name).read_bytes()),row['upstream_sha256'])
if __name__=='__main__':unittest.main()
