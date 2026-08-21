import json
import os
import ssl
import certifi
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
TORN_API_BASE = "https://api.torn.com/v2/user/log"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def sanitize_key(value):
    return str(value or "").strip()


def build_torn_url(from_timestamp=None, to_timestamp=None):
    params = {
        "limit": 100,
        "log": "1112,1113,4201,4210",
    }

    if from_timestamp:
        params["from"] = from_timestamp
    if to_timestamp:
        params["to"] = to_timestamp

    return f"{TORN_API_BASE}?{urlencode(params)}"


def fetch_torn_logs(api_key, from_timestamp=None, to_timestamp=None):
    url = build_torn_url(from_timestamp, to_timestamp)
    request_object = Request(
        url,
        headers={
            "Authorization": f"ApiKey {api_key}",
            "User-Agent": "tFini Torn financial dashboard",
        },
    )

    with urlopen(request_object, timeout=20, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))

@app.get("/")
def dashboard():
    return render_template("index.html")


@app.get("/api/torn/transactions")
def transactions():
    api_key = sanitize_key(request.args.get("key") or os.environ.get("TORN_API_KEY"))
    if not api_key:
        return jsonify({"error": "A Torn API key is required. Provide ?key=... or set TORN_API_KEY."}), 400

    try:
        logs, api_error = fetch_torn_logs(
            api_key,
            request.args.get("from"),
            request.args.get("to"),
        )
    except HTTPError as error:
        return jsonify({"error": f"Torn API returned HTTP {error.code}"}), error.code
    except (TimeoutError, URLError) as error:
        return jsonify({"error": f"Unable to reach Torn API: {error}"}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Torn API returned an invalid JSON response."}), 502

    if api_error:
        payload, status_code = api_error
        return jsonify(payload), status_code

    return jsonify({
    "logs": logs,
    "fetchedAt": datetime.now(timezone.utc).isoformat(),
})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8787)), debug=os.environ.get("FLASK_DEBUG") == "1")
