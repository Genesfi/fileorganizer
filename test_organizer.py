import os
import unittest
import tempfile
import shutil
import re
from organizer import OrganizeThread
import config

class TestFileOrganizer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for scanning
        self.test_dir = tempfile.mkdtemp()
        
        # Build standard configuration for testing
        self.test_config = {
            "types": {
                "Videos": [".mp4", ".mov"],
                "Images": [".jpg", ".png"],
                "Documents": [".txt", ".pdf"],
                "Archives": [".zip"]
            },
            "included_categories": ["Videos", "Images", "Documents", "Others"],
            "except_folders": [],
            "regex_apply_types": {
                "Videos": False,
                "Images": True,
                "Documents": False
            },
            "keyword_apply_types": {},
            "enable_size_filter": False,
            "enable_datetime_filter": False,
            "filename_regex": ".*test.*",
            "blacklist": "spam\nbadword",
            "scan_subfolders": True
        }

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir)

    def test_get_file_category(self):
        # Instantiate a dummy thread
        thread = OrganizeThread(
            target_folder=self.test_dir,
            config=self.test_config,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        
        # Test standard mappings
        self.assertEqual(thread.get_file_category("movie.mp4", ".mp4"), "Videos")
        self.assertEqual(thread.get_file_category("pic.PNG", ".PNG"), "Images")
        self.assertEqual(thread.get_file_category("unknown.xyz", ".xyz"), "Others")
        
        # Test category selection logic (if category not in included_categories, it must return None to prevent fallback to Others)
        # Archives is not in included_categories list
        self.assertIsNone(thread.get_file_category("archive.zip", ".zip"))

    def test_get_file_category_with_keywords(self):
        # Build configuration with overlapping extensions but keyword filtering enabled
        keyword_config = {
            "types": {
                "Cosplayer A": [".jpg", ".png"],
                "Cosplayer B": [".jpg", ".png"],
                "General Images": [".jpg", ".png"]
            },
            "included_categories": ["Cosplayer A", "Cosplayer B", "General Images", "Others"],
            "keyword_apply_types": {
                "Cosplayer A": True,
                "Cosplayer B": True,
                "General Images": False
            },
            "keywords": {
                "Cosplayer A": ["Abaoye", "阿包"],
                "Cosplayer B": ["rioko", "凉凉子"]
            }
        }
        thread = OrganizeThread(
            target_folder=self.test_dir,
            config=keyword_config,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        
        # 1. Matches "Cosplayer A" keyword -> goes to Cosplayer A
        self.assertEqual(thread.get_file_category("Abaoye_pic1.jpg", ".jpg"), "Cosplayer A")
        self.assertEqual(thread.get_file_category("阿包也是兔娘.png", ".png"), "Cosplayer A")
        
        # 2. Matches "Cosplayer B" keyword -> goes to Cosplayer B
        self.assertEqual(thread.get_file_category("rioko_cos.jpg", ".jpg"), "Cosplayer B")
        self.assertEqual(thread.get_file_category("凉凉子_02.png", ".png"), "Cosplayer B")
        
        # 3. No cosplayer keyword matches -> falls back to "General Images" (where keyword matching is disabled)
        self.assertEqual(thread.get_file_category("random_image.jpg", ".jpg"), "General Images")
        
        # 4. If all matched categories required keywords and none matched, and no fallback is available:
        keyword_config_no_fallback = keyword_config.copy()
        keyword_config_no_fallback["included_categories"] = ["Cosplayer A", "Cosplayer B", "Others"]
        thread_no_fallback = OrganizeThread(
            target_folder=self.test_dir,
            config=keyword_config_no_fallback,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        self.assertIsNone(thread_no_fallback.get_file_category("random_image.jpg", ".jpg"))

    def test_apply_filters_regex(self):
        thread = OrganizeThread(
            target_folder=self.test_dir,
            config=self.test_config,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        
        # 1. Images regex is enabled (requires "test" in filename)
        is_valid_img, _ = thread.apply_filters("my_test_pic.png", "Images")
        self.assertTrue(is_valid_img)
        
        is_valid_img_bad, _ = thread.apply_filters("normal_pic.png", "Images")
        self.assertFalse(is_valid_img_bad)
        
        # 2. Videos regex is disabled (does not require "test" in filename)
        is_valid_vid, _ = thread.apply_filters("normal_video.mp4", "Videos")
        self.assertTrue(is_valid_vid)

    def test_apply_filters_keywords(self):
        thread = OrganizeThread(
            target_folder=self.test_dir,
            config=self.test_config,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        
        # Define keywords config
        thread.config["keyword_apply_types"] = {
            "Documents": True,
            "Videos": False
        }
        thread.config["keywords"] = {
            "Documents": ["invoice", "report"]
        }
        thread.config["blacklist"] = "spam\nvirus" # global blacklist
        
        # Test category keywords match (Documents keywords is active, contains invoice/report)
        is_valid_doc, _ = thread.apply_filters("my_invoice_file.txt", "Documents")
        self.assertTrue(is_valid_doc)
        
        is_valid_doc_bad, reason = thread.apply_filters("normal_file.txt", "Documents")
        self.assertFalse(is_valid_doc_bad)
        self.assertEqual(reason, "keyword_mismatch")
        
        # Test category keywords inactive (Videos has keyword_apply_types=False)
        is_valid_vid, _ = thread.apply_filters("normal_video.mp4", "Videos")
        self.assertTrue(is_valid_vid)
        
        # Test global blacklist match
        is_valid_spam, reason_spam = thread.apply_filters("my_spam_invoice.txt", "Documents")
        self.assertFalse(is_valid_spam)
        self.assertEqual(reason_spam, "blacklisted_keyword")

    def test_apply_filters_size(self):
        thread = OrganizeThread(
            target_folder=self.test_dir,
            config=self.test_config,
            log_queue=None,
            progress_callback=None,
            conflict_resolver=None,
            on_complete=None
        )
        
        # Create temp file
        temp_file = os.path.join(self.test_dir, "size_test.txt")
        with open(temp_file, "w") as f:
            f.write("A" * 1024) # 1 KB file
            
        # Enable Size Filter (Min 2 KB)
        thread.config["enable_size_filter"] = True
        thread.config["min_size"] = 2
        thread.config["min_size_unit"] = "KB"
        thread.config["max_size"] = 0
        
        is_valid, reason = thread.apply_filters(temp_file, "Documents")
        self.assertFalse(is_valid)
        self.assertEqual(reason, "too_small")
        
        # Change Min 500 B
        thread.config["min_size"] = 500
        thread.config["min_size_unit"] = "B"
        is_valid_ok, _ = thread.apply_filters(temp_file, "Documents")
        self.assertTrue(is_valid_ok)

if __name__ == "__main__":
    unittest.main()
