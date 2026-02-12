import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse

API_KEY = "GUY8S89NSG15NVYH"

# Try these first. If some fail, we'll see it in errors.
# If a ticker is Canadian/TSX and fails, you may need ".TO" mapping here.
SYMBOLS = {
    "AGI": "AGI",
    "FSM": "FSM",
    "GAU": "GAU",
    "NFGC": "NFGC",
    "VGZ": "VGZ",
    "NEWP": "NEWP",
}

INTRADAY_INTERVAL = "5min"

def http_get_json(params: dict) -> dict:
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def check_common_errors(data: dict):
    if "Note" in data:
        raise RuntimeError("Rate limited (Note).")
    if "Information" in data:
        raise RuntimeError(f"Information: {data['Information']}")
    if "Error Message" in data:
        raise RuntimeError(f"API error: {data['Error Message']}")

def fetch_global_quote(av_symbol: str):
    data = http_get_json({
        "function": "GLOBAL_QUOTE",
        "symbol": av_symbol,
        "apikey": API_KEY,
    })
    check_common_errors(data)
    q = data.get("Global Quote") or {}
    px = q.get("05. price")
    day = q.get("07. latest trading day") or ""
    if not px:
        raise RuntimeError("GLOBAL_QUOTE empty")
    price = float(px)
    if price <= 0:
        raise RuntimeError("GLOBAL_QUOTE bad price")
    return price, day

def fetch_intraday_close(av_symbol: str):
    data = http_get_json({
        "function": "TIME_SERIES_INTRADAY",
        "symbol": av_symbol,
        "interval": INTRADAY_INTERVAL,
        "outputsize": "compact",
        "apikey": API_KEY,
    })
    check_common_errors(data)
    key = f"Time Series ({INTRADAY_INTERVAL})"
    series = data.get(key)
    if not series or not isinstance(series, dict):
        raise RuntimeError("INTRADAY empty/unsupported")
    latest_ts = sorted(series.keys())[-1]
    bar = series[latest_ts]
    price = float(bar["4. close"])
    if price <= 0:
        raise RuntimeError("INTRADAY bad close")
    return price, latest_ts

def fetch_best_effort(av_symbol: str):
    # Try GLOBAL_QUOTE, then fallback to INTRADAY
    try:
        return fetch_global_quote(av_symbol)
    except Exception:
        return fetch_intraday_close(av_symbol)

def main():
    out = {
        "asof_iso": datetime.now(timezone.utc).isoformat(),
        "last_trading_day": "—",
        "source": "alphavantage",
        "prices": {},
        "errors": {},
    }

    last_stamp = ""

    items = list(SYMBOLS.items())
    for i, (internal, avsym) in enumerate(items):
        try:
            price, stamp = fetch_best_effort(avsym)
            out["prices"][internal] = price
            if stamp and stamp > last_stamp:
                last_stamp = stamp
        except Exception as e:
            out["errors"][internal] = str(e)

        # Free tier: be conservative
        if i < len(items) - 1:
            time.sleep(15)

    out["last_trading_day"] = last_stamp or "—"

    # Always write file (even if errors)
    with open("data/quotes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
