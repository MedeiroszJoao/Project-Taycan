"""Independent synthetic-fixture tests, not empirical TUM validation."""
import csv,math,tempfile,unittest
from pathlib import Path
from scripts.stage4b_tum_energy_probe import _analyze,select

class TestEnergyProbe(unittest.TestCase):
 def test_selection_by_sha_not_file_index(self):
  frame=[{"path":f"realdriving_data_publication/realdriving_{i}.csv",
           "size_bytes":1000} for i in range(1,93)]
  chosen=select(frame)
  self.assertEqual(len(chosen),12)
  self.assertEqual(chosen,select(list(reversed(frame))))
 def test_two_points_exact_signed_energy(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"synthetic.csv"
   f.write_text("time,hv_soc,hv_current,hv_voltage,motor_torque,motor_speed\n"
                "0,50,10,800,60,6000\n"
                "1,50,10,800,60,6000\n")
   r=_analyze(f,"synthetic")
   self.assertEqual(r["rows"],2)
   self.assertAlmostEqual(r["net_terminal_signed_kWh"],8000/3.6e6)
   self.assertAlmostEqual(r["net_current_Ah_signed"],10/3600)
   self.assertAlmostEqual(r["net_single_motor_mechanical_kWh"],
                          60*6000*2*math.pi/60/3.6e6)
   self.assertEqual(r["pair_and_data_counts"]["voltage_current_pairs"],1)
   self.assertEqual(r["ten_minute_windows_eligible"],0)
 def test_invalid_gap_does_not_integrate(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"synthetic.csv"
   f.write_text("time,hv_soc,hv_current,hv_voltage,motor_torque,motor_speed\n"
                "0,50,10,800,60,6000\n"
                "2,50,10,800,60,6000\n")
   r=_analyze(f,"synthetic")
   self.assertEqual(r["net_terminal_signed_kWh"],0)
   self.assertEqual(r["pair_and_data_counts"]["gap_gt_1s_pairs"],1)
 def test_invalid_voltage_nan_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/"synthetic.csv"
   f.write_text("time,hv_soc,hv_current,hv_voltage,motor_torque,motor_speed\n"
                "0,50,10,800,60,6000\n"
                "0.1,50,10,NaN,60,6000\n")
   r=_analyze(f,"synthetic")
   self.assertEqual(r["net_terminal_signed_kWh"],0)
   self.assertEqual(r["pair_and_data_counts"]["voltage_current_missing_pairs"],1)
if __name__=="__main__":unittest.main()
