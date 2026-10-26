import numpy as np
from scripts.e66_relaxed_anchors import intervals

def test_short_rest_rejected():
 assert intervals(np.arange(600.),np.zeros(600))==[]
def test_full_rest_and_boundary():
 assert intervals(np.arange(601.),np.zeros(601))==[(0,601)]
def test_clock_gap_rejected():
 t=np.arange(601.);t[300:]+=3
 assert intervals(t,np.zeros(601))==[]
def test_current_interrupt_and_nan_split_rest():
 t=np.arange(1300.);i=np.zeros(1300);i[650]=np.nan
 assert intervals(t,i)==[(0,650),(651,1300)]
def test_current_threshold():
 assert intervals(np.arange(601.),np.ones(601)*1.01)==[]
