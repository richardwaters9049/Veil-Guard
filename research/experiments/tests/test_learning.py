from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

import numpy as np

EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))
import common
import development
import external_reference
from learning import ExactKNN, ResearchError, review_reason
import metrics

META = {"model_id": "authored-toy", "corpus_source_sha256": "a"*64, "protocol_sha256": "b"*64}
POLICY = {"review_all": False, "margin": 0.0, "distance_limit": 10.0, "selection_status": "baseline_fixed"}


class Neighbours(unittest.TestCase):
    def test_hand_worked_inverse_and_uniform_votes(self):
        x = [[1,0,0,0,0,0,0,0], [0,2,0,0,0,0,0,0], [0,0,2,0,0,0,0,0]]
        model = ExactKNN(x, [1,1,0], ["A","B","C"], 3, standardised=False)
        result = model.predict([[0]*8])[0]
        self.assertEqual(result["score"], .75)
        info = next(model.neighbours([[0]*8]))
        self.assertAlmostEqual(model.vote(info, weights="uniform"), 2/3)
        self.assertEqual(info["distances"].tolist(), [1,2,2])

    def test_all_zero_rows_vote_beyond_k_and_conflicts_require_review(self):
        model = ExactKNN([[0]*8]*3, [1,0,1], ["C","A","B"], 1, standardised=False)
        result = model.predict([[0]*8])[0]
        self.assertAlmostEqual(result["score"], 2/3)
        self.assertEqual(result["zero_count"], 3)
        self.assertTrue(result["conflict"])
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["review_reason"], "exact_match_conflict")

    def test_distance_ties_use_id_order_independent_of_reference_order(self):
        a = [-1]+[0]*7
        b = [1]+[0]*7
        first = ExactKNN([a,b],[1,0],["Z","A"],1,standardised=False)
        second = ExactKNN([b,a],[0,1],["A","Z"],1,standardised=False)
        self.assertEqual(first.predict([[0]*8])[0]["score"], 0)
        self.assertEqual(first.predict([[0]*8]), second.predict([[0]*8]))

    def test_train_statistics_and_constant_columns_remain_frozen(self):
        x = [[1,2]+[7]*6, [3,6]+[7]*6]
        model = ExactKNN(x,[0,1],["A","B"],1)
        np.testing.assert_allclose(model.mean,[2,4]+[7]*6,rtol=0,atol=0)
        np.testing.assert_allclose(model.scale,[1,2]+[1]*6,rtol=0,atol=0)
        before = model.mean.copy()
        result = model.predict([[100]*8])[0]
        self.assertEqual(result["review_reason"], "outside_training_support")
        np.testing.assert_array_equal(before, model.mean)

    def test_export_roundtrip_and_corrupt_models(self):
        model = ExactKNN([[1]*8,[3]*8],[0,1],["A","B"],1)
        bundle = model.bundle(META,POLICY)
        restored = ExactKNN.from_bundle(bundle)
        self.assertEqual(model.predict([[2]*8],POLICY),restored.predict([[2]*8],POLICY))
        mutations = [
            lambda d:d.update(schema="unknown"),
            lambda d:d["feature_names"].reverse(),
            lambda d:d["references"].append(d["references"][0]),
            lambda d:d["references"][0].update(label=True),
            lambda d:d["references"][0].update(label=2),
            lambda d:d["references"][0].update(vector=[0]*9),
            lambda d:d["references"][0].update(vector=[True]+[0.0]*7),
            lambda d:d.update(scale=[0]*8),
            lambda d:d.update(mean=[float("nan")]*8),
            lambda d:d.update(k=999),
            lambda d:d.update(weights="other"),
            lambda d:d.update(raw_source="forbidden"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ResearchError):
                altered=deepcopy(bundle);mutate(altered);ExactKNN.from_bundle(altered)

    def test_invalid_matrices_and_numeric_overflow_are_rejected(self):
        for matrix in ([[0]*7], [[0]*9], [[float("nan")]*8], [[float("inf")]*8], [[True]+[0.0]*7]):
            with self.assertRaises(ResearchError):
                ExactKNN(matrix,[0],["A"],1,standardised=False)
        model=ExactKNN([[0]*8],[0],["A"],1,standardised=False)
        with self.assertRaises(ResearchError):
            model.predict([[1e308]*8])

    def test_abstention_conditions(self):
        info={"conflict":False,"outside":False,"nearest":2}
        self.assertEqual(review_reason(.9,info,{**POLICY,"distance_limit":1}),"nearest_distance_exceeded")
        self.assertEqual(review_reason(.55,info,{**POLICY,"margin":.2}),"low_vote_margin")
        self.assertEqual(review_reason(.9,info,{**POLICY,"review_all":True}),"validation_policy_unmet")


class EvaluationMetrics(unittest.TestCase):
    def test_hand_worked_metrics_separate_AP_and_trapezoidal_area(self):
        result=metrics.ranking(["a","b","c"],[1,0,1],[.9,.8,.7])
        self.assertAlmostEqual(result["precision_at_m"],2/3)
        self.assertEqual(result["recall_at_m"],1)
        self.assertIsNone(result["precision_at_20"])
        self.assertAlmostEqual(result["average_precision"],5/6)
        self.assertAlmostEqual(result["trapezoidal_pr_auc"],19/24)

    def test_ties_have_ID_ordered_top20_and_threshold_grouped_AP(self):
        ids=["z"]+[f"a{i:02}" for i in range(20)]
        result=metrics.ranking(ids,[1]+[0]*20,[.5]*21)
        self.assertEqual(result["precision_at_20"],0)
        self.assertAlmostEqual(result["average_precision"],1/21)

    def test_empty_and_no_positive_scopes_are_explicit(self):
        empty=metrics.ranking([],[],[])
        self.assertIsNone(empty["precision_at_m"])
        self.assertIsNone(empty["average_precision"])
        negative=metrics.ranking(["a","b"],[0,0],[.9,.1])
        self.assertEqual(negative["precision_at_m"],0)
        self.assertIsNone(negative["recall_at_m"])
        self.assertIsNone(negative["average_precision"])

    def test_selective_denominators(self):
        result=metrics.selective([0,0,1,1],[0,1,None,1])
        self.assertEqual(result["confusion"],{"tn":1,"fp":1,"fn":0,"tp":1})
        self.assertEqual(result["coverage"],.75)
        self.assertAlmostEqual(result["error_rate_on_accepted"],1/3)
        self.assertEqual(result["accepted_positive_support"],1)
        self.assertEqual(result["full_positive_support"],2)
        self.assertIsNone(metrics.selective([0,1],[None,None])["error_rate_on_accepted"])

    def test_bootstrap_is_paired_by_group_and_deterministic(self):
        left=[{"repository_id":"a","group_id":"shared","precision_at_20":1.0},
              {"repository_id":"b","group_id":"shared","precision_at_20":1.0},
              {"repository_id":"c","group_id":"other","precision_at_20":0.0}]
        right=[{**r,"precision_at_20":0.0} for r in left]
        first=metrics.paired_interval(left,right,"precision_at_20",200,42)
        self.assertEqual(first,metrics.paired_interval(left,right,"precision_at_20",200,42))
        self.assertAlmostEqual(first["estimate"],2/3)
        self.assertEqual(first["groups"],2)
        self.assertEqual((first["lower"],first["upper"]),(0,1))
        right[0]["group_id"]="wrong"
        with self.assertRaises(ResearchError):
            metrics.paired_interval(left,right,"precision_at_20",200,42)

    def test_benefit_requires_both_gates(self):
        self.assertEqual(metrics.benefit(.56,.5,{"lower":.001},.1)["decision"],"pass_on_synthetic_benchmark")
        self.assertEqual(metrics.benefit(.7,.5,{"lower":-.001},.1)["decision"],"fail_on_synthetic_benchmark")
        self.assertEqual(metrics.benefit(.7,0,{"lower":.1},.1)["decision"],"unproven")


class Isolation(unittest.TestCase):
    def test_development_and_threshold_selection_refuse_held_out_rows(self):
        for partition in ("test","challenge"):
            with self.assertRaises(ResearchError):
                common.require_development([{"partition":partition,"label":"sensitive_candidate","group_id":"a"}])
        with self.assertRaises(ResearchError):
            common.require_development([{"partition":"train","label":"uncertain","group_id":"a"}])
        with self.assertRaises(ResearchError):
            common.require_development([{"partition":"train","label":"benign_fixture","group_id":"a"},
                                        {"partition":"validation","label":"benign_fixture","group_id":"a"}])
        model=ExactKNN([[0]*8,[1]*8],[0,1],["A","B"],1)
        with self.assertRaises(ResearchError):
            development.choose_policy(model,[{"partition":"test"}],common.protocol())

    def test_unmet_validation_targets_produce_full_review(self):
        model=ExactKNN([[0]*8,[0]*8],[0,1],["A","B"],1,standardised=False)
        validation=[{"partition":"validation","features":[0]*8,"label":"sensitive_candidate","id":"V"}]
        policy, record=development.choose_policy(model,validation,common.protocol())
        self.assertTrue(policy["review_all"])
        self.assertEqual(record["feasible_policies"],0)

    def test_cv_scalers_fit_only_fold_training_groups(self):
        rows=[]
        for group in range(6):
            for outcome in range(2):
                for variant in range(2):
                    rows.append({"id":f"g{group}y{outcome}v{variant}","partition":"train",
                                 "repository_id":f"r{group}","group_id":f"g{group}",
                                 "features":[group*10+variant,outcome]+[0.0]*6,
                                 "label":"sensitive_candidate" if outcome else "benign_fixture"})
        p={**common.protocol(),"folds":3,"k_grid":[3],"weight_grid":["inverse_distance"],
           "logistic_C_grid":[1.0]}
        result=development.grouped_selection(rows,p)
        for fold in result[4]:
            self.assertFalse(set(fold["fit_groups"]).intersection(fold["score_groups"]))
            fit=[r["features"] for r in rows if r["group_id"] in fold["fit_groups"]]
            np.testing.assert_allclose(fold["mean"],np.mean(fit,axis=0),atol=1e-12)
            self.assertEqual(fold["scale"][2:],[1.0]*6)

    def test_bounded_json_and_new_output_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            common.save_new(root/"valid.json",{"safe":1})
            with self.assertRaises(FileExistsError):
                common.save_new(root/"valid.json",{"replace":1})
            (root/"bad.json").write_text('{"value":NaN}')
            with self.assertRaises(ResearchError):
                common.load_json(root/"bad.json")
            with self.assertRaises(ResearchError):
                common.load_json(root/"valid.json",maximum=1)
            with self.assertRaises(ResearchError):
                common.new_directory(root)

    def test_external_archive_does_not_extract_links(self):
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode="w:gz") as archive:
            member=tarfile.TarInfo("gitleaks")
            member.type=tarfile.SYMTYPE
            member.linkname="/outside"
            archive.addfile(member)
        with self.assertRaises(ResearchError):
            external_reference.binary_from_archive(data.getvalue())


if __name__=="__main__":
    unittest.main()
