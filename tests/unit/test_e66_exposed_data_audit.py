import io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from scipy.io import savemat
from scripts.audit_e66_exposed_data import integrate,selected_indices
from scripts.fit_e66_generator_b import segment

def fixture(n=20):
 return {'Time':np.arange(n,dtype=float),'Current':np.full(n,-2.),'Voltage':np.full(n,3.8),'Battery_Temp_degC':np.full(n,25.)}
def mat(m):
 b=io.BytesIO();savemat(b,{'meas':m});return b.getvalue()
class ExposedDataAudit(unittest.TestCase):
 def test_constant_current_units(self):
  self.assertAlmostEqual(integrate([0,1800,3600],[2,2,2]),2.)
 def test_nonmonotone_time_rejected(self):
  with self.assertRaises(ValueError):integrate([0,2,1],[2,2,2])
 def test_first_contiguous_run_only(self):
  m=fixture();m['Current'][10]=0;ix,allix=selected_indices(m)
  self.assertEqual(len(ix),10);self.assertEqual(len(allix),19)
 def test_source_cell_negative_discharge_not_module_convention(self):
  m=fixture();self.assertEqual(len(selected_indices(m)[0]),20)
  m['Current']*=-1
  with self.assertRaises(ValueError):selected_indices(m)
 def test_nonfinite_break_exposed(self):
  m=fixture();m['Voltage'][12]=np.nan;ix,_=selected_indices(m)
  self.assertEqual(len(ix),12)
 def test_legacy_short_first_run_bug_characterized_not_modified(self):
  m=fixture();m['Current'][1]=0
  # Legacy checks >=10 overall before splitting, then returns a one-point run.
  old=segment(mat(m));self.assertEqual(old['rows'],1);self.assertEqual(old['capacity_Ah'],0)
  with self.assertRaises(ValueError):selected_indices(m)
 def test_legacy_gap_bridging_characterized(self):
  m=fixture();m['Time'][10:]+=1000
  self.assertGreater(segment(mat(m))['capacity_Ah'],.5)
  # Audit does not silently fill the gap; caller reports max dt/time fraction.
  ix,_=selected_indices(m);self.assertEqual(np.diff(m['Time'][ix]).max(),1001)
 def test_capacity_current_mapping_exact(self):
  q=61.;i=65.;self.assertAlmostEqual((i/(q/5))/5,i/q)
if __name__=='__main__':unittest.main()
