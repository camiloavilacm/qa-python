"""Meaningful fail-closed checks for observation and result integrity."""
from pathlib import Path
import sys,unittest,tempfile,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runner.observer import Observer
from runner.results import validate

class Integrity(unittest.TestCase):
    def observed(self):
        o=Observer('http://example.test')
        o.request('a','POST','http://example.test/api/users/login',{})
        o.finish('a',422,{'errors':{}})
        return o
    def test_incomplete_and_errors(self):
        o=self.observed();self.assertEqual(o.report('AC-3')['state'],'complete')
        o.request('b','GET','http://example.test/api/user',{})
        self.assertEqual(o.report('AC-3')['state'],'partial')
        o.errors.append('capture-failed');self.assertEqual(o.report('AC-3')['state'],'error')
        o.available=False;self.assertEqual(o.report('AC-3')['state'],'unavailable')
    def test_foreign_origin_cannot_satisfy_observation(self):
        o=Observer('http://example.test');o.request('a','POST','http://elsewhere.test/api/users/login',{});o.finish('a',422,{})
        self.assertEqual(o.report('AC-3')['state'],'partial')
    def test_authentication_evidence_is_required(self):
        o=Observer('http://example.test')
        o.request('a','POST','http://example.test/api/users/login',{});o.finish('a',200,{})
        o.request('b','GET','http://example.test/api/user',{});o.finish('b',200,{})
        self.assertEqual(o.report('AC-2')['state'],'partial')
if __name__=='__main__':unittest.main()
