import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src/simulator'))
from scripts.run_stage4_dev_separability import (
    metric, summarize, dev_seeds, frozen_seed_set, N_PER_HYPOTHESIS, HYPOTHESES
)
from scripts.run_stage4_experiments import FEATURE_NAMES, MASK_NAMES

class ExploratoryPairwiseTests(unittest.TestCase):
    def test_math_fisher_and_gaussian_jeffreys_are_nonnegative(self):
        z=metric([1,2,2,2,3,1,3,2],[3,4,4,4,5,3,5,4])
        self.assertGreater(z["Fisher_ratio"],0)
        self.assertGreater(z["symmetric_gaussian_KL"],0)
        u=metric([1,2,2,2,3,1,3,2],[1,2,2,2,3,1,3,2])
        self.assertAlmostEqual(u["Fisher_ratio"],0)
        self.assertAlmostEqual(u["symmetric_gaussian_KL"],0)

    def test_insufficient_and_constant_samples_are_null(self):
        self.assertIsNone(metric([1]*7,[2]*9)["Fisher_ratio"])
        self.assertIsNone(metric([1]*9,[2]*9)["symmetric_gaussian_KL"])

    def test_development_seed_namespace_disjoint_from_frozen(self):
        old=frozen_seed_set()
        new=[s for h in HYPOTHESES for i in range(N_PER_HYPOTHESIS)
             for s in dev_seeds(h,i).values()]
        self.assertEqual(len(new),len(set(new)))
        self.assertFalse(set(new)&old)
        self.assertEqual(len(old),8928)

    def test_features_reject_nondevelopment_samples(self):
        fake={f:1.0 for f in FEATURE_NAMES}
        fake.update({mask:0 for mask in MASK_NAMES})
        with self.assertRaises(ValueError):
            summarize([{"hypothesis":"H00","split":"test","features":fake}])

    def test_pairwise_schema_66_pairs_28_features(self):
        samples=[]
        for h in HYPOTHESES:
            for i in range(8):
                feats={f:float(i+(0 if h=="H00" else 3)) for f in FEATURE_NAMES}
                feats.update({m:0 for m in MASK_NAMES})
                samples.append({"hypothesis":h,"split":"UNSEALED_DEVELOPMENT_ONLY",
                                "features":feats})
        r=summarize(samples)
        self.assertEqual(len(r["pairs"]),66)
        self.assertTrue(all(len(p["feature_metrics"])==28 for p in r["pairs"]))
        self.assertEqual(r["pairs"][0]["a"],"H00")

if __name__=="__main__":
    unittest.main()
