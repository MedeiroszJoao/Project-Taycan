import unittest
import numpy as np
from scripts.e66_pulse_discrimination import clean_exact_duplicates
class QC(unittest.TestCase):
 def test_identical_zero_duration_rows(self):
  t=np.array([0.,1.,1.,2.]);v=np.array([4.,3.9,3.9,3.8]);i=np.ones(4);T=np.ones(4)*25
  (tt,ii,vv,temp),n=clean_exact_duplicates(t,i,v,T);self.assertEqual(n,1);np.testing.assert_equal(tt,[0,1,2]);self.assertAlmostEqual(np.trapezoid(ii,tt),np.trapezoid(i,t))
 def test_conflict_rejected(self):
  with self.assertRaises(ValueError):clean_exact_duplicates(np.array([0.,0.]),np.array([0.,1.]),np.ones(2),np.ones(2))
 def test_time_reversal_rejected(self):
  with self.assertRaises(ValueError):clean_exact_duplicates(np.array([1.,0.]),np.ones(2),np.ones(2),np.ones(2))
if __name__=='__main__':unittest.main()

class WindowQC(unittest.TestCase):
 def make_data(self,conflicts):
  t=np.arange(0,1021,.1);i=np.zeros(len(t));i[(t>=400)&(t<410)]=65
  # Prior discharge places the test pulse inside the permitted SOC range.
  i[t<40]=1200
  return t,i,np.full(len(t),3.8),np.full(len(t),25.),{'_conflict_times':np.array(conflicts)}
 def test_conflict_in_window_excludes_pulse(self):
  from unittest.mock import patch
  from scripts.e66_pulse_discrimination import extract
  with patch('scripts.e66_pulse_discrimination.read',return_value=self.make_data([405.])):
   pulses,meta=extract('HPPC')
  self.assertEqual(len(pulses),0);self.assertEqual(meta['pulses_excluded_conflicting_clock'],1)
 def test_outside_conflict_does_not_exclude_pulse(self):
  from unittest.mock import patch
  from scripts.e66_pulse_discrimination import extract
  with patch('scripts.e66_pulse_discrimination.read',return_value=self.make_data([10.])):
   pulses,meta=extract('HPPC')
  self.assertEqual(len(pulses),1);self.assertEqual(meta['pulses_excluded_conflicting_clock'],0)
