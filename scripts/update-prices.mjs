// scripts/update-prices.mjs
import fs from "node:fs/promises";

// If a ticker doesn't exist on Stooq under .us, add an override here.
const SYMBOL_OVERRIDES = {
  // Example if you find it doesn't resolve:
  // GOOGL: "googl.us",
  // or sometimes class/share symbols differ, e.g. GOOG:
  // GOOGL: "goog.us",
};

const TICKERS = ["AGI", "FSM", "GAU", "NFGC", "VGZ", "NEWP", "GOOGL"];

// Stooq uses lowercase tickers and usually needs an exchange suffix.
// Many US listings work as {ticker}.us
function stooqSymbol(t) {
  return SYMBOL_OVERRIDES[t] ?? `${t.toLowerCase()}.us`;
}

async function fetchCSV(url) {
  if (typeof fetch !== "function") {
    throw new Error(
      "Global fetch is not available. Use Node 18+ (recommended) or install a fetch polyfill."
    );
  }
  const res = await fetch(url, {
    headers: { "User-Agent": "mbd-bot" },
    redirect: "follow",
  });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status} ${res.statusText} ${url}`);
  return await res.text();
}

function parseStooqCSVLatestClose(csv) {
  // Stooq d/l CSV header: Date,Open,High,Low,Close,Volume
  // Usually ordered oldest->newest; grab the last valid data row.
  const lines = csv.trim().split(/\r?\n/);
  if (lines.length < 2) return null;

  // Walk backwards to find the most recent parseable close
  for (let i = lines.length - 1; i >= 1; i--) {
    const row = lines[i].split(",");
    if (row.length < 5) continue;
    const close = Number(row[4]);
    if (Number.isFinite(close) && close > 0) return close;
  }
  return null;
}

async function main() {
  const quotes = {};

  for (const t of TICKERS) {
    try {
      const sym = stooqSymbol(t);
      const url = `https://stooq.com/q/d/l/?s=${encodeURIComponent(sym)}&i=d`;
      const csv = await fetchCSV(url);
      const price = parseStooqCSVLatestClose(csv);
      if (price !== null) quotes[t] = { price };
    } catch (err) {
      // keep missing symbols absent; the site will fall back gracefully
      // Uncomment for debugging:
      // console.warn(`Failed ${t}:`, err?.message ?? err);
    }
  }

  const out = {
    asOf: new Date().toISOString(),
    source: "stooq",
    quotes,
  };

  await fs.mkdir("data", { recursive: true });
  await fs.writeFile("data/prices.json", JSON.stringify(out, null, 2) + "\n", "utf8");
  console.log("Updated data/prices.json:", out.asOf, Object.keys(quotes));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
