"""Pure helpers for the HAILM Hackathon flow.

Nothing in here imports frappe, so it can be unit-tested without a bench.
"""

import re
import secrets
from datetime import datetime, timezone

# Unambiguous alphabet: no 0/O, 1/I/L, so codes survive being read aloud or typed off WhatsApp.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_PREFIX = "HLHACK"

# The paid offer = Delhi hackathon + 1 State + 1 National Olympiad. On the LMS that is the
# student "state_national" package, whose package id is STU-S1N1. Pinning the code to it stops
# a 100% code from being spent on a pricier package (e.g. all_three).
DEFAULT_PACKAGE_IDS = ["STU-S1N1"]

# Registration for the last upcoming State round (11 Oct 2026) closes 7 Oct. After that the
# STU-S1N1 package has no State slot left to pick, so the code is useless — expire it then.
DEFAULT_CODE_ENDS_AT = "2026-10-07T23:59:59.999+05:30"

NAME_MAX_LEN = 120


class ValidationError(ValueError):
	"""Raised for user-correctable input problems. The message is safe to show to the user."""


def normalize_indian_mobile(raw):
	"""Return a canonical '+91XXXXXXXXXX' string, or raise ValidationError.

	Accepts 10-digit numbers, a leading 0, a 91 prefix, and a doubled 9191 prefix — the
	shapes seen in real LMS data. Indian mobiles start 6-9.
	"""
	digits = re.sub(r"\D", "", str(raw or ""))
	if len(digits) == 14 and digits.startswith("9191"):
		digits = digits[4:]
	elif len(digits) == 12 and digits.startswith("91"):
		digits = digits[2:]
	elif len(digits) == 11 and digits.startswith("0"):
		digits = digits[1:]

	if len(digits) != 10 or digits[0] not in "6789":
		raise ValidationError("Enter a valid 10-digit Indian mobile number.")
	return "+91" + digits


def clean_full_name(raw):
	name = re.sub(r"\s+", " ", str(raw or "")).strip()
	if len(name) < 2:
		raise ValidationError("Enter the student's full name.")
	if len(name) > NAME_MAX_LEN:
		raise ValidationError("That name is too long.")
	if not re.search(r"[A-Za-zऀ-ॿ]", name):
		raise ValidationError("Enter the student's full name.")
	return name


def split_name(full_name):
	parts = full_name.split(" ", 1)
	return parts[0], (parts[1] if len(parts) > 1 else "")


def generate_code(length=6, rand=secrets.choice):
	return f"{CODE_PREFIX}-" + "".join(rand(CODE_ALPHABET) for _ in range(length))


def build_discount_code_payload(code, student_name, registration_name, ends_at=None,
								package_ids=None, now=None):
	"""Payload for POST /payments/discount-codes on the HAILM LMS.

	Verified against staging on 2026-09-25: this exact shape creates an active code.
	Note `audiences` is stripped server-side for open codes (the admin UI never sends it for
	open scope), so the student-only restriction is enforced by the STU- package lock instead.
	"""
	now = now or datetime.now(timezone.utc)
	return {
		"code": code,
		"name": f"HAILM Hackathon - {student_name}"[:100],
		"description": f"Humain Learning x HAILM Hackathon. Registration {registration_name}.",
		"scope": "open",
		"valueType": "percentage",
		"value": 100,
		"productScope": "olympiad",
		"courseIds": [],
		"packageIds": list(package_ids or DEFAULT_PACKAGE_IDS),
		"schoolIds": [],
		"audiences": ["student"],
		"startsAt": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
		"endsAt": ends_at or DEFAULT_CODE_ENDS_AT,
		"maxRedemptions": 1,
		"perUserCap": 1,
		"campaignLabel": "Humain Learning x HAILM Hackathon",
	}


def whatsapp_destination(mobile):
	"""AiSensy wants the number with country code and no '+'."""
	return normalize_indian_mobile(mobile).lstrip("+")


def build_aisensy_payload(api_key, campaign_name, mobile, first_name, values, param_order):
	"""Payload for AiSensy's Campaign API v2.

	`param_order` is the list of value keys, in template order, e.g. ["name", "code"]. It is
	config-driven because the approved template's placeholder order is not known yet.
	"""
	missing = [key for key in param_order if key not in values]
	if missing:
		raise ValueError(f"Unknown AiSensy template param(s): {', '.join(missing)}")
	return {
		"apiKey": api_key,
		"campaignName": campaign_name,
		"destination": whatsapp_destination(mobile),
		"userName": first_name or "Student",
		"templateParams": [str(values[key]) for key in param_order],
		"source": "humainlearning-hailm-hackathon",
		"media": {},
		"buttons": [],
		"carouselCards": [],
		"location": {},
		"attributes": {},
		"paramsFallbackValue": {"FirstName": "Student"},
	}


def amount_to_paise(amount):
	"""Razorpay takes integer paise. The existing course flow used cint(amount)*100, which
	silently drops paise; round instead."""
	paise = int(round(float(amount) * 100))
	if paise <= 0:
		raise ValueError("Amount must be positive.")
	return paise


def gst_inclusive_breakup(amount, rate=0.18):
	"""The offer price is the all-in amount the student pays. Split out the GST component
	for the record, rather than adding GST on top like the course checkout does."""
	amount = float(amount)
	base = round(amount / (1 + rate), 2)
	return base, round(amount - base, 2)
