"""Safety tests for Stage4A research-only successor smoke."""
import sys, unittest, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"src"),str(ROOT/"src/simulator")]
from scripts.run_stage4a_research_train_smoke import (
 selected_train,sources,apply_fault_severity,POWER_KW
)
from scripts.run_stage4_experiments import HYPOTHESES,EXPECTED
from scripts.duty_cycle_candidate import build_duty_inputs
class ResearchSuccessorTests(unittest.TestCase):
 def test_only_first_train_rows_selected(self):
  data=selected_train()
  self.assertEqual(len(data),12)
  self.assertEqual([x["hypothesis"] for x in data],HYPOTHESES)
  self.assertTrue(all(x["split"]=="train" for x in data))
  self.assertTrue(all(x["episode_id"].startswith("S4R_") for x in data))
  self.assertEqual(len({x["episode_id"] for x in data}),12)
 def test_immutable_source_hashes(self):
  d=sources()
  self.assertEqual(d["historical_freeze"],EXPECTED["freeze_sha256"])
  self.assertEqual(d["historical_manifest"],EXPECTED["manifest_sha256"])
  self.assertEqual(d["stage3_model"],EXPECTED["model_py_sha256"])
 def test_i01_uses_physical_energy_matching_not_raw_manifest_severity(self):
  irow=selected_train()[-1]
  duty=build_duty_inputs(dt_s=5.,charge_power_kw=POWER_KW[irow["profile"]],
                         profile_id=irow["profile"])
  transformed=apply_fault_severity(irow,duty)
  self.assertGreater(transformed,0.)
  self.assertLess(transformed,float(irow["severity"]))
  self.assertTrue(math.isfinite(transformed))
 def test_noninverter_does_not_transform_severity(self):
  b=selected_train()[1]
  duty=build_duty_inputs(dt_s=5.,charge_power_kw=POWER_KW[b["profile"]],
                         profile_id=b["profile"])
  self.assertEqual(apply_fault_severity(b,duty),float(b["severity"]))
if __name__=="__main__":
 unittest.main()
