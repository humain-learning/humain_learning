import frappe as fp
from frappe.utils.data import get_datetime
from .constants import ZOOM_TOKEN_URL, GRANT_TYPE
from .utils import get_header
import requests
from frappe.utils import now_datetime
from datetime import timedelta

@fp.whitelist()
def fetch_and_store_token():
    """
    Fetch the access token from Zoom and store it.
    """

    creds = fp.get_single("Zoom Credentials")

    client_id = creds.client_id
    client_secret = creds.get_password("client_secret")
    
    headers = get_header(client_id, client_secret)

    params = {
        "grant_type": GRANT_TYPE,
        "account_id": creds.account_id,
    }

    response = requests.post(
        ZOOM_TOKEN_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    payload = response.json()

    if response.status_code != 200:
        fp.throw(
            f"Failed to fetch token: {payload}"
        )

    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in")

    if not access_token or not expires_in:
        fp.throw("Invalid token response from Zoom.")

    token_doc = fp.get_single("Zoom OAuth Token")

    token_doc.access_token = access_token
    token_doc.token_type = "Bearer"
    token_doc.expires_at = now_datetime() + timedelta(seconds=expires_in)
    token_doc.last_refreshed_at = now_datetime()  # or last_synced_at if that is your field

    token_doc.save(ignore_permissions=True)
    
    return True


def refresh_token():
    fetch_and_store_token()