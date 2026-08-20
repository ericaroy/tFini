import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
TORN_API_BASE = "https://api.torn.com/user/"


def sanitize_key(value):
    return str(value or "").strip()


def build_torn_url(api_key, from_timestamp=None, to_timestamp=None):
    params = {
        "selections": "moneylog",
        "key": api_key,
    }
    if from_timestamp:
        params["from"] = from_timestamp
    if to_timestamp:
        params["to"] = to_timestamp
    return f"{TORN_API_BASE}?{urlencode(params)}"


def fetch_torn_moneylog(api_key, from_timestamp=None, to_timestamp=None):
    url = build_torn_url(api_key, from_timestamp, to_timestamp)
    request_object = Request(url, headers={"User-Agent": "tFini Torn financial dashboard"})

    with urlopen(request_object, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("error"):
        error = payload["error"]
        message = error.get("error", "Torn API error")
        code = error.get("code")
        return None, ({"error": message, "code": code}, 400)

    return payload.get("moneylog", {}), None


@app.get("/")
def dashboard():
    return render_template("index.html")


@app.get("/api/torn/transactions")
def transactions():
    api_key = sanitize_key(request.args.get("key") or os.environ.get("TORN_API_KEY"))
    if not api_key:
        return jsonify({"error": "A Torn API key is required. Provide ?key=... or set TORN_API_KEY."}), 400

    try:
        moneylog, api_error = fetch_torn_moneylog(
            api_key,
            request.args.get("from"),
            request.args.get("to"),
        )
    except HTTPError as error:
        return jsonify({"error": f"Torn API returned HTTP {error.code}"}), error.code
    except (TimeoutError, URLError) as error:
        return jsonify({"error": "Unable to reach Torn API.", "details": str(error)}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Torn API returned an invalid JSON response."}), 502

    if api_error:
        payload, status_code = api_error
        return jsonify(payload), status_code

    return jsonify({"moneylog": moneylog, "fetchedAt": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8787)), debug=os.environ.get("FLASK_DEBUG") == "1")
