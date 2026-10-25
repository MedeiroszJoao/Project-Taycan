import unittest
from scripts.e66_mesh80_batch import compare,baseline_check

class E66MeshBatchTests(unittest.TestCase):
    def make(self,offset=0.,full=True):
        return {'status':'COMPLETED','model':'SPMe','model_only_curve':[{'time_s':float(i),'model_V':4.-i*.1+offset} for i in range(5)],'summary':{'complete_full_horizon':full,'coverage_fraction':1. if full else .8},'original_empirical_gate':'FAIL'}
    def test_small_mesh_gap_does_not_make_empirical_pass(self):
        result=compare(self.make(),self.make(.001))
        self.assertEqual(result['gate'],'PASS')
        self.assertEqual(result['mesh80_empirical_gate'],'FAIL')
        self.assertAlmostEqual(result['max_abs_mesh_difference_V'],.001)
    def test_large_mesh_gap_fails(self):self.assertEqual(compare(self.make(),self.make(.006))['gate'],'FAIL')
    def test_incomplete_domain_not_pass(self):self.assertEqual(compare(self.make(),self.make(.001,False))['gate'],'INCONCLUSIVO')
    def test_timeout_is_not_numerical_failure(self):self.assertEqual(compare(self.make(),{'status':'TIMEOUT'})['gate'],'INCONCLUSIVO')
    def test_grid_mismatch_fails_closed(self):
        other=self.make();other['model_only_curve'][2]['time_s']=2.1
        with self.assertRaises(ValueError):compare(self.make(),other)
    def test_archived_scalar_check_is_separate(self):
        r=self.make();r['predictive_scalar_metrics']={'rmse_V':.08,'bias_V':-.079,'max_abs_V':.16}
        old={'models':{'SPMe':{'cases':{'D_BOTH_ORIGINAL_COMPARATOR':{'predictive':dict(r['predictive_scalar_metrics'])}}}}}
        self.assertTrue(baseline_check(r,old)['within_0_1mV_all_scalar_metrics'])
        r['predictive_scalar_metrics']['bias_V']=-.07
        self.assertFalse(baseline_check(r,old)['within_0_1mV_all_scalar_metrics'])
if __name__=='__main__':unittest.main()
