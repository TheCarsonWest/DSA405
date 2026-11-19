# Congressional Stock Trades Journal

**Repository:** https://github.com/TheCarsonWest/DSA405

**Author:** Carson West (`cjwest7`) · DSA 405 (Fall 2026)

## Overview & Key Findings

This project analyzes how stocks traded by members of the U.S. House of Representatives perform around the times those trades are executed and disclosed. Using **1,426 Periodic Transaction Reports (PTRs)** published between 2023 and 2025, PDF filings were parsed into structured JSON using Google Gemini (`3.5 Flash Lite`, with `3.8 Flash Preview` attempted on oversized filings), joined with U.S. House Clerk filing metadata, and matched against historical daily high stock prices retrieved via `yfinance` (including `dt`, `ndt`, `pdt`, `dt + 45 days`, and a recent reference date of`2026-10-20`).

**For my analysis timeframe (2023-2025)**
Across the **9,214** transactions that survived cleaning (out of **29,936** raw extracted rows from **1,422** successfully parsed documents), congressional trades overall showed typical-to-slightly-negative short-term performance between the transaction date and publication date, with an **average favorable price change of -0.48%** (across 4,288 buys and 4,862 sells). However, the small subset of **handwritten/scanned PTR transactions** that survived parsing and cleaning (**324 rows**, ~2% of the 16,870 handwritten rows) had a noticeably higher **average favorable price change of +2.45%**.

Because over two-thirds of all raw rows—and ~98% of handwritten rows—were dropped due to missing/unparseable fields or missing ticker/price data, the results are subject to substantial **survivorship bias**, and easily parsable filings may differ systematically from those that failed to parse.

---
## Data Sources & Licenses

1. **U.S. House of Representatives, Office of the Clerk — Financial Disclosure Reports (PTRs & Directory Metadata)**
   - **Description:** 1,426 Periodic Transaction Report PDFs published between 2023 and 2025 and the accompanying Clerk PTR filing directory (`combined_ptr.csv`).
   - **Link:** [Office of the Clerk Financial Disclosures](https://disclosures-clerk.house.gov/FinancialDisclosure) (Contains a list of annual document directories)
   - **License / Terms:** Public Domain

2. **Yahoo Finance (via `yfinance`) — Historical Stock Market Pricing**
   - **Description:** Historical daily high prices queried for `36,283` unique `(ticker, date)` pairs across `1,569` unique tickers (`33,677` valid daily highs returned; `2,606` missing, e.g., delisted tickers such as `ATVI`).
   - **Links:** [Yahoo Finance](https://finance.yahoo.com/) [yfinance's PyPi website](https://pypi.org/project/yfinance/)
   - **License / Terms:**
	   - [yfiannce's Apache Software License](https://github.com/ranaroussi/yfinance/blob/main/LICENSE.txt)
	   - [Yahoo Developer API Terms of Use](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html)
	   - [Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
	   - [Yahoo Terms](https://policies.yahoo.com/us/en/yahoo/terms/index.htm)

---

## Repository Structure

```text
DSA405/
├── README.md
├── requirements.txt
├── download_pdfs.py                 # Download PTR PDFs from Office of the Clerk
├── ptr_pdf_to_json.py               # Parse PTR PDFs with Google Gemini
├── yfiannce_cache.py                # Fetch and cache historical stock prices
├── assignment-jupyter/
│   ├── DSA405_002_FA26_P2_cjwest7.ipynb
│   ├── DSA405_002_FA26_P3_cjwest7.ipynb    # Pipeline to assemble the final dataframe
│   └── DSA405_002_FA26_P4_cjwest7.ipynb
└── data/                             # Committed datasets used by the project
    ├── clerk_directories/
    │   ├── 2023FD.xml
    │   ├── 2024FD.xml
    │   └── 2025FD.xml
    ├── pdf/                          # Optional downloaded PTR PDFs, ignored by Git
    ├── json/                         # 1,422 committed, LLM-parsed PTR JSON files
    ├── scrape_dates.csv                   # Deduplicated (ticker, date) pairs to query
    └── scrape_dates_prices.csv            # Cached daily high prices from yfinance
```

---

## How to Run the Project

### 1. Environment Setup

The project environment uses Python 3.15.1. From the repository root:

```bash
python3.15 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The existing `.venv` can be activated directly on macOS with:

```bash
source .venv/bin/activate
```

### 2. Run the Existing 2023-2025 Analysis

The repository already includes the 1,422 parsed PTR JSON files and
`data/scrape_dates_prices.csv`, so no PDF parsing or market-price download is
required for the existing analysis.

Open [P3](./assignment-jupyter/DSA405_002_FA26_P3_cjwest7.ipynb) in VS Code or
Jupyter and choose **Run All**. Jupyter kernels can use the project interpreter
at `.venv/bin/python`.
## How to Run the Project
### 3. Regenerate Data (Optional)

#### Download PTR PDFs

The Clerk XML directories are already in `data/clerk_directories/`:

```bash
python download_pdfs.py
```

Use `python download_pdfs.py --overwrite` to replace existing PDFs.

#### Parse PDFs with Gemini

Set a Gemini API key, then pass one or more PDF directories to the parser:

```bash
export GEMINI_API_KEY="your-api-key"
python ptr_pdf_to_json.py data/pdf/digital_ptr data/pdf/handwritten_ptr
```

The default model is `gemini-3.5-flash-lite`. Use `--retry-failed` to retry
entries in `data/failed_pdfs.csv`, or `--max-documents N` to limit a run.
Generated JSON files are written under `data/json/`.

#### Scrape and cache historical prices

`yfiannce_cache.py` reads `data/scrape_dates.csv` and writes
`data/scrape_dates_prices.csv`:

```bash
python yfiannce_cache.py
```

Add `--retry-failed` to retry ticker/date pairs cached as `NaN`. The project
cache generated for this analysis contains 36,283 requested pairs and took
about 18 hours to build. The script waits one second between requests.

To analyze additional years, edit `ANALYSIS_YEARS` in P3, run the notebook
cells through the cache setup, generate `scrape_dates.csv`, run the cache
script, and then continue through the rest of P3.

---

## Data Cleaning Log (Final State)

| #      | Target Column / Scope          | Change Made                                                                                                     | Rows / Cells Affected                                         | Why                                                                                                   | What is Lost                                                                         |
| :----- | :----------------------------- | :-------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| **1**  | `ticker`                       | Replaced ticker strings longer than 5 characters with `None`                                                    | **233 cells** `[MISSING: verify—P3.py comment says 128 rows]` | Tickers cannot be longer than 5 characters                                                            | False-positive ticker strings misidentified during regex extraction.                 |
| **2**  | `dt`                           | Coerced raw text strings into `datetime64[ns]` with `errors="coerce"`                                           | **11,307 cells**                                              | Converts text dates (`MM/DD/YYYY`) into timestamps for ordering, range checks, and joins.             | 11,307 unparseable entries (mostly handwritten/empty/corrupted fields) set to `NaT`. |
| **3**  | `ndt`                          | Coerced raw text strings into `datetime64[ns]` with `errors="coerce"`                                           | **9,503 cells**                                               | Converts notification date text into standardized timestamps.                                         | 9,503 malformed strings or empty values set to `NaT`.                                |
| **4**  | `dt`                           | Replaced dates outside study bounds (`< 2022-11-14` or `> 2026-01-01`) with `NaT`                               | **372 cells**                                                 | Eliminates impossible dates, OCR digit flips, and LLM hallucinations.                                 | 372 invalid date values reset to `NaT`.                                              |
| **5**  | `ndt`                          | Replaced notification dates outside study bounds with `NaT`                                                     | **413 cells**                                                 | Eliminates impossible notification dates and future dates contradicting the filing timeline.          | 413 invalid notification date values reset to `NaT`.                                 |
| **6**  | Lookup table (`DocID`)         | Deduplicated lookup table on `DocID` prior to metadata merge                                                    | **0 rows** *(already unique)*                                 | Guarantees strict Many-to-One cardinality (`validate="many_to_one"`) and prevents fanout duplication. | None (all 1,422 parsed PTR documents were uniquely indexed).                         |
| **7**  | Full DataFrame                 | Filtered out rows missing required trade metadata (`ticker.notna() & stat == 'New' & dt.notna() & ndt.notna()`) | **18,560 rows dropped** *(leaving 11,376)*                    | Transactions lacking tickers, dates, or `New` status cannot be analyzed meaningfully.                 | 18,560 unanalyzable rows.                                                            |
| **8**  | Full DataFrame                 | Dropped identical intra-document duplicate transactions (`file_name`, `ast`, `dt`, `ndt`, `amt`)                | **710 rows dropped** *(leaving 10,666)*                       | Parsers frequently extract redundant line items when tables span page breaks.                         | 710 redundant duplicate transaction records within filings.                          |
| **9**  | Full DataFrame (`pdt` vs `dt`) | Filtered out rows where disclosure publication gap exceeded 90 days (`\|pdt - dt\| > 90`)                       | **813 rows dropped** *(leaving 9,853)*                        | PTRs are mandated within 30–45 days; gaps > 90 days indicate mislabeled annual disclosures.           | 813 non-periodic or misclassified disclosure rows.                                   |
| **10** | Market Prices (`high_*`)       | Dropped rows with fewer than 2 valid market price observations across reference dates                           | **639 rows dropped** *(leaving 9,214)*                        | Measuring trade performance requires at least two price observations to compare.                      | 639 transactions with fewer than 2 valid daily highs across the 5 reference dates.   |

---

## Glossary & Extraction Details

- **`PTR`:** Periodic Transaction Report. Inside of the Office of the Clerk disclosure directories, there are many different types of documents, the only ones we are concerned with are these ones, denoted with the XML tag `<FilingType>P</FilingType>`
- **`dt` / `ndt` / `pdt`:** Transaction date / Notification date (self-reported date the representative says they were notified of the trade) / Publication date of the PTR document.


## LLM PDF-to-JSON Extraction Prompt & Notes
```text
Your task is to parse a raw OCR text dump or table from a Congressional Periodic Transaction Report (PTR) and convert every transaction row into a strict JSON format.

### Instructions:
1. Extract every individual transaction row into the schema provided below.
2. Handle jumbled, multi-line, or messy OCR text gracefully by mapping parts of the entry to their correct logical fields.
3. If a custom or long description/note is provided by the filer to explain or obfuscate a transaction/account, capture it entirely in the optional "desc" field. If no extra description exists, leave it as an empty string ("").
4. Output ONLY valid JSON matching the schema. No markdown wrapping outside the JSON block if possible, or standard markdown json code blocks.

### JSON Schema Structure:
{
  "transactions": [
    {
      "own": "Owner code (e.g., SP, DC, or empty string)",
      "ast": "Full asset or security name and ticker",
      "code": "Asset type abbreviation from brackets (e.g., ST, GS)",
      "typ": "Transaction type (e.g., P, S, S (partial))",
      "dt": "Transaction date (MM/DD/YYYY)",
      "ndt": "Notification date (MM/DD/YYYY)",
      "amt": "Dollar amount range string",
      "cg": boolean (true if Capital Gains > $200 box is checked, else false),
      "stat": "Filing status (e.g., New)",
      "sub": "Subholding account name/number",
      "desc": "Optional extra text, notes, or descriptive text added by the filer"
    }
  ]
}
```

