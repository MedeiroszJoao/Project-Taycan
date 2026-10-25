import unittest
from unittest.mock import patch
import numpy as np
from scripts.compare_e66_a_cell_law import predict
from scripts.calibrate_e66_kinetics import params
class ConditionalPhysicsTests(unittest.TestCase):
 def test_joint_kinetic_scaling_preserves_ocp(self):
  a=params(1,.6,25);b=params(3,.6,25)
  self.assertEqual(a['Positive electrode OCP [V]'](.5),b['Positive electrode OCP [V]'](.5))
  for side in ['Negative','Positive']:
   key=side+' electrode exchange-current density [A.m-2]';v=a[key](1000,10000,30000,298.15);w=b[key](1000,10000,30000,298.15)
   self.assertAlmostEqual(float(w.evaluate()),3*float(v.evaluate()),places=10)
 def test_a_zero_current_no_voltage_change(self):
  from taycan_sim.model import ModelConfig
  np.testing.assert_array_equal(predict(np.array([0.,10.,100.]),0,10,25,0,ModelConfig()),0)
 def test_a_current_interrupt_removes_ohmic_drop(self):
  from taycan_sim.model import ModelConfig
  p=ModelConfig();v=predict(np.array([10-1e-8,10+1e-8]),65,10,25,0,p)
  self.assertAlmostEqual(v[1]-v[0],65*p.r0_ohm_cell,places=8)
 def test_a_long_rest_retains_soc_ocv_shift(self):
  from taycan_sim.model import ModelConfig
  p=ModelConfig();v=predict(np.array([10000.]),65,10,25,0,p)[0]
  self.assertAlmostEqual(v,-p.ocv_span_v*65*10/(3600*p.capacity_ah_cell),places=12)
if __name__=='__main__':unittest.main()
