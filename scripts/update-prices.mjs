// scripts/update-prices.mjs
import fs from "node:fs/promises";

const TICKERS = ["AGI", "FSM", "GAU", "NFGC", "VGZ", "NEWP", "GOOGL"];

// Stooq uses lowercase tickers and may need exchange suffixes for some.
// For US stocks, many work as {ticker}.us
function stooqSymbol(t) {
  return `${t.toLowerCase()}.us`;
}

async function fetchCSV(url) {
  const res = await fetch(url, { headers: { "User-Agent": "mbd-bot" } });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status} ${url}`);
  return await res.text();
}

function parseStooqCSV(csv) {
  // Stooq d/l CSV header: Date,Open,High,Low,Close,Volume
  const lines = csv.trim().split("\n");
  if (lines.length < 2) return null;
  const row = lines[1].split(",");
  const close = Number(row[4]);
  if (!Number.isFinite(close) || close <= 0) return null;
  return close;
}

async function main() {
  const quotes = {};
  for (const t of TICKERS) {
    try {
      const sym = stooqSymbol(t);
      const url = `https://stooq.com/q/d/l/?s=${encodeURIComponent(sym)}&i=d`;
      const csv = await fetchCSV(url);
      const price = parseStooqCSV(csv);
      if (price !== null) quotes[t] = { price };
    } catch {
      // keep missing symbols absent; the site will fall back gracefully
    }
  }

  const out = {
    asOf: new Date().toISOString(),
    source: "stooq",
    quotes
  };

  await fs.mkdir("data", { recursive: true });
  await fs.writeFile("data/prices.json", JSON.stringify(out, null, 2) + "\n", "utf8");
  console.log("Updated data/prices.json:", out.asOf, Object.keys(quotes));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
