# Congress's stock trades journal

## Glossary
- `PTR`: Periodic Transaction Report, the primary document this project will be parsing and working with. They are 


## Suspicious Findings:
### Hand delivered, scanned PTR subset
There is a subset of 56 representitves that have hand delivered, and occasionally even hand written, their PTR reports. These reports are way harder to parse than the typical digital PTR. They are scanneed to be digitized, but it is exceptionally low resolution
 - See [TX-10 Representitve Michael T. McCau!'s (the autoparser thought the 'l' was a '!', ironic) hand delivered PTR](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2023/8220078.pdf)
    - This selection was completely randomly, but if you look at this [representitive's wikipedia page](https://en.wikipedia.org/wiki/Michael_McCaul#TikTok), he is not seeking re-election in 2026 due to allegations of, who would have guessed, insider trading.
### Duplicate Values
There are 5 duplicate values in the directory. I kept them because I'm not sure what to do with them.


# How this whole thing is going to work
### All digital PTR records:
We get the inital filing date from the XML/CSV, rather than trying to read it from the PDF
Extract all tables using pdf plumber
#### Cleaning pdf plumber rows:
- FOrmatting is inconsistence across rows, so just combine entire rows into a single string
- Headers look like
` [['ID', 'Owner', 'Asset', 'Transaction\nType', 'Date', 'Notification\nDate', 'Amount', 'Cap.\nGains >\n$200?'],`
- Get rid of rows full of blanks and Nones
- Look just for the rows with [ST], denoting a common stock purchase
- All within parenthese can be the full name of a stock/financial investment
    - (?<=\()[^)]+(?=\))
- All text within parentheses is a stock ticker
- Look for standalone "P" or "S" or "E" (purchase sale exchange)
- Investment names that are multiple lines long are quite elusive
    - They might even be able to go across pages
    - Sometimes they format to the end of the line, sometimes they format with a \n right after
- Text within brackets is an abbreivation of the asset type codes
- Finding dollar binning:
    - Look for the numbers (and commas within) after dollar signs
- Dates:
    - All Dates are MM/DD/YYYY
    - Easy to read those, there should be two dates that can be the same, take both of them, make the earlier one "date of purchase" and the later one "date of notification"
#### Nevermind, no matter what the data is too jumbled because politicians are sleezy
NEW PLAN: Give an LLM the data and call it a day
We are going to use Gemini Flash Lite 3.5 to check all PTR reports. It has PDF capabilities, and once I am sure that it 
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