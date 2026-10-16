"""Build data/markets.json for the prices page: commodities, currencies and stock indexes priced in sats.

Monthly closes since bitcoin's data start (Sep 2014) plus each item's latest price, all from Yahoo Finance.
Non-dollar prices are converted to dollars with that month's exchange rate, then to sats with that month's
bitcoin close. Standard library only, so the daily GitHub Action needs no installs.
Run: python3 scripts/update_data.py   (from the site folder)
"""
import datetime as dt, json, os, sys, time, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "markets.json")
UA = {"User-Agent": "Mozilla/5.0 (bitcoineatstheworld.com data refresh)"}

# Lists are chosen by a stated rule, never by how bitcoin looks against them (see "how picked" on the page).
GROUPS = {
    "commodities": {
        "title": "Commodities",
        "how": "The widely traded US commodity futures (metals, energy, grains, softs, livestock), front month.",
        "items": [
            ("gold", "GC=F", "Gold", "ounce"), ("silver", "SI=F", "Silver", "ounce"),
            ("platinum", "PL=F", "Platinum", "ounce"), ("palladium", "PA=F", "Palladium", "ounce"),
            ("copper", "HG=F", "Copper", "pound"), ("oil", "CL=F", "Oil (WTI)", "barrel"),
            ("brent", "BZ=F", "Oil (Brent)", "barrel"), ("natgas", "NG=F", "Natural gas", "MMBtu"),
            ("gasoline", "RB=F", "Gasoline (wholesale)", "gallon"), ("heatingoil", "HO=F", "Heating oil", "gallon"),
            ("wheat", "ZW=F", "Wheat", "bushel"), ("corn", "ZC=F", "Corn", "bushel"),
            ("soybeans", "ZS=F", "Soybeans", "bushel"), ("coffee", "KC=F", "Coffee", "pound"),
            ("sugar", "SB=F", "Sugar", "pound"), ("cocoa", "CC=F", "Cocoa", "metric ton"),
            ("cotton", "CT=F", "Cotton", "pound"), ("cattle", "LE=F", "Live cattle", "pound"),
            ("hogs", "HE=F", "Lean hogs", "pound"), ("oj", "OJ=F", "Orange juice", "pound"),
        ],
    },
    "currencies": {
        "title": "Currencies",
        "how": "The 20 most traded currencies in the BIS Triennial Survey (2022), one unit of each.",
        "items": [
            ("USD", None, "US dollar", "dollar"), ("EUR", "EURUSD=X", "Euro", "euro"),
            ("JPY", "JPY=X", "Japanese yen", "yen"), ("GBP", "GBPUSD=X", "British pound", "pound"),
            ("CNY", "CNY=X", "Chinese yuan", "yuan"), ("AUD", "AUDUSD=X", "Australian dollar", "dollar"),
            ("CAD", "CAD=X", "Canadian dollar", "dollar"), ("CHF", "CHF=X", "Swiss franc", "franc"),
            ("HKD", "HKD=X", "Hong Kong dollar", "dollar"), ("SGD", "SGD=X", "Singapore dollar", "dollar"),
            ("SEK", "SEK=X", "Swedish krona", "krona"), ("KRW", "KRW=X", "South Korean won", "won"),
            ("NOK", "NOK=X", "Norwegian krone", "krone"), ("NZD", "NZDUSD=X", "New Zealand dollar", "dollar"),
            ("INR", "INR=X", "Indian rupee", "rupee"), ("MXN", "MXN=X", "Mexican peso", "peso"),
            ("TWD", "TWD=X", "Taiwan dollar", "dollar"), ("ZAR", "ZAR=X", "South African rand", "rand"),
            ("BRL", "BRL=X", "Brazilian real", "real"), ("DKK", "DKK=X", "Danish krone", "krone"),
        ],
    },
    "indexes": {
        "title": "Stock indexes",
        "how": "The headline index of the world's biggest stock markets, plus the main US ones. Price indexes: dividends not included (DAX is the exception: it includes them).",
        "items": [
            ("sp500", "^GSPC", "S&P 500", "US"), ("nasdaq", "^IXIC", "Nasdaq Composite", "US"),
            ("dow", "^DJI", "Dow Jones", "US"), ("russell", "^RUT", "Russell 2000", "US"),
            ("nikkei", "^N225", "Nikkei 225", "Japan"), ("shanghai", "000001.SS", "Shanghai Composite", "China"),
            ("hangseng", "^HSI", "Hang Seng", "Hong Kong"), ("ftse", "^FTSE", "FTSE 100", "UK"),
            ("cac", "^FCHI", "CAC 40", "France"), ("dax", "^GDAXI", "DAX", "Germany"),
            ("stoxx50", "^STOXX50E", "Euro Stoxx 50", "Eurozone"), ("tsx", "^GSPTSE", "S&P/TSX", "Canada"),
            ("sensex", "^BSESN", "Sensex", "India"), ("asx", "^AXJO", "ASX 200", "Australia"),
            ("kospi", "^KS11", "KOSPI", "South Korea"),
        ],
    },
}
CURRENCY_FIX = {"^STOXX50E": "EUR"}  # Yahoo leaves the currency blank for these
START = "2014-09"  # bitcoin's Yahoo data start: fixed, stated, never moved


def fetch(symbol):
    # daily bars, then the last close of each month: Yahoo's own monthly bars skip months and coarsen to quarterly
    p1 = int(dt.datetime(2014, 9, 1, tzinfo=dt.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?period1={p1}&period2={int(time.time())}&interval=1d")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                res = json.load(r)["chart"]["result"][0]
            break
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    meta, closes = res["meta"], res["indicators"]["quote"][0]["close"]
    tz = dt.timezone(dt.timedelta(seconds=meta.get("gmtoffset", 0)))  # exchange-local dates
    months = {}
    for ts, c in zip(res.get("timestamp", []), closes):
        if c:  # later days overwrite earlier ones: each month keeps its last close (this month: the latest)
            months[dt.datetime.fromtimestamp(ts, tz).strftime("%Y-%m")] = c
    asof = dt.datetime.fromtimestamp(meta["regularMarketTime"], tz).strftime("%Y-%m-%d")
    cur = meta.get("currency") or CURRENCY_FIX.get(symbol)
    if not cur:
        raise ValueError(f"{symbol}: Yahoo gives no currency")
    return {"cur": cur, "months": months, "now": meta["regularMarketPrice"], "asof": asof}


def despike(series):
    """Drop one-month data glitches (e.g. Yahoo's TWD Dec 2014 at 10x): a value 3x off both neighbours
    while the neighbours agree. Real moves (crashes, spikes over several months) are untouched."""
    ms = list(series)
    bad = {ms[i] for i in range(1, len(ms) - 1)
           if (a := series[ms[i - 1]]) and (b := series[ms[i + 1]]) and (v := series[ms[i]])
           and 1 / 1.5 < a / b < 1.5 and not 1 / 3 < v / a < 3}
    for m in bad:
        print("  despiked", m, file=sys.stderr)
    return {m: v for m, v in series.items() if m not in bad}


def sig(x, n=4):
    return float(f"{x:.{n}g}")


def main():
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    raw, failed = {}, []
    syms = ["BTC-USD"] + [s for g in GROUPS.values() for _, s, _, _ in g["items"] if s]
    for s in syms:
        try:
            raw[s] = fetch(s)
        except Exception as e:
            failed.append(s); print("FAILED", s, e, file=sys.stderr)
        time.sleep(0.2)
    if "BTC-USD" in failed:
        sys.exit("No bitcoin data; keeping the old file.")
    btc = raw["BTC-USD"]
    months = sorted(m for m in btc["months"] if m >= START)

    # dollars per one unit of each currency, by month and now ("EURUSD=X" is already $ per unit; "JPY=X" is units per $)
    per = {"USD": ({m: 1.0 for m in months}, 1.0)}
    for key, s, _, _ in GROUPS["currencies"]["items"]:
        if s and s in raw:
            r, inv = raw[s], not s.endswith("USD=X")
            per[key] = ({m: (1 / v if inv else v) for m, v in r["months"].items()}, 1 / r["now"] if inv else r["now"])

    def to_usd(cur, value, month=None):
        div = 1
        if cur in ("USX", "GBp", "ZAc"):  # quoted in cents/pence
            cur, div = {"USX": "USD", "GBp": "GBP", "ZAc": "ZAR"}[cur], 100
        if cur not in per:
            return None
        rate = per[cur][1] if month is None else per[cur][0].get(month)
        return None if rate is None else value / div * rate

    out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "start": START,
           "btc": {"usd": btc["now"], "asof": btc["asof"]}, "groups": {}}
    for gkey, g in GROUPS.items():
        items = []
        for key, s, name, unit in g["items"]:
            if s and s not in raw:  # fetch failed today: keep yesterday's numbers for this one
                prev = next((i for i in old.get("groups", {}).get(gkey, {}).get("items", []) if i["id"] == key), None)
                if prev: items.append(prev)
                continue
            if gkey == "currencies":
                series_usd = {m: per[key][0].get(m) for m in months}
                now_usd, asof, cur = per[key][1], (raw[s]["asof"] if s else btc["asof"]), "USD"
            else:
                r = raw[s]
                series_usd = {m: to_usd(r["cur"], r["months"][m], m) for m in months if m in r["months"]}
                now_usd, asof, cur = to_usd(r["cur"], r["now"]), r["asof"], r["cur"]
            series_usd = despike({m: v for m, v in series_usd.items() if v and v > 0})
            series = [[m, sig(v / btc["months"][m] * 1e8)] for m, v in series_usd.items()]
            if not series or now_usd is None:
                print("SKIP (no data)", key, file=sys.stderr); continue
            items.append({"id": key, "name": name, "unit": unit, "symbol": s, "quote": cur,
                          "usd": sig(now_usd, 6), "asof": asof, "series": series})
        out["groups"][gkey] = {"title": g["title"], "how": g["how"], "items": items}
        print(f"{g['title']}: {len(items)} items")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("wrote", os.path.relpath(OUT), os.path.getsize(OUT), "bytes;", "failed:", failed or "none")


if __name__ == "__main__":
    import urllib.parse
    main()
