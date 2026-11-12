# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/test_classify.py — annotation abstention/provenance tests.

import csv
import json
import os
import tempfile
import unittest

from classify import BirdNetBackend, classify_file, result_record


class FakeBackend:
    name = "fake"
    version = "test-1"
    supports_context = True

    def predict(self, wav_path, context=None):
        if context:
            return [{"label": "site-bird", "species": "Site bird",
                     "score": 0.9}]
        return [{"label": "acoustic-bird", "species": "Acoustic bird",
                 "score": 0.8}]


class ClassifyTest(unittest.TestCase):
    def test_result_keeps_acoustic_and_context_separate(self):
        rec = result_record("/tmp/a.wav", "n1", "cal", {"lat": 32},
                            "fake", "v1",
                            [{"label": "raw", "score": 0.7}],
                            [{"label": "ctx", "score": 0.9}], 0.5, 300)
        self.assertEqual(rec["label"], "raw")
        self.assertTrue(rec["provenance"]["context_applied"])
        self.assertEqual(rec["provenance"]["context_adjusted_scores"][0]
                         ["label"], "ctx")
        self.assertFalse(rec["needs_review"])

    def test_low_confidence_abstains(self):
        rec = result_record("/tmp/a.wav", "n1", None, {}, "fake", "v1",
                            [{"label": "maybe", "score": 0.2}], [], 0.5, 1)
        self.assertEqual(rec["status"], "needs_review")
        self.assertIsNone(rec["species"])
        self.assertEqual(rec["review_reason"], "below-threshold")

    def test_no_scores_is_human_review_not_species(self):
        rec = result_record("/tmp/a.wav", "n1", None, {}, "none", None,
                            [], [], 0.5, 1)
        self.assertEqual(rec["label"], "unknown")
        self.assertTrue(rec["needs_review"])
        self.assertEqual(rec["review_reason"], "no-model-scores")

    def test_birdnet_csv_parser(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.csv")
            with open(p, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=[
                    "Start (s)", "End (s)", "Scientific name",
                    "Common name", "Confidence"])
                w.writeheader()
                w.writerow({"Start (s)": 0, "End (s)": 3,
                            "Scientific name": "Turdus migratorius",
                            "Common name": "American Robin",
                            "Confidence": 0.83})
            got = BirdNetBackend()._read(p)
        self.assertEqual(got[0]["label"], "American Robin")
        self.assertEqual(got[0]["species"], "Turdus migratorius")

    def test_fake_backend_classifies_and_routes(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "a.pcm")
            with open(path, "wb") as fh:
                fh.write(b"\x01\x20" * 4800)   # audible non-silence
            rec = classify_file(path, FakeBackend(), "n1", "cal",
                                {"lat": 32, "habitat": "playa"}, 0.5)
        self.assertEqual(rec["label"], "acoustic-bird")
        self.assertEqual(rec["provenance"]
                         ["context_adjusted_scores"][0]["label"], "site-bird")
        self.assertFalse(rec["needs_review"])


if __name__ == "__main__":
    unittest.main()
