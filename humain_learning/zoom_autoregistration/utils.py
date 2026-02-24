import xmltodict

def extract_error(r):
    # Try JSON
    try:
        data = r.json()
        return (
            r.status_code,
            data.get("code"),
            data.get("message")
        )
    except ValueError:
        pass

    # Try XML
    try:
        parsed = xmltodict.parse(r.text)
        # Root element (error, result, etc.)
        root = next(iter(parsed.values()))
        return (
            r.status_code,
            root.get("code"),
            root.get("message")
        )
    except Exception:
        pass

    # Fallback
    return (
        r.status_code,
        None,
        r.text
    )