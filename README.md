# Congress's stock trades journal

In this project we are analyzing the performance of stocks in and around the times that congressmembers purchase them. This involves scraping and parsing the PTR docuemnts from 2022-2025, and matching up each transaction described to the historical stock data from the dates purchase, dates notified, and dates the document was published.

## Glossary
- `PTR`: Periodic Transaction Report, the primary document this project will be parsing and working with. They are 


## Current Cleaning log

| #      | Target Column / Scope          | Change Made                                                                                                     | Rows / Cells Affected                          | Why                                                                                                                                                          | What is Lost                                                                                                  |
| :----- | :----------------------------- | :-------------------------------------------------------------------------------------------------------------- | :--------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **1**  | `ticker`                       | Replaced ticker strings longer than 5 characters with `None`                                                    | **233 cells**                                  | Tickers cannot be longer than 5 characters                                                                                                                   | 233 false-positive ticker strings misidentified during regex extraction.                                      |
| **2**  | `dt`                           | Coerced raw text strings into `datetime64[ns]` with `errors="coerce"`                                           | **11,307 cells**                               | Converts text dates (`MM/DD/YYYY`) into proper timestamps required for chronological ordering, range checks, and joins.                                      | 11,307 unparseable entries (mostly unparsed/handwritten lines, empty fields, or corrupted text) set to `NaT`. |
| **3**  | `ndt`                          | Coerced raw text strings into `datetime64[ns]` with `errors="coerce"`                                           | **9,503 cells**                                | Converts notification date text into standardized timestamps to measure reporting delays.                                                                    | 9,503 malformed strings or empty values set to `NaT`.                                                         |
| **4**  | `dt`                           | Replaced dates outside the study bounds (`< 2022-11-14` or `> 2026-01-01`) with `NaT`                           | **372 cells**                                  | Eliminates impossible dates, OCR digit flips (e.g., years in the 1900s or 2090s), and LLM hallucinations.                                                    | 372 invalid date values reset to `NaT`.                                                                       |
| **5**  | `ndt`                          | Replaced notification dates outside the study bounds with `NaT`                                                 | **413 cells**                                  | Eliminates impossible notification dates and future dates that contradict the filing timeline.                                                               | 413 invalid notification date values reset to `NaT`.                                                          |
| **6**  | Lookup table (`DocID`)         | Deduplicated lookup table on `DocID` prior to metadata merge                                                    | **0 rows** *(already unique)*                  | Guarantees a strict Many-to-One cardinality to satisfy `validate="many_to_one"` and prevent fanout duplication.                                              | None (all 1,422 PTR documents were uniquely indexed).                                                         |
| **7**  | Full DataFrame                 | Filtered out rows missing required trade metadata (`ticker.notna() & stat == 'New' & dt.notna() & ndt.notna()`) | **18,560 rows dropped** <br>*(leaving 11,376)* | Transactions lacking tickers, dates, or non-new status cannot be analyzed in a meaningful way                                                                | 18,560 unanalyzable rows.                                                                                     |
| **8**  | Full DataFrame                 | Dropped identical intra-document duplicate transactions (`file_name`, `ast`, `dt`, `ndt`, `amt`)                | **710 rows dropped** <br>*(leaving 10,666)*    | OCR and document parsers frequently extract redundant transaction line items when files span page breaks.                                                    | 710 redundant duplicate transaction records within filings.                                                   |
| **9**  | Full DataFrame (`pdt` vs `dt`) | Filtered out rows where disclosure publication gap exceeded 90 days (`\|pdt - dt\| > 90`)                       | **813 rows dropped** <br>*(leaving 9,853)*     | Periodic Transaction Reports are legally mandated within 30–45 days. Gaps > 90 days indicate mislabelled Annual Financial Disclosures rather than true PTRs. | 813 non-periodic or misclassified asset disclosure rows.                                                      |
| **10** | Market Prices (`high_*`)       | Dropped rows with fewer than 2 valid market price observations across reference dates                           | **639 rows dropped** <br>*(leaving 9,214)*     | We want to measure the performance of a trade, if we only have 1 date, then we have nothing to compare at all.                                               | 639 transactions that only one daily high could be found for the 5 different price dates                      |





## Suspicious Findings:
### Hand delivered, scanned PTR subset
There is a subset of 56 representitves that have hand delivered, and occasionally even hand written, their PTR reports. These reports are way harder to parse than the typical digital PTR. They are scanneed to be digitized, but it is exceptionally low resolution
 - See [TX-10 Representitve Michael T. McCau!'s (the autoparser thought the 'l' was a '!', ironic) hand delivered PTR](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2023/8220078.pdf)
    - This selection was completely randomly, but if you look at this [representitive's wikipedia page](https://en.wikipedia.org/wiki/Michael_McCaul#TikTok), he is not seeking re-election in 2026 due to allegations of, who would have guessed, insider trading.
### Duplicate Values
There are 5 duplicate values in the directory. I kept them because I'm not sure what to do with them.


#### Nevermind, no matter what the data is too jumbled because politicians are sleezy
NEW PLAN: Give an LLM the data and call it a day
We are going to use Gemini Flash Lite 3.5 to check all PTR reports. 
Prompt:
```
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

# Post PDF to JSON LLM transform:
- It took more than 3 days to get through all the files(which was expected), but I finally did. Almost no erors, except for TWO errors parsing the PTR reports of Congresswoman Lisa McClain of Michigan's 9th District. These two documents happen to be the largest and third largest PTR reports in the entire dataset. Document 20030891 is **81 pages long** and Document 20033446 is 53 pages long.
```
[error] 20030891, attempt 1/3: Unterminated string starting at: line 6136 column 7 (char 153910)
[error] 20030891, attempt 2/3: Unterminated string starting at: line 6136 column 7 (char 153910)
[error] 20030891, attempt 3/3: Unterminated string starting at: line 6136 column 7 (char 153910)
[failed permanently] 20030891
[skipped existing] /Users/carson/Desktop/DSA405/data/json/20030932.json
[skipped existing] /Users/carson/Desktop/DSA405/data/json/20032129.json
[error] 20033446, attempt 1/3: Unterminated string starting at: line 6063 column 14 (char 149822)
[error] 20033446, attempt 2/3: Expecting value: line 6063 column 13 (char 149821)
[error] 20033446, attempt 3/3: Unterminated string starting at: line 6063 column 14 (char 149822)
[failed permanently] 20033446
```
### Running the LLM and prompt manually with a bigger model
Ok, an 81 page pdf input is in fact a lot for 3.5 Flash Lite, in fact its 45,000 tokens of input between the prompt and the PTR. I ran this one specifically on 3.8 Flash Preview with a higher thinking level, hopefully it parses better.

---

#### Results
It thought for 5 minutes and used 65,000 tokens. It still couldnt get me a full answer. I am going to need to look back to see if the longer PTRs fully match.

## Downloading and parsing PTR documents

`data/clerk_directories/` contains the Office of the Clerk year-specific
`<Year>FD.xml` files used to discover PTR documents. Download PDFs from all XML
files in that directory, or from one XML file:

```sh
python download_pdfs.py
python download_pdfs.py --input data/clerk_directories/2024FD.xml
python download_pdfs.py --input /path/to/clerk/xml --overwrite
```

The downloader includes only members whose `<FilingType>` is `P`.

Documents with IDs below `20000000` are saved under
`data/pdf/handwritten_ptr/`; other IDs go under `data/pdf/digital_ptr/`.
Existing PDFs are skipped by default.

Parse PDFs from one or more directories, or from a text file containing one PDF
path per line. Relative paths in a path list are resolved relative to that list:

```sh
python ptr_pdf_to_json.py data/pdf/handwritten_ptr data/pdf/digital_ptr
python ptr_pdf_to_json.py --file-list data/all_json_paths.txt --max-documents 20
python ptr_pdf_to_json.py data/pdf/digital_ptr --overwrite
python ptr_pdf_to_json.py data/pdf/digital_ptr --retry-failed
```

Set `GEMINI_API_KEY` before parsing. JSON files are written to `data/json/`;
existing files and previously permanent failures are skipped by default.
`--overwrite` replaces existing JSON, `--retry-failed` retries entries from
`data/failed_pdfs.csv`, and `--max-documents` limits attempted documents for
that run. Per-input-directory cumulative parsing statistics are cached in
`data/json/.parse_stats/`. After at least five reference documents, a warning
is recorded when a PDF is at least 1.5 times the median PDF size but its JSON to
PDF size ratio is below one quarter of the historical median ratio.

Both scripts continue to report progress in the terminal and also append it to
their respective log files in `data/log/`.