import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import recalibrate_e66_ocp_offset as o
class OCPFreezeTests(unittest.TestCase):
 def attempt(self,biases=(.01,.03),coverage=1,existing=False):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);parent=p/'parent';out=p/'out';parent.mkdir();out.mkdir()
   (parent/'GENERATOR_B_FREEZE.json').write_text(json.dumps({'signature':{},'k':4.3}))
   (parent/'FIT_REGRESSION.json').write_text(json.dumps({'results':[{'status':'COMPLETED','coverage':coverage,'bias_V':b} for b in biases]}))
   if existing:(out/'GENERATOR_B_FREEZE.json').write_text('preserved')
   with patch.object(o,'OUT',out),patch.object(o.c,'OUT',parent),patch.object(o.c,'signature',return_value={}),patch.object(o,'signature',return_value={}),contextlib.redirect_stdout(io.StringIO()):o.fit()
   return json.loads((out/'GENERATOR_B_FREEZE.json').read_text())
 def test_training_only_equal_curve_offset(self):self.assertAlmostEqual(self.attempt()['additive_ocp_offset_V'],-.02)
 def test_incomplete_training_is_rejected(self):
  with self.assertRaises(ValueError):self.attempt(coverage=.9)
 def test_out_of_bounds_offset_is_rejected(self):
  with self.assertRaises(ValueError):self.attempt(biases=(.2,.3))
 def test_existing_freeze_is_not_overwritten(self):
  with self.assertRaises(ValueError):self.attempt(existing=True)
if __name__=='__main__':unittest.main()
