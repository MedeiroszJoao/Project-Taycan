"""Pilot 2 preregistration and measurement corruption guards."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"src/simulator"),str(ROOT/"src")]
from scripts.run_stage4_pilot2_dev import jobs,seed_audit,degrade
from scripts.analyze_stage4_pilot2_dev import metric
from scripts.run_stage4_experiments import OBSERVED_CHANNEL_WHITELIST
class Pilot2Tests(unittest.TestCase):
 def test_factorial_counts(self):
  data=list(jobs())
  self.assertEqual(len(data),2916)
  self.assertEqual(sum(j[5]=="long" for j in data),36)
  self.assertEqual(sum(j[5]=="short" and j[0]=="H00" for j in data),240)
  self.assertEqual(sum(j[5]=="short" and j[0]!="H00" for j in data),2640)
 def test_precommitted_rng_seeds_are_disjoint(self):
  self.assertEqual(seed_audit(),14580)
 def test_nominal_corruption_is_identity(self):
  src=[{**{k:1.234 for k in OBSERVED_CHANNEL_WHITELIST},
        "time_s":float(i)*5,"dt_s":5.} for i in range(15)]
  dst,n=degrade(src,"nominal",100)
  self.assertEqual(src,dst);self.assertEqual(n,0)
 def test_assumed_severe_corruption_removes_and_quantizes(self):
  src=[{**{k:1.234 for k in OBSERVED_CHANNEL_WHITELIST},
        "time_s":float(i)*5,"dt_s":5.} for i in range(15)]
  dst,n=degrade(src,"severe_assumed",200)
  self.assertEqual(len(dst),15)
  self.assertGreaterEqual(n,20*15)
  self.assertTrue(any(len(x)<len(src[0]) for x in dst))
 def test_metrics_are_not_synthetic_accuracy(self):
  x=metric([1,2,2,3,3,3,4,4],[2,3,3,4,4,5,5,5])
  self.assertGreaterEqual(x["fisher"],0)
  self.assertGreaterEqual(x["jeffreys_normal"],0)
  self.assertIsNone(metric([1]*7,[2]*10)["fisher"])
  self.assertIsNone(metric([1]*8,[2]*8)["fisher"])
if __name__=="__main__":unittest.main()
