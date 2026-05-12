import requests
import frappe
FACEBOOK_BASE_URL = "https://graph.facebook.com/"


def fetch_creds():
	creds = frappe.get_single("Meta CAPI Credentials")
	return creds.pixel_id, creds.get_password("access_token"), creds.version


def validate_credentials(creds):
	url = f"{FACEBOOK_BASE_URL}/{creds.version}/{creds.pixel_id}/events?fields=id&access_token={creds.get_password('access_token')}"
	payload = {
		"data": [
			{
				"event_name": "ValidateToken",
				"event_time": 1778145783,
				"event_id": "123456",
				"action_source": "system_generated",
				"user_data": {
					"em": ["9fbdefe2837a03c9225be80e741f316f4d174d1732b719b6abb6477efc1ae9d2"],
					"ph": ["d36e83082288d9f2c98b3f3f87cd317a31e95527cb09972090d3456a7430ad4d"],
					"lead_id": 1234567890123456
				},
				"custom_data": {
					"lead_event_source": "FCRM",
					"event_source": "crm"
				}
			}
		],
	}
	response = requests.post(url, json=payload)

	return response



def send_meta_event(event_id,payload):
	pixel_id, access_token, version = fetch_creds()
	url = f"{FACEBOOK_BASE_URL}/{version}/{pixel_id}/events?access_token={access_token}"

	response = requests.post(url, json=payload)
	frappe.logger("meta_capi").warning(f"{payload.get('data')[0].get('event_name')} Event sent for {event_id.split(':')[1]}")

	return response