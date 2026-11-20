# Data motivation
My initial question from P1 was:

> How do stocks trend in the grace period between when a member of congress originally purchases a stock, and when they are legally required to report their stock trade?

My wording has changed slightly since then, but the core principle driving what I was trying to analyze stayed the same. Early on as I got the data, I noticed that there was another interesting metric to differentiate congress members reporting their stocks: whether or not they were submitting it using the easily parsable digital format, or the very difficult printed, scanned, and sometimes handwritten paper version(denoted in the data as "handwritten" reports, even though many of them were still printed).

In end, my original statement was really fishing for a 'smoking gun' of insider trading somewhere in the data, but finding how some of congress was attempting to conceal their transactions by publishing an unreadable format, and how the few transactions I did manage to parse were significantly different, and much more successful than the rest of the dataset was really the data I found most interesting in the end.
# Sources, provenance & terms

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
# **Data dictionary & metadata**

## A. Filing & Congressmember Metadata

| Field         | What goes in it                                                                                                                                                                                                                                                                                                                                                                                     |
| :------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `file_name`                                                                                                                                                                                                                                                                                                                                                                                         |
| Type          | String (`str`)                                                                                                                                                                                                                                                                                                                                                                                      |
| Valid range   | Format `{DocID}.json` (12–13 characters; 743 unique files in `culled_df`).<br>• **In `parsed_df` (29,936 rows):** Handwritten DocIDs range `8219339`–`9115689` (16,870 rows); Digital DocIDs range `20000788`–`20033700` (13,066 rows).<br><br>• **In `culled_df` (9,214 rows):** Handwritten DocIDs range `8219826`–`8221212` (324 rows); Digital DocIDs range `20000807`–`20033691` (8,890 rows). |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                                                                                                                                                                                                                                 |
| Notes         | Source JSON filename for each transaction. Its numeric stem (`DocID`) serves as the Many-to-One join key against the House Clerk XML directory (`*FD.xml`) to attach `last`, `first`, `StateDst`, and `pdt`, and to classify `handwritten`.                                                                                                                                                         |

| Field         | What goes in it                                                                                                                                                                                                                                                                     |
| :------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `handwritten`                                                                                                                                                                                                                                                                       |
| Type          | Boolean (`bool`)                                                                                                                                                                                                                                                                    |
| Factor levels | `False` (Digital PTR), `True` (Handwritten PTR)                                                                                                                                                                                                                                     |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                                                                                                                 |
| Notes         | Derived flag (`DocID < 20,000,000`). In `parsed_df`, 56.35% (`16,870`) of rows came from 193 handwritten PTRs and 43.65% (`13,066`) came from 1,229 digital PTRs. <br><br>After culling, only **3.52% (`324`)** of remaining rows are handwritten vs. **96.48% (`8,890`)** digital. |

| Field         | What goes in it                                                                                                                                                                                               |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Variable name | `last`, `first`, `StateDST`                                                                                                                                                                                   |
| Type          | String (`str`)                                                                                                                                                                                                |
| Valid range   | Names of congressmembers, and their district code.                                                                                                                                                            |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df` (enforced by assertion).                                                                                                                                   |
| Notes         | Last name, first name, and State/District code of the filing House member, joined from the House Clerk XML directory.<br><br>First names occasionally contained a middle name as well (E.g `Marjorie Taylor`) |

| Field         | What goes in it                                                                                                                                                                                                                                                                                                                        |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `pdt` (Publication / Filing Date)                                                                                                                                                                                                                                                                                                      |
| Type          | Date (`datetime64[us]`)                                                                                                                                                                                                                                                                                                                |
| Units         | Date (day resolution)                                                                                                                                                                                                                                                                                                                  |
| Valid range   | Observed in `culled_df`: `2023-01-01` to `2025-12-29` (497 unique dates).                                                                                                                                                                                                                                                              |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                                                                                                                                                                    |
| Notes         | Date the Periodic Transaction Report (PTR) was filed/published, joined from `FilingDate` in the House Clerk XML directory. Rows where <br><br>There were some anomalies where `pdt` and `dt` would 100+ days apart, and these were thrown out as they were likely a part of a mislabelled other kind of financial disclosure document. |

---
## B. Transaction & Asset Identifiers

| Field         | What goes in it                                                                                                                                                                          |
| :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `ast` (Asset)                                                                                                                                                                            |
| Type          | String (`str`)                                                                                                                                                                           |
| Valid range   | 2,396 unique asset strings in `culled_df` (12–113 characters).                                                                                                                           |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                      |
| Notes         | Raw asset name reported on the PTR (typically company/fund name followed by parenthetical ticker, e.g., `NVIDIA Corporation - Common Stock (NVDA)`). Used to extract `ticker` via regex. |

| Field         | What goes in it                                                                                                                                                                                               |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Variable name | `ticker`                                                                                                                                                                                                      |
| Type          | String (`str`)                                                                                                                                                                                                |
| Valid range   | 1,319 unique ticker symbols in `culled_df` (1–5 characters, extracted via regex `\((.*?)\)` from `ast` with strings > 5 chars set to `None`).                                                                 |
| Missingness   | **In `parsed_df`:** 46.42% (`13,897` rows) missing (`None`).<br>**In `culled_df`:** 0.00% (0 rows) missing (required during culling).                                                                         |
| Notes         | Stock/ETF ticker symbol used to query historical daily highs via `yfinance`. Note: delisted tickers (e.g., `ATVI`) may still appear in `culled_df` if at least 2 of the 5 reference dates had price coverage. |

| Field         | What goes in it                                                                                                                                                        |
| :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `desc` (Description)                                                                                                                                                   |
| Type          | String (`str`)                                                                                                                                                         |
| Valid range   | 281 unique text strings in `culled_df` (0–603 characters).                                                                                                             |
| Missingness   | 0.00% `NaN` in `parsed_df` and `culled_df`; **81.89% (`7,545` rows)** are empty string `""` in `culled_df`.                                                            |
| Notes         | Optional free-text remarks entered by the filer. Most of the time, nothing, sometimes a whole paragraph that was repeated for every single transaction in a document.  |

| Field         | What goes in it                                                                             |
| :------------ | :------------------------------------------------------------------------------------------ |
| Variable name | `stat` (Filing Status)                                                                      |
| Type          | Category (`str`)                                                                            |
| Factor levels | Raw levels: `New`, `Amended`, `Deleted`.<br>In `culled_df` (1 value): `New` (`9,214` rows). |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                         |
| Notes         | Transaction filing status. `culled_df` filters exclusively to `stat == "New"`.              |

| Field         | What goes in it                                                                                                                                                                                                                                                        |
| :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `typ` (Transaction Type)                                                                                                                                                                                                                                               |
| Type          | Category (`str`)                                                                                                                                                                                                                                                       |
| Factor levels | Observed in `culled_df` (5 values): `P` (4,310), `S` (3,083), `S (partial)` (1,801), `E` (19), `S.` (1).                                                                                                                                                               |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                                                                                                    |
| Notes         | Denotes Purchase (`P`), Sale (`S`, `S (partial)`, plus 1 OCR/parsing typo `S.`), or Exchange (`E`). <br><br>Downstream buy/sell analysis groups rows via `.str.startswith("P")` and `.str.startswith("S")`, which captures `S (partial)` and `S.` while excluding `E`. |

| Field         | What goes in it                                                                                             |
| :------------ | :---------------------------------------------------------------------------------------------------------- |
| Variable name | `cg` (Capital Gains > $200)                                                                                 |
| Type          | Boolean (`bool`)                                                                                            |
| Factor levels | `False` (7,724 rows / 83.83%), `True` (1,490 rows / 16.17%) in `culled_df`.                                 |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                         |
| Notes         | Indicates whether the transaction resulted in capital gains exceeding $200. Not used in any of my analysis. |

---
## C. Transaction Dates & Dollar Amounts

### `dt` and `ndt`
| Field         | What goes in it                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Variable name | `dt` (Transaction Date) and `ndt` (Notification Date)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Type          | Date (`datetime64[us]`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Units         | Date (day resolution)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Valid range   | Enforced study bounds: `2022-11-14` to `2026-01-01`.<br>Observed in `culled_df`:<br>• `dt`: `2022-11-22` to `2025-12-16` (715 unique dates)<br>• `ndt`: `2022-12-02` to `2025-12-24` (594 unique dates)                                                                                                                                                                                                                                                                                                                                                                   |
| Missingness   | **In `parsed_df` (after coercion & bounds check):**<br>• `dt`: **39.18% (`11,730`)** `NaT`<br>          - 0.17% (`51`) raw empty/null, <br>		  - **37.77% (`11,307`)** failed `MM/DD/YYYY` parsing (mostly handwritten)<br>		  - 1.24% (`372`) out-of-range.<br>• `ndt`: **33.30% (`9,970`)** `NaT`<br>            - 0.18% (`54`) raw empty/null<br>			- **31.74% (`9,503`)** failed `MM/DD/YYYY` parse (mostly handwritten)<br>			- 1.38% (`413`) out-of-range.<br>**In `culled_df`:** **0.00% (0 rows)** missing for both `dt` and `ndt` (rows with `NaT` were culled). |
| Notes         | `dt` is the reported trade date; `ndt` is the date the member was notified of the trade. In-range user typos or LLM hallucinations within `2022-11-14`–`2026-01-01` cannot be automatically detected beyond the `\|pdt - dt\| <= 90` day check.                                                                                                                                                                                                                                                                                                                           |

| Field         | What goes in it                                                                                                                                                                                                                                                                                  |
| :------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `amt` (Raw Amount)                                                                                                                                                                                                                                                                               |
| Type          | String (`str`)                                                                                                                                                                                                                                                                                   |
| Valid range   | 34 unique string formats in `culled_df`: standard House bins (`$1,001 - $15,000` through `$5,000,001 - $25,000,000`), spacing variants (e.g., `$1,001-$15,000`, `$1,000-$15,000`), `Over $1,000,000` (2 rows), and 18 exact dollar amounts (`$1.00` to `$2,000.00`) extracted by the LLM parser. |
| Missingness   | 0.00% (0 rows) in both `parsed_df` and `culled_df`.                                                                                                                                                                                                                                              |
| Notes         | Raw dollar amount or range string from the parsed PTR. Cleaned and converted into `amt_int` at the end of the notebook.                                                                                                                                                                          |

| Field | What goes in it |
| :--- | :--- |
| Variable name | `amt_int` (Canonicalized Minimum Dollar Amount) |
| Type | Nullable Integer (`Int64`) |
| Units | US Dollars ($) |
| Valid range | `1` to `5,000,001` (29 unique values; p25 = `$1,001`, median = `$1,001`, p75 = `$1,001`, mean = `$13,363.29`). |
| Missingness | 0.00% (0 rows) in `culled_df` (verified via assertion). |
| Notes | Created by `canonicalize_amt(culled_df["amt"])`. Extracts the leading dollar amount (lower bound for binned ranges, rounded to nearest integer USD, or exact dollar amount when provided). Note: `Over $1,000,000` maps to `1,000,000` (the `+1` adjustment is commented out in code). |

---
## D. Joined Market Price Data (`yfinance` Daily Highs)

> *Note on culling:* After joining cached prices from `scrape_dates_prices.csv` (33,803 requested pairs; 36,283 cached rows with 33,677 non-null & 2,606 `NaN` prices), rows with fewer than 2 non-null values across the 5 `high_*` columns were dropped (reducing 9,853 rows to **9,214**). This is since there is no comparison we could possibly make for them, since they only have one value.

| Field         | What goes in it                                                                                                                                                                                                                                                                                                       |
| :------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `high_dt`, `high_ndt`, `high_pdt`, `high_dt_plus_45`, `high_today`                                                                                                                                                                                                                                                    |
| Type          | Float (`float64`)                                                                                                                                                                                                                                                                                                     |
| Units         | US Dollars ($) — daily stock high                                                                                                                                                                                                                                                                                     |
| Valid range   | Positive dollar amounts                                                                                                                                                                                                                                                                                               |
| Missingness   | `high_dt`: **0.26% (24 rows)** `NaN` in `culled_df`.<br>`high_ndt`: **0.21% (19 rows)** `NaN` in `culled_df`.<br>`high_pdt`: **0.28% (26 rows)** `NaN` in `culled_df`.<br>`high_dt_plus_45`: **0.36% (33 rows)** `NaN` in `culled_df`.<br>`high_today`: **0.63% (58 rows)** `NaN` in `culled_df` (typically delisted) |
| Notes         | "today" is set as October 20th, 2026                                                                                                                                                                                                                                                                                  |

---
## E. Derived Analysis Metrics (`transactions` & `hist_df`)

| Field         | What goes in it                                                                                                                                          |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `change_pct` (in `transactions`)                                                                                                                         |
| Type          | Float (`float64`)                                                                                                                                        |
| Units         | Percentage (`%`)                                                                                                                                         |
| Valid range   | Observed (unfiltered): `-160.40%` to `87.00%` (median = `0.48%`, mean = `0.89%`). Note: values below `-100%` stem from the 1 negative `high_dt` anomaly. |
| Missingness   | **0.48% (44 rows)** `NaN` across `9,214` rows (where `high_dt` or `high_pdt` is missing).                                                                |
| Notes         | Percent price change from transaction date to PTR publication date: `((high_pdt - high_dt) / high_dt) * 100`.                                            |

| Field         | What goes in it                                                                                                                                                                                                                                                        |
| :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variable name | `luck_score_pct` (in `buys`, `sells`, and `hist_df`, `n = 9,150`)<br><br>Percent change of the stock in the *favorable* direction                                                                                                                                      |
| Type          | Float (`float64`)                                                                                                                                                                                                                                                      |
| Units         | Percentage (`%`)                                                                                                                                                                                                                                                       |
| Valid range   | Observed: `-87.00%` to `70.79%` (median = `-0.22%`, mean = `-0.45%`).                                                                                                                                                                                                  |
| Missingness   | 0%                                                                                                                                                                                                                                                                     |
| Notes         | Directional favorable price move between `dt` and `pdt`: equal to `+change_pct` for buys (`typ` starting with `P`) and `-change_pct` for sales (`typ` starting with `S`). Positive values indicate the stock moved favorably after the trade before public disclosure. |

# Data cleaning steps narrative

1. 1426 PDF Files where downloaded from the Office of the Clerk, found through the directories
	1. 1231 Digital PTR Documents
	2. 195  Handwritten PTR Documents
2. 1229 digital and 193 handwritten documents were successfully parsed by the LLM script, and output the 1422 JSON files that make up the dataset
3. The 1422 JSON Files were then loaded into pandas to make 29,936 transaction rows (13066 from digital, 16870 from handwritten)
4. Found the associated stock ticker for each transaction from the text within parentheses in the asset name
	1. Deleted 233 rows that had a ticker longer than 5 characters, since stock tickers can't be longer than that
5. Removed anything caused by LLM hallucination
	1. Dates that were unparsable (11,307 Purchase dates, 9,503 notification dates)
	2. Dates that were outside of the feasible range of any transaction (373 Purchase dates, 413 notification dates)
6. Removed any rows that were not analyzable (missing either date, not `Status == "new"`, no ticker) (18,350)
7. Removed duplicate rows (Caused by a transaction crossing a page)
8. Joined the JSON transaction data *back* with the document metadata by matching the JSON's file name to the docId in the Clerk directories.
	1. This gave us `pdt` , `first`, `last`, `stateDst`
	2. Removed more rows with dating timelines (the purchase date was months before the publication date. removed a few obvious outliers caused by mislabelled documents)
9. Used the dataframe to create a list of stock ticker daily highs to cache using Yahoo Finance
	1. Making the list and removing duplicates was a **very** smart decision, as it removed **15,462 duplicate stock ticker-date/daily high pairs** that would have been scraped more than once
10. Joined the data with the stock price data cache, giving us all of the stock prices relative to the key transaction dates. 
	1. Removed any row that had one or less values joined, since there is no comparison we could possibly make with only one or zero price values
11. Made calculated columns to see the percent change of the stock between `dt` and `pdt`, as well as the favorable percent change (if someone buys a stock, it is favorable for it to go up, if they sell, it is favorable for it to go down)
# Integration & verification

## Integration
### First Join (Congressmember metadata Join)

| Dimension                                 | Specification                                                                                                                                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Join key(s)**                           | `DocID` (derived from `file_name` in left table; matching `DocID` in right table)                                                                                                                    |
| **Grain of the left table (`parsed_df`)** | One row per reported financial transaction within a disclosure filing                                                                                                                                |
| **Grain of the right table (`lookup`)**   | One row per PTR document filing (`DocID` deduplicated with `.drop_duplicates("DocID")`)                                                                                                              |
| **Relationship**                          | **Many-to-One (`validate="many_to_one"`)**                                                                                                                                                           |
| **Expected row count after join**         | Exactly equal to the row count of `parsed_df` before the join (29,936 rows)                                                                                                                          |
| **Join type and why**                     | **Left join (`how="left"`)**: Every transaction row stays, even if the join doesn't find matching metadata.                                                                                          |
| **What happens to unmatched rows**        | Unmatched rows retain transaction features while filling member data (`last`, `first`, `StateDst`, `pdt`) with `NaN`. <br><br>The notebook later has asssertions to ensure that this never happened. |

### Second Join (Price Data Lookup)

| Dimension                             | Specification                                                                                                                                      |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Join key(s)**                       | Composite key: `[ticker, date]` (where date corresponds to `dt`, `ndt`, `pdt`, `dt_plus_45`, or `today`)                                           |
| **Grain of left table (`culled_df`)** | One row per validated stock transaction                                                                                                            |
| **Grain of right table (`prices`)**   | One row per unique `[ticker, date]` market observation                                                                                             |
| **Relationship**                      | Many-to-One lookup                                                                                                                                 |
| **Expected row count after join**     | Exactly equal to `len(culled_df)` before alignment (9,853 rows)                                                                                    |
| **Join type and why**                 | Left positional lookup (`reindex` over a MultiIndex) to align market quotes onto transactions without mutating table structure or reordering rows. |
| **What happens to unmatched rows**    | Returns `NaN` (e.g., delisted stocks or tickers missing historical coverage).                                                                      |
## Verification
Most of the verification had to do with ensuring there was no duplicates, fan-outs, out of bounds values, and that joins did not give a row a value that it needed(every row needed the personally identifying information of who made the trade). With the nature of this project, more of the code was dedicating to deleting data we knew was wrong, and less about asserting that the data we had was correct.
# Findings

The project found that across the whole population of transactions in congress, the results about followed a normal distribution, and while that does produce outliers, they don't appear in a strange quantity. Admittedly, I found nothing out of the ordinary, no 'smoking gun' of insider trading, that hasn't already been covered by some news article already. 

The finding I found much more interesting was the subset of handwritten PTR documents. While I am missing 97% of the handwritten transactions, the ones I did get had a very different buy-sell ratio (66% buys, compared to 48% buys), and performed significantly better than the general population (average favorable price change of +2.45% compared to -0.45%). I am confident that there is something to be uncovered if someone manages to find a way to consistently parse these nearly un-parsable documents, as at least some congress members who are submitting their transaction reports in this way are certainly doing it to conceal their trading history.
# What is missing
As previously mentioned, 97% of the transaction rows from the handwritten documents, which is more than half of all of the transactions in the initial data set, is missing from the final analysis. The exclusion of the rows that did get successfully parsed creates a significant survivorship bias, as it is reasonable to believe that the un-parsed transactions have very different patterns to the ones that were parsed. 

Another thing that my model of the transactions doesn't account for which would provide deeper insight is the idea of continuity of buying and sell. Every sold stock was bought at some point, and if we can find matching buy-sell dates of all the stocks, we could see truly how well congress's stock portfolios are long-term. My analysis was more focused on looking for short-term anomalies in stock prices when a congress member completed a transaction with that stock, and this idea would take much longer to implement.
# AI use log & reflection
AI was used on this a lot, and without it this wouldn't be possible. I used a structured repeated Google Gemini 3.5 Flash prompt with PDF context to parse all of the PDF files into readable JSONs, and I used Github Copilot to code just about everything. The trickiest part of making the program was getting everything to work in one cohesive manner, which is something I ignored for the whole project, since once I got the data I needed from something, why would I go back and fix the code? 

Up until recently, the project directory was full of "temporary" CSV, txt, and XML files that held the vibe-coded python scripts together like bandaids. After giving time to make the project work as one cohesive pipeline by actually reviewing some of the code myself, everything runs way smoother. There are no more inputs beyond what you download from the web, the python scripts log every action they take, and any issue that comes up becomes much easier to diagnose and fix. 

Vibe coding is extremely powerful, theres no doubt about that. But it is very easy to let it slip away into you allowing terrible code to propagate through your entire project, without just spending a little extra time to fix it. 

# Reproducibility
All of the instructions to reproduce this analysis, including with a different date range, can be found on [the readme.md](https://github.com/TheCarsonWest/DSA405/blob/master/README.md#how-to-run-the-project)). 
## [Link to the repo](https://github.com/TheCarsonWest/DSA405/tree/master)
