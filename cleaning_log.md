# Cleaning Log
## Creating the dataset
- 9/1/26: Downloaded the 2023FD, 2024FD, and 2025FD.xml files.
- 9/1/26: Agreggated the three XML's list above into a single XML. All entries are dated, so nothing was lost (`2023-2025-combined.xml`)
- 9/1/26 Imported `2023-2025-combined.xml` into Excel to format it better (`PTR Excel Sheet.xlsx`). Filtered out non-PTR rows(we only care about PTR documents)
- 9/1/26 Created `all_digital_ptr.csv` using Excel. It includes every entry from the `2023-2025-combined.xml` that is a PTR document with a document ID above 20,000,000. It was noted that the PTR documents with docuemnt ID's above 20,000,000 were digital PDF files, which can be processed differently than the handwritten PTRs.
- 9/1/26 Created `handwritten_ptr.csv` using Excel. It includes every entry from the `2023-2025-combined.xml` that is a PTR document with a document ID below 10,000,000. It was noted that the PTR documents with docuemnt ID's below 10,000,000 were handwitten, scanned PDF files, which will have to be specially processed.
- 9/25/26: Created `extraction_test_random_sample`, which is just a list of 100 random PTR docIDs that I will use for testing
