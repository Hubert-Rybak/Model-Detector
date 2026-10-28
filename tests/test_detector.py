import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detector import features, probes, unicode_scan, scorer  # noqa: E402


class UnicodeScanTests(unittest.TestCase):
    def test_hidden_chars_detected(self):
        r = unicode_scan.scan("a​b 10 PM it’s “q” — x")
        self.assertEqual(r.zero_width_count, 1)
        self.assertEqual(r.narrow_nbsp_count, 1)
        self.assertEqual(r.curly_apostrophes, 1)
        self.assertEqual(r.curly_double_quotes, 2)
        self.assertEqual(r.em_dash, 1)
        sev = [s for s, _ in unicode_scan.suspicious_summary(r)]
        self.assertIn("HIGH", sev)

    def test_clean_text(self):
        r = unicode_scan.scan("plain ascii text, nothing to see.")
        self.assertEqual(unicode_scan.suspicious_summary(r)[0][0], "NONE")

    def test_homoglyph(self):
        r = unicode_scan.scan("pаssword")  # cyrillic a
        self.assertEqual(r.mixed_script_words, ["pаssword"])


class FeatureTests(unittest.TestCase):
    def test_markdown_and_rhetoric(self):
        t = "## Title\n\n- **A:** one\n- **B:** two\n\nIt's not luck, it's physics. Not magic. Not luck. Just physics.\n\nWould you like me to continue?"
        f = features.extract(t)
        self.assertEqual(f["headers_h2"], 1)
        self.assertEqual(f["bold_colon_inside"], 2)
        self.assertGreaterEqual(f["rh_antithesis_not_but"], 1)
        self.assertEqual(f["rh_tricolon_fragments"], 1)
        self.assertEqual(f["closer_offer_would_you_like"], 1)

    def test_empty(self):
        f = features.extract("")
        self.assertEqual(f["n_words"], 0)


class ProbeTests(unittest.TestCase):
    def test_battery_parse(self):
        txt = "\n".join(f"{i}. x" for i in range(1, 25))
        txt = txt.replace("5. x", "5. 53").replace("9. x", "9. Tails").replace("11. x", "11. The letter Q").replace("13. x", "13. Paris, France")
        b = probes.parse_battery(txt)
        self.assertEqual(b["n_items_found"], 24)
        self.assertEqual(b["rand_1_100"], 53)
        self.assertEqual(b["coin"], "tails")
        self.assertEqual(b["rand_letter"], "q")
        self.assertEqual(b["rand_city"], "paris")

    def test_negated_self_report(self):
        pa = scorer.provider_assertions("I'm not ChatGPT; I'm Claude, made by Anthropic.")
        self.assertNotIn("openai", pa)
        self.assertIn("anthropic", pa)

    def test_ok_forms(self):
        self.assertEqual(probes.parse_ok("ok")["ok_form"], "exact_ok")
        self.assertEqual(probes.parse_ok("Ok.")["ok_form"], "ok_with_punct")


class ScorerTests(unittest.TestCase):
    def test_llama_number(self):
        ctx = scorer.Context()
        ctx.b = {"rand_1_100": 53}
        ev = scorer.random_choice_evidence(ctx, scorer.load_random_priors())
        self.assertTrue(ev)
        self.assertEqual(max(ev[0].weights, key=ev[0].weights.get), "meta")

    def test_evaluate_runs_without_essay(self):
        ctx = scorer.Context()
        ctx.b = probes.parse_battery("1. I am Gemini, made by Google.\n2. none\n")
        r = scorer.evaluate(ctx)
        self.assertEqual(r["top"], "google")


if __name__ == "__main__":
    unittest.main()
