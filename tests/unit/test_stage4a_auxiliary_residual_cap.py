"""Regression for prospective 4A auxiliary residual cap, not historical observer."""
import json,math,statistics,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from observation.observation_layer_4a_candidate import auxiliary_trace_candidate
from scripts.run_stage4_dev_separability import make_dev_row,dev_seeds
from scripts.run_stage4_experiments import make_observation_config

class AuxiliaryResidualCap(unittest.TestCase):
 def config(self):
  prereg=json.loads((ROOT/"experiments/stage_04_data_validation/REVISION_PREREG_ADDENDUM.json").read_text())
  row=make_dev_row("H00",0,prereg,dev_seeds("H00",0))
  return make_observation_config(row,prereg,verify_draws=True)
 def test_small_cap_no_longer_collapses_load_to_constant(self):
  c=self.config();c["aux_cap_W"]=100.
  x=auxiliary_trace_candidate(c,5.,400,nominal_W=1900.)
  self.assertEqual(len(x),400)
  self.assertTrue(all(1800<=v<=2000 for v in x))
  self.assertGreater(statistics.pstdev(x),0.01)
  self.assertGreater(min(x),100.)
  self.assertEqual(x,auxiliary_trace_candidate(c,5.,400,nominal_W=1900.))
 def test_bounds_nonnegative_and_seed_independent(self):
  c=self.config();c["aux_cap_W"]=4000.
  x=auxiliary_trace_candidate(c,5.,300,nominal_W=1900.)
  self.assertTrue(all(0<=v<=5900 and math.isfinite(v) for v in x))
  c2=dict(c);c2["seeds"]=dict(c["seeds"]);c2["seeds"]["aux"]^=7919
  y=auxiliary_trace_candidate(c2,5.,300,nominal_W=1900.)
  self.assertNotEqual(x,y)
if __name__=="__main__":unittest.main()
