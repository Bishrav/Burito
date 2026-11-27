import unittest

from scripts.benchmark_local_asr import edit_distance


class AsrBenchmarkTests(unittest.TestCase):
    def test_edit_distance_counts_substitution_insertion_and_deletion(self):
        self.assertEqual(edit_distance("kitten", "sitting"), 3)
        self.assertEqual(edit_distance(["ask", "not"], ["ask", "what", "not"]), 1)


if __name__ == "__main__":
    unittest.main()
