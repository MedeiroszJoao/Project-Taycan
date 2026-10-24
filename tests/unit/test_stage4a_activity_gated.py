"""Unapproved 4A candidate I01 gating invariants. No historical file mutation."""
import hashlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src/simulator"))
from candidate_sim import model_4a_activity_gated as phys

class I01ActivityGate(unittest.TestCase):
 def run_case(self,h,torque,rpm,severity=.25):
  p=phys.ModelConfig(seed=741,dt_s=5.,steps=2,initial_soc=.6,
    sensor_noise=False,auxiliary_amplitude_W=0)
  return phys.simulate(phys.Fault(h,severity=severity),p,
    torque_trace_nm=[torque]*2,rpm_trace_rpm=[rpm]*2,
    auxiliary_trace_W=[100.]*2)
 def test_historical_model_immutable(self):
  path=ROOT/"src/simulator/taycan_sim/model.py"
  self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
    "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e")
 def test_parked_zero_extra(self):
  a=self.run_case("H00",0.,0.)
  b=self.run_case("I01",0.,0.)
  for x,y in zip(a.truth,b.truth):
   self.assertAlmostEqual(y["power_inverter_loss_W"]-x["power_inverter_loss_W"],0.)
 def test_motoring_and_regen(self):
  for tau in (30.,-30.):
   with self.subTest(torque=tau):
    a=self.run_case("H00",tau,3000.)
    b=self.run_case("I01",tau,3000.)
    for x,y in zip(a.truth,b.truth):
     self.assertAlmostEqual(y["power_inverter_loss_W"]-x["power_inverter_loss_W"],400.,delta=1e-8)
 def test_zero_rpm_or_torque(self):
  for tau,rpm in ((30.,0.),(0.,3000.)):
   with self.subTest(torque=tau,rpm=rpm):
    a=self.run_case("H00",tau,rpm)
    b=self.run_case("I01",tau,rpm)
    for x,y in zip(a.truth,b.truth):
     self.assertAlmostEqual(y["power_inverter_loss_W"]-x["power_inverter_loss_W"],0.,delta=1e-8)
if __name__=="__main__":unittest.main()
