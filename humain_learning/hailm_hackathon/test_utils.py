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


class TestPaymentPageUrl(unittest.TestCase):
	def test_prefills_name_phone_and_registration(self):
		from urllib.parse import parse_qs, urlsplit

		url = u.build_payment_page_url("https://pages.razorpay.com/pl_ABC123/view", "Aarav Sharma", "+91 98765 43210", "HHR-00012")
		parts = urlsplit(url)
		self.assertEqual(parts.netloc + parts.path, "pages.razorpay.com/pl_ABC123/view")
		q = parse_qs(parts.query)
		self.assertEqual(q["phone"], ["9876543210"])  # 10 digits, as Razorpay's docs show
		self.assertEqual(q["full_name"], ["Aarav Sharma"])
		self.assertEqual(q["registration_id"], ["HHR-00012"])

	def test_keeps_existing_query_params(self):
		from urllib.parse import parse_qs, urlsplit

		url = u.build_payment_page_url("https://pages.razorpay.com/pl_ABC/view?utm_source=wa", "A B", "9876543210", "HHR-00001")
		self.assertEqual(parse_qs(urlsplit(url).query)["utm_source"], ["wa"])


class TestSignature(unittest.TestCase):
	SECRET = "whsec_test"
	BODY = b'{"event":"payment.captured"}'

	def _sign(self, body, secret):
		import hashlib
		import hmac

		return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

	def test_valid(self):
		self.assertTrue(u.verify_razorpay_signature(self.BODY, self._sign(self.BODY, self.SECRET), self.SECRET))

	def test_tampered_body_or_wrong_secret(self):
		sig = self._sign(self.BODY, self.SECRET)
		self.assertFalse(u.verify_razorpay_signature(self.BODY + b" ", sig, self.SECRET))
		self.assertFalse(u.verify_razorpay_signature(self.BODY, sig, "other"))

	def test_missing_pieces_never_pass(self):
		# In particular: an unset secret must reject, not accept.
		sig = self._sign(self.BODY, self.SECRET)
		self.assertFalse(u.verify_razorpay_signature(self.BODY, sig, None))
		self.assertFalse(u.verify_razorpay_signature(self.BODY, None, self.SECRET))
		self.assertFalse(u.verify_razorpay_signature(b"", sig, self.SECRET))


class TestMatchKeys(unittest.TestCase):
	def test_finds_registration_id_and_phones_in_any_note_key(self):
		payment = {"contact": "+919876543210",
				   "notes": {"full_name": "Aarav", "registration_id": "HHR-00012", "phone": "9123456789", "email": "a@b.co"}}
		ids, mobiles = u.payment_match_keys(payment)
		self.assertEqual(ids, ["HHR-00012"])
		self.assertEqual(mobiles, ["+919123456789", "+919876543210"])

	def test_list_notes_and_no_notes(self):
		self.assertEqual(u.payment_match_keys({"notes": [], "contact": "9876543210"}), ([], ["+919876543210"]))
		self.assertEqual(u.payment_match_keys({}), ([], []))


class TestChooseRegistration(unittest.TestCase):
	"""The gate that decides whether an account-wide payment is a hackathon payment."""

	PRICE = 999

	def choose(self, payment, existing=(), unpaid=None):
		unpaid = unpaid or {}
		return u.choose_registration(payment, self.PRICE, lambda n: n in existing, lambda m: unpaid.get(m))

	def test_registration_id_is_an_exact_match(self):
		p = {"amount": 99900, "notes": {"registration_id": "HHR-00012"}, "contact": "+919000000000"}
		self.assertEqual(self.choose(p, existing={"HHR-00012"}), ("HHR-00012", "Registration ID"))

	def test_phone_and_amount_match(self):
		p = {"amount": 99900, "notes": {}, "contact": "+919876543210"}
		self.assertEqual(self.choose(p, unpaid={"+919876543210": "HHR-00007"}), ("HHR-00007", "Phone + amount"))

	def test_phone_alone_is_never_enough(self):
		# A registered parent paying for something else on the same Razorpay account.
		p = {"amount": 1250000, "notes": {}, "contact": "+919876543210"}
		name, why = self.choose(p, unpaid={"+919876543210": "HHR-00007"})
		self.assertIsNone(name)
		self.assertIn("amount", why)

	def test_already_paid_phone_does_not_match(self):
		# unpaid lookup only returns Unpaid rows, so a paid registration can't be re-matched by phone
		p = {"amount": 99900, "notes": {}, "contact": "+919876543210"}
		self.assertEqual(self.choose(p, unpaid={})[0], None)

	def test_unknown_registration_id_falls_back_to_phone(self):
		p = {"amount": 99900, "notes": {"registration_id": "HHR-99999"}, "contact": "+919876543210"}
		self.assertEqual(self.choose(p, existing=set(), unpaid={"+919876543210": "HHR-00007"}), ("HHR-00007", "Phone + amount"))

	def test_no_price_configured_rejects_phone_matches(self):
		p = {"amount": 99900, "notes": {}, "contact": "+919876543210"}
		self.assertIsNone(u.choose_registration(p, None, lambda n: False, lambda m: "HHR-00007")[0])


if __name__ == "__main__":
	unittest.main()
