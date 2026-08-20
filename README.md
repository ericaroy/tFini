# tFini - testing codex

A Flask-powered Torn City financial web dashboard that syncs a player's `moneylog` through a local Python API proxy and summarizes income, expenses, net change, balances, and searchable transactions.

## Features

- Flask web app with a dependency-light dashboard, KPI cards, transaction search, date filters, and demo data.
- Python proxy for Torn City API calls so API keys are not embedded in frontend source.
- Supports either a pasted key per sync or a server-side `TORN_API_KEY` environment variable.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8787`. The Flask server hosts both the dashboard and backend proxy.

## Configuration

Optionally set a Torn API key on the server before starting the app:

```bash
export TORN_API_KEY=your_torn_api_key
python app.py
```

The dashboard calls `/api/torn/transactions`, which forwards to Torn's user `moneylog` selection. Use the optional date inputs to send `from` and `to` Unix timestamp filters.
