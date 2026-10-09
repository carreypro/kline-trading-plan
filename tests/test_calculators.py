import unittest

from scripts.risk_plan import calculate as calculate_risk
from scripts.signal_score import calculate as calculate_score


class SignalScoreTests(unittest.TestCase):
    def test_missing_signal_reduces_coverage_without_becoming_zero_score(self):
        result = calculate_score(
            {
                "pillars": {
                    "price_volume": {
                        "signals": [
                            {"name": "structure", "score": 60, "weight": 1},
                            {"name": "volume", "available": False, "weight": 1},
                        ]
                    },
                    "derivatives": {"signals": []},
                    "macro": {"signals": []},
                }
            }
        )
        self.assertEqual(result["composite_score"], 60.0)
        self.assertEqual(result["pillars"]["price_volume"]["coverage"], 0.5)
        self.assertLess(result["coverage"], 0.5)

    def test_score_bounds_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "between -100 and 100"):
            calculate_score(
                {
                    "pillars": {
                        "price_volume": {
                            "signals": [{"name": "bad", "score": 101}]
                        }
                    }
                }
            )


class RiskPlanTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "direction": "long",
            "product": "swap",
            "entry_low": 99_000,
            "entry_high": 100_000,
            "stop_loss": 97_000,
            "targets": [106_000, 112_000],
            "account_equity": 10_000,
            "max_account_risk_pct": 1,
            "max_margin_pct": 20,
            "max_leverage": 3,
            "lot_size": 0.0001,
        }

    def test_all_tiers_respect_user_caps(self):
        result = calculate_risk(self.payload)
        for tier in result["tiers"]:
            self.assertLessEqual(tier["account_risk_pct"], 1.0)
            self.assertLessEqual(tier["margin_required"], 2_000.0)
            self.assertLessEqual(tier["leverage"], 3.0)

    def test_short_uses_lower_entry_as_worst_fill(self):
        payload = dict(self.payload)
        payload.update(
            direction="short",
            entry_low=100,
            entry_high=102,
            stop_loss=106,
            targets=[94, 88],
        )
        result = calculate_risk(payload)
        self.assertEqual(result["sizing_entry"], 100.0)
        self.assertGreater(result["tiers"][0]["targets"][0]["net_rr"], 0)

    def test_spot_forces_one_x_leverage(self):
        payload = dict(self.payload)
        payload["product"] = "spot"
        result = calculate_risk(payload)
        self.assertTrue(all(tier["leverage"] == 1.0 for tier in result["tiers"]))

    def test_invalid_long_stop_is_rejected(self):
        payload = dict(self.payload)
        payload["stop_loss"] = 101_000
        with self.assertRaisesRegex(ValueError, "long stop"):
            calculate_risk(payload)


if __name__ == "__main__":
    unittest.main()
