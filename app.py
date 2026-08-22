import json
import os
import ssl
import time
import certifi
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlencode, urlparse

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
TORN_API_BASE = "https://api.torn.com/v2/user/log"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def sanitize_key(value):
    return str(value or "").strip()

ITEM_NAME_CACHE = {}
ITEM_NAME_CACHE_EXPIRES_AT = 0

def fetch_all_item_names(api_key):
    global ITEM_NAME_CACHE, ITEM_NAME_CACHE_EXPIRES_AT

    if ITEM_NAME_CACHE and time.time() < ITEM_NAME_CACHE_EXPIRES_AT:
        return ITEM_NAME_CACHE

    request_object = Request(
        "https://api.torn.com/v2/torn/items",
        headers={
            "Authorization": f"ApiKey {api_key}",
            "User-Agent": "tFini Torn financial dashboard",
        },
    )

    with urlopen(request_object, timeout=20, context=SSL_CONTEXT) as response:
        payload = json.loads(response.read().decode("utf-8"))

    ITEM_NAME_CACHE = {
        str(item["id"]): item["name"]
        for item in payload.get("items", [])
    }

    ITEM_NAME_CACHE_EXPIRES_AT = time.time() + 86400  # 24 hours
    return ITEM_NAME_CACHE

def build_torn_url(from_timestamp=None, to_timestamp=None, page_url=None):
    if page_url:
        parsed = urlparse(page_url)

        if (
            parsed.scheme != "https"
            or parsed.netloc != "api.torn.com"
            or parsed.path != "/v2/user/log"
        ):
            raise ValueError("Invalid Torn pagination link.")

        allowed_params = {"limit", "log", "from", "to", "nanostamp"}
        supplied_params = parse_qs(parsed.query)

        params = {
            key: values[-1]
            for key, values in supplied_params.items()
            if key in allowed_params
        }

        return f"{TORN_API_BASE}?{urlencode(params)}"

    params = {
        "limit": 100,
        "log": "1112,1113,4201,4210",
    }

    if from_timestamp:
        params["from"] = from_timestamp
    if to_timestamp:
        params["to"] = to_timestamp

    return f"{TORN_API_BASE}?{urlencode(params)}"


def fetch_torn_logs(api_key, from_timestamp=None, to_timestamp=None, page_url=None):
    url = build_torn_url(from_timestamp, to_timestamp, page_url)
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
        payload = fetch_torn_logs(
    api_key,
    request.args.get("from"),
    request.args.get("to"),
    request.args.get("page"),
    )
  
    except HTTPError as error:
        return jsonify({"error": f"Torn API returned HTTP {error.code}"}), error.code
    except (TimeoutError, URLError) as error:
        return jsonify({"error": f"Unable to reach Torn API: {error}"}), 502
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except json.JSONDecodeError:
        return jsonify({"error": "Torn API returned an invalid JSON response."}), 502

    if payload.get("error"):
        error = payload["error"]
        return jsonify({
            "error": error.get("error", "Torn API error"),
            "code": error.get("code"),
        }), 400

    logs = payload.get("log", [])
    
    print("Fetched Torn log entries:", len(logs))



    item_ids = set()

    item_names = fetch_all_item_names(api_key)
  

    return jsonify({
        "logs": logs,
        "itemNames": item_names,
        "pagination": payload.get("_metadata", {}).get("links", {}),
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8787)), debug=os.environ.get("FLASK_DEBUG") == "1")
