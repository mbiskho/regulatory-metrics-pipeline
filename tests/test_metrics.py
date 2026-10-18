import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from regulatory_metrics_pipeline import calculate_metrics


ROOT = Path(__file__).resolve().parents[1]


class RegulatoryMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = json.loads((ROOT / "examples/sample_metrics.json").read_text())

    def test_calculates_explainable_components(self):
        result = calculate_metrics(self.sample)
        metrics = result["metrics"]
        self.assertAlmostEqual(metrics["credit_risk_weighted_assets"], 588250000)
        self.assertAlmostEqual(metrics["three_year_average_gross_income"], 43566666.666666664)
        self.assertAlmostEqual(metrics["illustrative_total_risk_weighted_assets"], 745937500)
        self.assertAlmostEqual(
            metrics["illustrative_total_capital_ratio"],
            metrics["eligible_capital"] / metrics["illustrative_total_risk_weighted_assets"],
        )
        self.assertIsNotNone(metrics["illustrative_total_capital_ratio"])
        self.assertIn("not a regulatory capital determination", result["notice"])

    def test_rejects_risk_weight_above_supported_range(self):
        invalid = json.loads(json.dumps(self.sample))
        invalid["credit_exposures"][0]["risk_weight"] = 2.01
        with self.assertRaisesRegex(ValueError, "between 0 and 2"):
            calculate_metrics(invalid)

    def test_requires_three_income_years(self):
        invalid = json.loads(json.dumps(self.sample))
        invalid["gross_income_3y"] = [10, 20]
        with self.assertRaisesRegex(ValueError, "exactly three"):
            calculate_metrics(invalid)

    def test_cli_outputs_notice_and_metrics(self):
        process = subprocess.run(
            [sys.executable, "-m", "regulatory_metrics_pipeline", str(ROOT / "examples/sample_metrics.json")],
            cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            check=True, capture_output=True, text=True,
        )
        output = json.loads(process.stdout)
        self.assertIn("illustrative_total_capital_ratio", output["metrics"])
        self.assertIn("synthetic calculation only", output["notice"])


if __name__ == "__main__":
    unittest.main()
