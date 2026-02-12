import json
import time
import urllib.request
from datetime import datetime, timezone

# Stooq daily snapshot CSV:
# https://stooq.com/q/l/?s=agi.us&f=sd2t2ohlcv&h&e=csv
# fields: s = symbol, d2 = date, t2 = time, o = open, h = high, l = low, c = close, v = volume

TICKERS = {
    "AGI": "agi.us",
    "FSM": "fsm.us",
    "GAU": "gau.us",
    "NFGC": "nfgc.us",
    "VGZ": "vgz.us",
    "NEWP": "newp.us",
}

def fetch_csv(symbol: str) -> str:
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_latest(csv_text: str):
    lines = [ln.strip() for ln in csv_text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    header = lines[0].split(",")
    row = lines[1].split(",")
    if len(row) != len(header):
        return None

    data = dict(zip(header, row))
    # Expect columns: Symbol,Date,Time,Open,High,Low,Close,Volume
    # Sometimes Stooq returns "N/A" values
    def fnum(x):
        try:
            return float(x)
        except:
            return None

    return {
        "date": data.get("Date"),
        "time": data.get("Time"),
        "open": fnum(data.get("Open")),
        "price": fnum(data.get("Close")),  # "Close" as current snapshot
    }

def main():
    out = {
        "asOf": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "stooq",
        "quotes": {}
    }

    for tkr, stooq_symbol in TICKERS.items():
        try:
            csv_text = fetch_csv(stooq_symbol)
            q = parse_latest(csv_text)
            if q and (q["open"] is not None or q["price"] is not None):
                out["quotes"][tkr] = {"open": q["open"], "price": q["price"]}
            else:
                out["quotes"][tkr] = {"open": None, "price": None}
        except Exception:
            out["quotes"][tkr] = {"open": None, "price": None}

        time.sleep(0.8)  # be polite

    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()
