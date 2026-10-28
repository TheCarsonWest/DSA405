import os
import time
import warnings
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import timedelta

# --- Suppress Pandas deprecation warnings from yfinance ---
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message=".*inplace keyword.*")
warnings.filterwarnings('ignore', module='yfinance')

# File configuration
FILE_PATH = './data/scrape_dates.csv'
REQUESTS_PER_MINUTE = 30
SLEEP_TIME = 60.0 / REQUESTS_PER_MINUTE  # 1.2 seconds per request

def main():
    # 1. Verify the file exists
    if not os.path.exists(FILE_PATH):
        print(f"Error: The file {FILE_PATH} does not exist.")
        return

    # 2. Read the CSV file
    df = pd.read_csv(FILE_PATH)

    # 3. Add the 'price' column if it doesn't exist
    if 'price' not in df.columns:
        df['price'] = np.nan

    # Identify the first column (Ticker) and second column (Date)
    ticker_col = df.columns[0]
    date_col = df.columns[1]

    print(f"Starting scrape. Using '{ticker_col}' for tickers and '{date_col}' for dates.")

    # 4. Iterate over the rows
    for index, row in df.iterrows():
        # Check if the price is already scraped/cached
        current_price = row['price']
        if pd.notna(current_price) and str(current_price).strip().lower() != 'nan':
            continue

        ticker = str(row[ticker_col]).strip()
        date_str = str(row[date_col]).strip()

        # Calculate the next date because yfinance end dates are exclusive
        try:
            current_date = pd.to_datetime(date_str)
            next_date_str = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"[{index}] Invalid date format '{date_str}'. Skipping...")
            df.at[index, 'price'] = np.nan
            df.to_csv(FILE_PATH, index=False)
            continue

        print(f"[{index}] Fetching High price for {ticker} on {date_str}...", end=" ")

        success = False
        
        # 5. Retry logic (up to 3 times)
        for attempt in range(3):
            try:
                # Fetch data for the specific day
                stock = yf.Ticker(ticker)
                hist = stock.history(start=date_str, end=next_date_str)

                if not hist.empty and 'High' in hist.columns:
                    # Extract the Daily High
                    high_price = hist['High'].iloc[0]
                    df.at[index, 'price'] = round(float(high_price), 4)
                    print(f"Success: {high_price}")
                else:
                    # No data available for this day (weekend, holiday, invalid ticker, etc.)
                    df.at[index, 'price'] = np.nan
                    print("No data (Weekend/Holiday?) -> NaN")
                
                success = True
                
                # Respect rate limits after a successful API call
                time.sleep(SLEEP_TIME)
                break  # Exit the retry loop

            except Exception as e:
                print(f"\n   Attempt {attempt + 1} failed: {e}", end=" ")
                time.sleep(SLEEP_TIME)  # Respect rate limit even on errors to avoid being blocked
                
        # 6. If it failed 3 times, mark as NaN
        if not success:
            print("Failed 3 times -> NaN")
            df.at[index, 'price'] = np.nan

        # 7. Write to CSV dynamically (updates cache after every row)
        df.to_csv(FILE_PATH, index=False)

    print("\nScraping complete!")

if __name__ == "__main__":
    main()