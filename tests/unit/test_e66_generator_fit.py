import io,unittest
import numpy as np
from scipy.io import savemat
from scripts.fit_e66_generator_b import segment
class E66FitTests(unittest.TestCase):
 def fixture(self,t=None):
  n=20;b=io.BytesIO();savemat(b,{'meas':{'Time':np.arange(n) if t is None else t,'Current':np.r_[0.,np.full(16,-3.25),0,0,0],'Voltage':np.full(n,3.8),'Battery_Temp_degC':np.full(n,25)}});return b.getvalue()
 def test_discharge_positive_capacity(self):
  s=segment(self.fixture());self.assertEqual(s['rows'],16);self.assertEqual(s['t'][0],0);self.assertAlmostEqual(s['capacity_Ah'],3.25*15/3600)
 def test_reject_duplicated_time(self):
  t=np.arange(20,dtype=float);t[4]=t[3]
  with self.assertRaises(ValueError):segment(self.fixture(t))
if __name__=='__main__':unittest.main()
