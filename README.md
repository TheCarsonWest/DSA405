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
- All text before the first "(" can be the full name of a stock/financial investment
- All text within parentheses is a stock ticker
- Look for standalone "P" or "S" or "E" (purchase sale exchange)
- Investment names that are multiple lines long are quite elusive
    - They might even be able to go across pages
    - Sometimes they format to the end of the line, sometimes they format with a \n right after
- Text within brackets is an abbreivation of the asset type codes 