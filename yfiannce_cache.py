import argparse
import time
import tempfile
import warnings
from datetime import timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "data" / "scrape_dates.csv"
OUTPUT_PATH = ROOT / "data" / "scrape_dates_prices.csv"
REQUESTS_PER_MINUTE = 60
SLEEP_TIME = 60.0 / REQUESTS_PER_MINUTE
RETRY_COUNT = 3


warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*inplace keyword.*")
warnings.filterwarnings("ignore", module="yfinance")

session = requests.Session()
session.headers["User-Agent"] = (
    "DSA405-student-coursework (NC State; teaching exercise)"
)


def write_cache(rows: dict[tuple[str, str], str]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {"ticker": ticker, "date": date, "price": price}
            for (ticker, date), price in sorted(rows.items())
        ],
        columns=["ticker", "date", "price"],
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=OUTPUT_PATH.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            frame.to_csv(temporary_file, index=False, na_rep="NaN")
        temporary_path.replace(OUTPUT_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def append_cache_entry(ticker: str, date: str, price: str) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"ticker": ticker, "date": date, "price": price}]).to_csv(
        OUTPUT_PATH,
        mode="a",
        header=not OUTPUT_PATH.exists(),
        index=False,
        na_rep="NaN",
    )


def load_requests() -> list[tuple[str, str]]:
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Ticker/date request file not found: {INPUT_PATH}")
    requests_df = pd.read_csv(
        INPUT_PATH,
        dtype={"ticker": str, "date": str},
        keep_default_na=False,
    )
    if not {"ticker", "date"}.issubset(requests_df.columns):
        raise ValueError(f"{INPUT_PATH} must contain ticker and date columns.")

    requests_df["ticker"] = requests_df["ticker"].str.strip()
    parsed_dates = pd.to_datetime(requests_df["date"], errors="coerce")
    invalid_rows = requests_df["ticker"].eq("") | parsed_dates.isna()
    if invalid_rows.any():
        raise ValueError(
            "Invalid ticker/date request rows: "
            f"{requests_df.loc[invalid_rows, ['ticker', 'date']].head().to_dict('records')}"
        )
    requests_df["date"] = parsed_dates.dt.normalize().dt.strftime("%Y-%m-%d")
    return list(
        requests_df.drop_duplicates(["ticker", "date"])
        .sort_values(["ticker", "date"])[["ticker", "date"]]
        .itertuples(index=False, name=None)
    )


def load_cached_prices() -> dict[tuple[str, str], str]:
    if not OUTPUT_PATH.exists():
        return {}
    cached_df = pd.read_csv(
        OUTPUT_PATH,
        dtype={"ticker": str, "date": str, "price": str},
        keep_default_na=False,
    )
    if not {"ticker", "date", "price"}.issubset(cached_df.columns):
        raise ValueError(f"{OUTPUT_PATH} must contain ticker, date, and price columns.")

    cached_df["ticker"] = cached_df["ticker"].str.strip()
    parsed_dates = pd.to_datetime(cached_df["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError(f"{OUTPUT_PATH} contains invalid dates.")
    cached_df["date"] = parsed_dates.dt.normalize().dt.strftime("%Y-%m-%d")
    cached_df["price"] = cached_df["price"].str.strip()
    cached_df = cached_df.drop_duplicates(["ticker", "date"], keep="last")
    return {
        (row.ticker, row.date): row.price
        for row in cached_df.itertuples(index=False)
    }


def fetch_high_price(ticker: str, date: str) -> tuple[str, str]:
    requested_date = pd.Timestamp(date)
    start_date = (requested_date - timedelta(days=10)).strftime("%Y-%m-%d")
    end_date = (requested_date + timedelta(days=1)).strftime("%Y-%m-%d")

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            stock = yf.Ticker(ticker, session=session)
            history = stock.history(start=start_date, end=end_date)
            if history.empty or "High" not in history.columns:
                print("No data (invalid ticker or no historical price) -> NaN")
                return "NaN", ""

            high_price = history["High"].iloc[-1]
            actual_date = history.index[-1].strftime("%Y-%m-%d")
            if pd.isna(high_price):
                print("No daily high available -> NaN")
                return "NaN", actual_date
            price = str(round(float(high_price), 4))
            return price, actual_date
        except Exception as error:
            print(f"\n   Attempt {attempt}/{RETRY_COUNT} failed: {error}", end=" ")
            if attempt < RETRY_COUNT:
                time.sleep(SLEEP_TIME)

    return "NaN", ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and cache daily high prices for requested ticker/date pairs."
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry cached ticker/date pairs whose price is NaN.",
    )
    args = parser.parse_args()

    requests_to_fetch = load_requests()
    cached_prices = load_cached_prices()
    if OUTPUT_PATH.exists():
        # Compact any interrupted/retried append records before this run.
        write_cache(cached_prices)

    print(
        f"Starting scrape for {len(requests_to_fetch):,} unique ticker/date pairs. "
        f"Prices will be saved to {OUTPUT_PATH}."
    )
    for index, (ticker, date) in enumerate(requests_to_fetch, start=1):
        key = (ticker, date)
        current_price = cached_prices.get(key, "")
        is_failed_cache = current_price.strip().lower() == "nan"
        if current_price and not (args.retry_failed and is_failed_cache):
            continue

        print(
            f"[{index}/{len(requests_to_fetch)}] Fetching High for {ticker} on {date}...",
            end=" ",
        )
        price, actual_date = fetch_high_price(ticker, date)
        cached_prices[key] = price
        append_cache_entry(ticker, date, price)

        if price == "NaN":
            print("No price cached.")
        elif actual_date != date:
            print(f"Success: {price} (used previous market date: {actual_date})")
        else:
            print(f"Success: {price}")

        time.sleep(SLEEP_TIME)

    # Keep one row per key even when a previous run was interrupted mid-retry.
    write_cache(cached_prices)
    print(f"\nScraping complete. Cached prices: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
