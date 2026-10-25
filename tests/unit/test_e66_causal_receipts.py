import unittest,json,copy
from scripts.audit_e66_causal_receipts import BASE,validate
class ReceiptTests(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads((BASE/'counterfactuals/RESULTS.json').read_text())['results'];self.spec=json.loads((BASE/'counterfactuals/PROTOCOL.json').read_text())
 def test_completed(self):self.assertEqual(validate(self.rows,self.spec),20)
 def test_omission(self):
  with self.assertRaises(ValueError):validate(self.rows[:-1],self.spec)
 def test_false_rmse(self):
  self.rows[0]['RMSE_V']+=.1
  with self.assertRaises(ValueError):validate(self.rows,self.spec)
 def test_relabel_fit(self):
  self.rows[0]['parameters_optimized']=True
  with self.assertRaises(ValueError):validate(self.rows,self.spec)
if __name__=='__main__':unittest.main()
