import json
import os
import time
from pathlib import Path

from google import genai


ROOT = Path(__file__).resolve().parent
SAMPLE_FILE = ROOT / "extraction_test_random_sample.txt"
PDF_DIRECTORY = ROOT / "data" / "pdf" / "digital_ptr"
OUTPUT_DIRECTORY = ROOT / "data" / "json"

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
OVERWRITE_EXISTING = False
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 10


PROMPT = """
Your task is to parse a Congressional Periodic Transaction Report (PTR) PDF
and convert every transaction row into strict JSON.

### Instructions

1. Extract every individual transaction row from the attached PDF.
2. Preserve every transaction. Do not combine separate transactions.
3. Handle multi-line tables, unusual formatting, scanned text, and messy OCR.
4. Use the visual table layout when it helps identify the correct field.
5. If a value is missing or unreadable, use an empty string rather than guessing.
6. If a custom description or note is provided by the filer, capture it entirely
   in the "desc" field.
7. Return only valid JSON matching the schema below.
8. Do not wrap the response in Markdown code fences.

### JSON schema

{
  "transactions": [
    {
      "own": "Owner code, such as SP or DC, or an empty string",
      "ast": "Full asset or security name, including ticker when available",
      "code": "Asset type abbreviation from brackets, such as ST or GS",
      "typ": "Transaction type, such as P, S, or S (partial)",
      "dt": "Transaction date in MM/DD/YYYY format",
      "ndt": "Notification date in MM/DD/YYYY format",
      "amt": "Dollar amount range exactly as shown",
      "cg": "Boolean: true if Capital Gains > $200 is checked, otherwise false",
      "stat": "Filing status, such as New",
      "sub": "Subholding account name or number",
      "desc": "Optional filer-provided description or note"
    }
  ]
}
"""


# Put any one-off instructions for this run in this long string.
ADDITIONAL_PROMPT = """
Pay special attention to transaction rows that continue across page breaks.
Use the exact dollar range shown in the report. Do not infer a value from
the asset name or transaction type.
"""


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "own": {"type": "string"},
                    "ast": {"type": "string"},
                    "code": {"type": "string"},
                    "typ": {"type": "string"},
                    "dt": {"type": "string"},
                    "ndt": {"type": "string"},
                    "amt": {"type": "string"},
                    "cg": {"type": "boolean"},
                    "stat": {"type": "string"},
                    "sub": {"type": "string"},
                    "desc": {"type": "string"},
                },
                "required": [
                    "own",
                    "ast",
                    "code",
                    "typ",
                    "dt",
                    "ndt",
                    "amt",
                    "cg",
                    "stat",
                    "sub",
                    "desc",
                ],
            },
        }
    },
    "required": ["transactions"],
}


def read_document_ids() -> list[str]:
    return [
        line.strip()
        for line in SAMPLE_FILE.read_text().splitlines()
        if line.strip()
    ]


def process_document(client: genai.Client, document_id: str) -> None:
    pdf_path = PDF_DIRECTORY / f"{document_id}.pdf"
    output_path = OUTPUT_DIRECTORY / f"{document_id}.json"

    if not pdf_path.exists():
        print(f"[missing PDF] {pdf_path}")
        return

    if output_path.exists() and not OVERWRITE_EXISTING:
        print(f"[skipped existing] {output_path}")
        return

    uploaded_file = client.files.upload(
        file=pdf_path,
        config={"mime_type": "application/pdf"},
    )

    response = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "document",
                "uri": uploaded_file.uri,
                "mime_type": uploaded_file.mime_type,
            },
            {
                "type": "text",
                "text": PROMPT + "\n\nAdditional instructions:\n" + ADDITIONAL_PROMPT,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RESPONSE_SCHEMA,
        },
    )

    parsed_output = json.loads(response.output_text)

    output_path.write_text(
        json.dumps(parsed_output, indent=2, ensure_ascii=False) + "\n"
    )

    print(f"[saved] {output_path}")


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GEMINI_API_KEY")
    print(api_key)
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY before running this script.")

    client = genai.Client(api_key=api_key)
    document_ids = read_document_ids()

    print(f"Processing {len(document_ids)} document IDs with {MODEL}")

    for document_id in document_ids:
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                process_document(client, document_id)
                break
            except Exception as error:
                print(
                    f"[error] {document_id}, attempt "
                    f"{attempt}/{RETRY_COUNT}: {error}"
                )

                if attempt == RETRY_COUNT:
                    print(f"[failed permanently] {document_id}")
                else:
                    time.sleep(RETRY_DELAY_SECONDS)


if __name__ == "__main__":
    main()