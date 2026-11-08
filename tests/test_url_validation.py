import unittest
from backend.server import extract_work_id


class WorkUrlValidationTests(unittest.TestCase):
    def test_work_url(self):
        self.assertEqual(extract_work_id("https://archiveofourown.org/works/123456"), "123456")

    def test_chapter_url(self):
        self.assertEqual(extract_work_id("https://archiveofourown.org/works/123456/chapters/987"), "123456")

    def test_rejects_other_domains(self):
        with self.assertRaises(ValueError):
            extract_work_id("https://example.com/works/123456")

    def test_rejects_non_work_paths(self):
        with self.assertRaises(ValueError):
            extract_work_id("https://archiveofourown.org/users/example")


if __name__ == "__main__":
    unittest.main()
