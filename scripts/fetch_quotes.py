import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import os

API_KEY = "GUY8S89NSG15NVYH"
INTERVAL = "5min"

SYMBOLS = {
    "AGI": "AGI",
    "FSM": "FSM",
    "GAU": "GAU",
    "NFGC": "NFGC",
    "VGZ": "VGZ",
    "NEWP": "NEWP",
}

def http_get_json(params: dict) -> dict:
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def check_errors(data: dict):
    if "Note" in data:
        raise RuntimeError("Rate limited (Note)")
    if "Information" in data:
        raise RuntimeError(f"Information: {data['Information']}")
    if "Error Message" in data:
        raise RuntimeError(f"API error: {data['Error Message']}")

def fetch_intraday_close(av_symbol: str):
    data = http_get_json({
        "function": "TIME_SERIES_INTRADAY",
        "symbol": av_symbol,
        "interval": INTERVAL,
        "outputsize": "compact",
        "apikey": API_KEY,
    })
    check_errors(data)

    key = f"Time Series ({INTERVAL})"
    series = data.get(key)
    if not series or not isinstance(series, dict):
        raise RuntimeError("No intraday series returned (unsupported or empty)")

    latest_ts = sorted(series.keys())[-1]
    bar = series[latest_ts]
    px = float(bar["4. close"])
    if px <= 0:
        raise RuntimeError("Bad intraday close")
    return px, latest_ts

def main():
    out = {
        "asof_iso": datetime.now(timezone.utc).isoformat(),
        "last_trading_day": "—",
        "source": "alphavantage_intraday",
        "interval": INTERVAL,
        "prices": {},
        "errors": {}
    }

    last_ts_seen = ""

    items = list(SYMBOLS.items())
    for i, (internal, avsym) in enumerate(items):
        try:
            px, ts = fetch_intraday_close(avsym)
            out["prices"][internal] = px
            if ts and ts > last_ts_seen:
                last_ts_seen = ts
        except Exception as e:
            out["errors"][internal] = str(e)

        # free tier throttle
        if i < len(items) - 1:
            time.sleep(15)

    out["last_trading_day"] = last_ts_seen or "—"

    os.makedirs("data", exist_ok=True)
    with open("data/quotes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
