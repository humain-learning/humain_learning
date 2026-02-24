import base64


def get_header(client_id, client_secret):
    """
    Get the header for the Zoom API request.

    Args:
        client_id (str): The client ID of the Zoom app.
        client_secret (str): The client secret of the Zoom app.
    Returns:
        dict: The header for the Zoom API request.
    """
    encoded_credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
        ).decode()

    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }