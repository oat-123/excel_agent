import unittest
from unittest.mock import patch
from memory.name_mapping import (
    levenshtein_distance,
    similarity,
    get_all_student_names,
    get_corrected_keyword,
    learn_mapping,
    _load_mappings,
    _save_mappings
)
import os
import json

class TestNameMapping(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for mappings to avoid interfering with the actual file
        self.test_mappings_file = "memory/test_name_mappings.json"
        # Temporarily replace the MAPPINGS_FILE in the module
        import memory.name_mapping as nm
        self.original_mappings_file = nm.MAPPINGS_FILE
        nm.MAPPINGS_FILE = self.test_mappings_file
        # Ensure the memory directory exists
        os.makedirs("memory", exist_ok=True)
        # Start with an empty mapping file
        with open(self.test_mappings_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

    def tearDown(self):
        # Restore the original MAPPINGS_FILE
        import memory.name_mapping as nm
        nm.MAPPINGS_FILE = self.original_mappings_file
        # Remove the test file
        if os.path.exists(self.test_mappings_file):
            os.remove(self.test_mappings_file)

    def test_levenshtein_distance(self):
        self.assertEqual(levenshtein_distance("", ""), 0)
        self.assertEqual(levenshtein_distance("a", ""), 1)
        self.assertEqual(levenshtein_distance("", "a"), 1)
        self.assertEqual(levenshtein_distance("abc", "abc"), 0)
        self.assertEqual(levenshtein_distance("abc", "ab"), 1)
        self.assertEqual(levenshtein_distance("ab", "abc"), 1)
        self.assertEqual(levenshtein_distance("kitten", "sitting"), 3)

    def test_similarity(self):
        self.assertEqual(similarity("", ""), 1.0)
        self.assertEqual(similarity("a", ""), 0.0)
        self.assertEqual(similarity("", "a"), 0.0)
        self.assertEqual(similarity("abc", "abc"), 1.0)
        self.assertAlmostEqual(similarity("abc", "ab"), 0.6666666666666666)
        self.assertAlmostEqual(similarity("kitten", "sitting"), 0.5)

    @patch("memory.name_mapping.read_database")
    def test_get_all_student_names(self, mock_read_database):
        # Mock the database to return a list of rows with headers
        mock_read_database.return_value = [
            ["ยศ", "ชื่อ", "สกุล", "อื่นๆ"],
            ["น.พ.", "สมชาย", "ใจดี", "ข้อมูลเพิ่มเติม"],
            ["ร.ท.", "สมหญิง", "ดีใจ", "ข้อมูลเพิ่มเติม"],
            ["น.ท.", "ธีรภัทร์", "ขาวศรี", "ข้อมูลเพิ่มเติม"]
        ]
        names = get_all_student_names()
        # We expect variations: with title and without title
        expected = {
            "น.พ. สมชาย ใจดี",
            "สมชาย ใจดี",
            "ร.ท. สมหญิง ดีใจ",
            "สมหญิง ดีใจ",
            "น.ท. ธีรภัทร์ ขาวศรี",
            "ธีรภัทร์ ขาวศรี"
        }
        self.assertEqual(set(names), expected)

        # Call again to test caching
        names2 = get_all_student_names()
        self.assertEqual(names, names2)
        # The mock should still have been called only once? Actually, the function caches,
        # so the second call should not call the mock again.
        mock_read_database.assert_called_once()

    def test_get_corrected_keyword_exact(self):
        # First, add a mapping
        learn_mapping("ธีรภัทร์ ขาวศรี", "ธีรภัทร์ ขาวศรี")
        # Now test that it returns the exact match
        keyword, correction_type, suggestions = get_corrected_keyword("ธีรภัทร์ ขาวศรี")
        self.assertEqual(keyword, "ธีรภัทร์ ขาวศรี")
        self.assertEqual(correction_type, "exact")
        self.assertEqual(suggestions, [])

    def test_get_corrected_keyword_high_similarity(self):
        # We need to mock get_all_student_names to return a known set
        with patch("memory.name_mapping.get_all_student_names") as mock_get_names:
            mock_get_names.return_value = ["ธีรภัทร์ ขาวศรี", "สมชาย ใจดี"]
            # Test with a misspelling that is close enough (e.g., missing one character)
            keyword, correction_type, suggestions = get_corrected_keyword("ธีรภัทร์ ขาวศ")  # Missing 'รี' at the end?
            # We expect it to be corrected to "ธีรภัทร์ ขาวศรี" and the mapping to be learned
            self.assertEqual(correction_type, "high")
            self.assertEqual(keyword, "ธีรภัทร์ ขาวศรี")
            self.assertEqual(suggestions, [])  # For high similarity, we don't return suggestions

    def test_get_corrected_keyword_low_similarity(self):
        with patch("memory.name_mapping.get_all_student_names") as mock_get_names:
            mock_get_names.return_value = ["ธีรภัทร์ ขาวศรี", "สมชาย ใจดี"]
            # Test with a misspelling that is somewhat close but not high enough
            keyword, correction_type, suggestions = get_corrected_keyword("ธีรภัทร ขาวศรี")  # Missing one 'ท' in ธีรภัทร์?
            # We expect it to return the original keyword and a suggestion
            self.assertEqual(correction_type, "low")
            self.assertEqual(keyword, "ธีรภัทร ขาวศรี")  # The original keyword (not corrected)
            # The suggestion should be the closest match
            self.assertIn("ธีรภัทร์ ขาวศรี", suggestions)

    def test_get_corrected_keyword_none(self):
        with patch("memory.name_mapping.get_all_student_names") as mock_get_names:
            mock_get_names.return_value = ["ธีรภัทร์ ขาวศรี", "สมชาย ใจดี"]
            # Test with a completely different word
            keyword, correction_type, suggestions = get_corrected_keyword("จอห์น สมิท")
            self.assertEqual(correction_type, "none")
            self.assertEqual(keyword, "จอห์น สมิท")
            self.assertEqual(suggestions, [])

    def test_learn_mapping(self):
        # Learn a new mapping
        learn_mapping("มิสเปล", "คำที่ถูกต้อง")
        # Load the mappings and check
        mappings = _load_mappings()
        # The key should be normalized
        from memory.name_mapping import normalize
        expected_key = normalize("มิสเปล")
        self.assertEqual(mappings.get(expected_key), "คำที่ถูกต้อง")

if __name__ == '__main__':
    unittest.main()