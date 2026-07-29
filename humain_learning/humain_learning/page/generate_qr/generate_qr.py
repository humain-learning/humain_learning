import qrcode
import io
import frappe
import base64
from PIL import Image
from pathlib import Path
import math

APP_PATH = Path(frappe.get_app_path("humain_learning"))
LOGOS = {
	"Humain Learning": APP_PATH / "public" /"images" / "humain_learning_logo.png",
	"HAILM": APP_PATH / "public" / "images" / "hailm_logo.png",
}

BRAND_COLOURS = {
	"Humain Learning": {
		"primary": "#E7A572",
		"secondary": "#AAC191"
	},
	"HAILM": {
		"primary": "#253459",
		"secondary": "#FFFFFF"
	}
}

@frappe.whitelist(allow_guest=True)
def generate_qr_code(values):
	# print(values)
	values = validate_and_normalize(values)
	# print(values)
	qr = qrcode.QRCode(
		version=None,
		error_correction=qrcode.constants.ERROR_CORRECT_H,
		box_size=20,
		border=2
	)

	qr.add_data(values.data)
	qr.make(fit=True)

	fill = "black"
	bg = "white"

	if values.brand_colours:
		fill = BRAND_COLOURS[values.product][ "primary"]
		# bg = BRAND_COLOURS[values.product]["secondary"]

	img = qr.make_image(
		fill_color=fill,
		back_color=bg
	).convert("RGBA")

	if values.brand_logo:
		module = qr.box_size
		padding = module

		logo_path = LOGOS[values.product]
		logo = Image.open(logo_path).convert("RGBA")

		# Resize logo first
		logo_size = (img.width // 5, img.height // 5)
		logo.thumbnail(logo_size, Image.Resampling.LANCZOS)

		# Desired background size
		desired_w = logo.width + padding
		desired_h = logo.height + padding

		# Round up to full QR modules
		bg_w = math.ceil(desired_w / module) * module
		bg_h = math.ceil(desired_h / module) * module

		background = Image.new(
			"RGBA",
			(bg_w, bg_h),
			"white",
		)

		# Center logo inside the background
		logo_x = (bg_w - logo.width) // 2
		logo_y = (bg_h - logo.height) // 2

		background.paste(
			logo,
			(logo_x, logo_y),
			logo,
		)

		# Center background on the QR and snap to the module grid
		pos_x = ((img.width - bg_w) // 2 // module) * module
		pos_y = ((img.height - bg_h) // 2 // module) * module

		img.paste(background, (pos_x, pos_y), background)
	buffer = io.BytesIO()
	img.save(buffer, format="PNG")

	return {
    	"image": f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
	}



def validate_and_normalize(values):
	values = frappe.parse_json(values)
	if values.type == "URL" and not values.data.startswith("http"):
		frappe.throw("URL must start with http:// or https://")
	if values.type == "Text" and values.data.startswith("http"):
		frappe.throw("You selected Data Type as Text but the data provided is a URL. Please select URL or edit the text.")
	if values.product == "Personal Use":
		values.brand_logo = 0
		values.brand_colours = 0
	return values