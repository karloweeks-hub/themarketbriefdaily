import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import os

API_KEY = "GUY8S89NSG15NVYH"

SYMBOLS = {
    "AGI": "AGI",
    "FSM": "FSM",
    "GAU": "GAU",
    "NFGC": "NFGC",
    "VGZ": "VGZ",
    "NEWP": "NEWP",
}

INTRADAY_INTERVAL = "5min"

TOTAL_CAPITAL = 100000

TARGET_DOLLARS = {
    "AGI": 2000,
    "FSM": 1500,
    "GAU": 1000,
    "NFGC": 800,
    "VGZ": 700,
    "NEWP": 1000,
}

ENTRY = {
    "AGI": 42.855,
    "FSM": 10.46,
    "GAU": 2.765,
    "NFGC": 2.735,
    "VGZ": 2.675,
    "NEWP": 3.58,
}

def http_get_json(params: dict) -> dict:
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)

def check_common_errors(data: dict):
    if "Note" in data:
        raise RuntimeError("Rate limited")
    if "Information" in data:
        raise RuntimeError(data["Information"])
    if "Error Message" in data:
        raise RuntimeError(data["Error Message"])

def fetch_global_quote(symbol):
    data = http_get_json({
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY,
    })
    check_common_errors(data)
    q = data.get("Global Quote") or {}
    px = q.get("05. price")
    day = q.get("07. latest trading day") or ""
    if not px:
        raise RuntimeError("Empty GLOBAL_QUOTE")
    return float(px), day

def fetch_intraday(symbol):
    data = http_get_json({
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": INTRADAY_INTERVAL,
        "outputsize": "compact",
        "apikey": API_KEY,
    })
    check_common_errors(data)
    key = f"Time Series ({INTRADAY_INTERVAL})"
    series = data.get(key)
    if not series:
        raise RuntimeError("Empty INTRADAY")
    ts = sorted(series.keys())[-1]
    return float(series[ts]["4. close"]), ts

def fetch_price(symbol):
    try:
        return fetch_global_quote(symbol)
    except:
        return fetch_intraday(symbol)

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    quotes = {
        "asof_iso": datetime.now(timezone.utc).isoformat(),
        "last_trading_day": "—",
        "source": "alphavantage",
        "prices": {},
        "errors": {}
    }

    last_ts = ""

    for i, (k, sym) in enumerate(SYMBOLS.items()):
        try:
            px, ts = fetch_price(sym)
            quotes["prices"][k] = px
            if ts and ts > last_ts:
                last_ts = ts
        except Exception as e:
            quotes["errors"][k] = str(e)
        time.sleep(15)

    quotes["last_trading_day"] = last_ts or "—"
    save_json("data/quotes.json", quotes)

    # --------- PERFORMANCE SNAPSHOT ---------
    perf = load_json("data/performance.json", {
        "inception": "2026-02-12",
        "currency": "USD",
        "nav_history": []
    })

    INITIAL_INVESTED = sum(TARGET_DOLLARS.values())
    INITIAL_CASH = max(0, TOTAL_CAPITAL - INITIAL_INVESTED)

    invested_mv = 0.0
    for k, px in quotes["prices"].items():
        sh = TARGET_DOLLARS[k] / ENTRY[k]
        invested_mv += sh * px

    nav = invested_mv + INITIAL_CASH
    ret = (nav / TOTAL_CAPITAL - 1) * 100

    today = datetime.now(timezone.utc).date().isoformat()

    if not perf["nav_history"] or perf["nav_history"][-1]["date"] != today:
        perf["nav_history"].append({
            "date": today,
            "nav": round(nav, 2),
            "return_pct": round(ret, 3)
        })

    save_json("data/performance.json", perf)

if __name__ == "__main__":
    main()
