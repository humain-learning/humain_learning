"""Unit tests for the pure HAILM Hackathon helpers.

These need no bench: `python -m unittest humain_learning/hailm_hackathon/test_utils.py`
(also picked up by `bench run-tests --module humain_learning.hailm_hackathon.test_utils`).
"""

import importlib.util
import os
import unittest
from datetime import datetime, timezone

_spec = importlib.util.spec_from_file_location("hh_utils", os.path.join(os.path.dirname(__file__), "utils.py"))
u = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(u)


class TestMobile(unittest.TestCase):
	def test_accepts_real_world_shapes(self):
		for raw in ("9876543210", "+91 98765 43210", "919876543210", "09876543210", "91919876543210", "98765-43210"):
			self.assertEqual(u.normalize_indian_mobile(raw), "+919876543210", raw)

	def test_rejects_bad_numbers(self):
		for raw in ("", None, "12345", "5876543210", "98765432101", "abcdefghij", "+1 415 555 0100"):
			with self.assertRaises(u.ValidationError, msg=raw):
				u.normalize_indian_mobile(raw)

	def test_whatsapp_destination_has_no_plus(self):
		self.assertEqual(u.whatsapp_destination("98765 43210"), "919876543210")


class TestName(unittest.TestCase):
	def test_collapses_whitespace(self):
		self.assertEqual(u.clean_full_name("  Aarav   Sharma "), "Aarav Sharma")

	def test_accepts_devanagari(self):
		self.assertEqual(u.clean_full_name("आरव शर्मा"), "आरव शर्मा")

	def test_rejects_junk(self):
		for raw in ("", " ", "a", "12345", "!!", "x" * 121):
			with self.assertRaises(u.ValidationError, msg=raw):
				u.clean_full_name(raw)

	def test_split(self):
		self.assertEqual(u.split_name("Aarav Kumar Sharma"), ("Aarav", "Kumar Sharma"))
		self.assertEqual(u.split_name("Aarav"), ("Aarav", ""))


class TestCode(unittest.TestCase):
	def test_shape_and_alphabet(self):
		for _ in range(200):
			code = u.generate_code()
			prefix, body = code.split("-")
			self.assertEqual(prefix, "HLHACK")
			self.assertEqual(len(body), 6)
			self.assertTrue(set(body) <= set(u.CODE_ALPHABET))
			self.assertFalse(set(body) & set("0O1IL"))


class TestDiscountPayload(unittest.TestCase):
	def setUp(self):
		self.now = datetime(2026, 9, 25, 6, 0, 0, tzinfo=timezone.utc)
		self.p = u.build_discount_code_payload("HLHACK-ABC234", "Aarav Sharma", "HHR-00001", now=self.now)

	def test_spec_open_100pct_single_use_students(self):
		# The spec: 100% off, open, students, single use.
		self.assertEqual(self.p["scope"], "open")
		self.assertEqual((self.p["valueType"], self.p["value"]), ("percentage", 100))
		self.assertEqual((self.p["maxRedemptions"], self.p["perUserCap"]), (1, 1))
		self.assertEqual(self.p["audiences"], ["student"])

	def test_locked_to_state_plus_national_package(self):
		self.assertEqual(self.p["productScope"], "olympiad")
		self.assertEqual(self.p["packageIds"], ["STU-S1N1"])

	def test_open_codes_need_end_date_and_campaign_label(self):
		# The LMS admin form rejects open codes without these.
		self.assertTrue(self.p["endsAt"])
		self.assertTrue(self.p["campaignLabel"].strip())

	def test_starts_now_in_utc(self):
		self.assertEqual(self.p["startsAt"], "2026-09-25T06:00:00.000Z")

	def test_overrides(self):
		p = u.build_discount_code_payload("C", "N", "R", ends_at="2026-10-01T00:00:00Z", package_ids=["X"])
		self.assertEqual((p["endsAt"], p["packageIds"]), ("2026-10-01T00:00:00Z", ["X"]))


class TestAisensy(unittest.TestCase):
	def test_params_follow_configured_order(self):
		p = u.build_aisensy_payload("k", "camp", "9876543210", "Aarav",
									{"name": "Aarav", "code": "HLHACK-ABC234"}, ["code", "name"])
		self.assertEqual(p["templateParams"], ["HLHACK-ABC234", "Aarav"])
		self.assertEqual(p["destination"], "919876543210")

	def test_unknown_param_is_a_config_error(self):
		with self.assertRaises(ValueError):
			u.build_aisensy_payload("k", "c", "9876543210", "A", {"name": "A"}, ["name", "nope"])


class TestMoney(unittest.TestCase):
	def test_paise_rounds_instead_of_truncating(self):
		self.assertEqual(u.amount_to_paise(999), 99900)
		self.assertEqual(u.amount_to_paise(999.99), 99999)
		self.assertEqual(u.amount_to_paise("499.5"), 49950)

	def test_paise_rejects_zero(self):
		with self.assertRaises(ValueError):
			u.amount_to_paise(0)

	def test_gst_inclusive(self):
		base, gst = u.gst_inclusive_breakup(1180)
		self.assertEqual((base, gst), (1000.0, 180.0))
		base, gst = u.gst_inclusive_breakup(999)
		self.assertAlmostEqual(base + gst, 999, places=2)


if __name__ == "__main__":
	unittest.main()
