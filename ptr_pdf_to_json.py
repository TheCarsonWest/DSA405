import argparse
import csv
import hashlib
import json
import logging
import os
import statistics
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"
OUTPUT_DIRECTORY = DATA_DIRECTORY / "json"
STATS_DIRECTORY = OUTPUT_DIRECTORY / ".parse_stats"
FAILED_DOCUMENTS_PATH = DATA_DIRECTORY / "failed_pdfs.csv"
LOG_PATH = DATA_DIRECTORY / "log" / "ptr_pdf_to_json.log"

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
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
      "ast": "Full asset or security name, including ticker when available. If the company name is glaringly misspelled, use the correct spelling rather than the OCR text. If the company name is clearly that of a publicly traded company, include the ticker in parentheses after the name, e.g. 'Apple Inc. (AAPL)'. If the asset is a mutual fund, include the fund family and fund name, e.g. 'Vanguard 500 Index Fund'.",
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


def configure_logging() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger("ptr_pdf_to_json")


def collect_pdfs(
    directories: list[Path], file_list: Path | None, logger: logging.Logger
) -> list[tuple[Path, Path]]:
    discovered: dict[Path, Path] = {}
    for directory in directories:
        directory = directory.resolve()
        if not directory.is_dir():
            raise NotADirectoryError(f"PDF input is not a directory: {directory}")
        for pdf_path in sorted(directory.rglob("*")):
            if pdf_path.is_file() and pdf_path.suffix.lower() == ".pdf":
                discovered.setdefault(pdf_path.resolve(), directory)

    if file_list is not None:
        file_list = file_list.resolve()
        if not file_list.is_file():
            raise FileNotFoundError(f"PDF path list does not exist: {file_list}")
        for line_number, line in enumerate(
            file_list.read_text(encoding="utf-8").splitlines(), start=1
        ):
            entry = line.strip()
            if not entry:
                continue
            pdf_path = Path(entry)
            if not pdf_path.is_absolute():
                pdf_path = file_list.parent / pdf_path
            pdf_path = pdf_path.resolve()
            if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
                logger.error(
                    "Invalid PDF path at %s:%d: %s", file_list, line_number, pdf_path
                )
                raise ValueError(
                    f"Invalid PDF path at {file_list}:{line_number}: {pdf_path}"
                )
            discovered.setdefault(pdf_path, pdf_path.parent)
    return [(directory, pdf) for pdf, directory in sorted(discovered.items())]


def stats_path_for(directory: Path) -> Path:
    directory_key = str(directory.resolve())
    digest = hashlib.sha256(directory_key.encode("utf-8")).hexdigest()[:20]
    return STATS_DIRECTORY / f"{digest}.json"


def load_stats(directory: Path) -> dict:
    path = stats_path_for(directory)
    if not path.exists():
        return {
            "source_directory": str(directory.resolve()),
            "documents": {},
            "failed_documents": {},
            "permanent_failure_count": 0,
            "outliers": {},
        }
    stats = json.loads(path.read_text(encoding="utf-8"))
    if stats.get("source_directory") != str(directory.resolve()):
        raise ValueError(f"Statistics cache does not match input directory: {path}")
    stats.setdefault("documents", {})
    stats.setdefault("failed_documents", {})
    stats.setdefault(
        "permanent_failure_count", sum(stats["failed_documents"].values())
    )
    stats.setdefault("outliers", {})
    return stats


def write_json_atomically(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, indent=2, ensure_ascii=False)
            temporary_file.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_failed_documents() -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not FAILED_DOCUMENTS_PATH.exists():
        return records
    with FAILED_DOCUMENTS_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        expected_columns = [
            "file_path",
            "permently_failed_count",
            "has_suceeded",
        ]
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"{FAILED_DOCUMENTS_PATH} must have columns: "
                + ",".join(expected_columns)
            )
        for row in reader:
            records[row["file_path"]] = {
                "permently_failed_count": int(row["permently_failed_count"]),
                "has_suceeded": row["has_suceeded"].strip().lower() == "true",
            }
    return records


def save_failed_documents(records: dict[str, dict]) -> None:
    FAILED_DOCUMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=FAILED_DOCUMENTS_PATH.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            writer = csv.DictWriter(
                temporary_file,
                fieldnames=[
                    "file_path",
                    "permently_failed_count",
                    "has_suceeded",
                ],
            )
            writer.writeheader()
            for file_path in sorted(records):
                writer.writerow(
                    {
                        "file_path": file_path,
                        **records[file_path],
                    }
                )
        temporary_path.replace(FAILED_DOCUMENTS_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def find_size_outlier(
    stats: dict, pdf_size_bytes: int, json_size_bytes: int
) -> dict | None:
    historical_points = [
        point
        for point in stats["documents"].values()
        if point.get("status") in {"succeeded", "existing"}
        and point.get("pdf_size_bytes", 0) > 0
        and point.get("json_size_bytes", 0) > 0
    ]
    if len(historical_points) < 5 or json_size_bytes <= 0 or pdf_size_bytes <= 0:
        return None

    median_pdf_size = statistics.median(
        point["pdf_size_bytes"] for point in historical_points
    )
    median_ratio = statistics.median(
        point["json_size_bytes"] / point["pdf_size_bytes"]
        for point in historical_points
    )
    ratio = json_size_bytes / pdf_size_bytes
    if pdf_size_bytes < 1.5 * median_pdf_size or ratio >= 0.25 * median_ratio:
        return None
    return {
        "pdf_size_bytes": pdf_size_bytes,
        "json_size_bytes": json_size_bytes,
        "json_to_pdf_ratio": ratio,
        "historical_median_pdf_size_bytes": median_pdf_size,
        "historical_median_json_to_pdf_ratio": median_ratio,
    }


def parse_pdf(client, pdf_path: Path) -> tuple[dict, float]:
    start_time = time.perf_counter()
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
                "text": PROMPT
                + "\n\nAdditional instructions:\n"
                + ADDITIONAL_PROMPT,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RESPONSE_SCHEMA,
        },
    )
    parsed_output = json.loads(response.output_text)
    if not isinstance(parsed_output, dict) or not isinstance(
        parsed_output.get("transactions"), list
    ):
        raise ValueError("Model response does not match the expected JSON shape.")
    return parsed_output, time.perf_counter() - start_time


def log_directory_stats(directory: Path, stats: dict, logger: logging.Logger) -> None:
    successful = [
        point
        for point in stats["documents"].values()
        if point.get("status") in {"succeeded", "existing"}
    ]
    total_pdf_size = sum(point.get("pdf_size_bytes", 0) for point in successful)
    total_json_size = sum(point.get("json_size_bytes", 0) for point in successful)
    total_elapsed = sum(point.get("elapsed_seconds", 0.0) for point in successful)
    logger.info(
        "[directory stats] %s | documents=%d | PDF bytes=%d | JSON bytes=%d | "
        "parse seconds=%.2f | permanent failures=%d",
        directory,
        len(successful),
        total_pdf_size,
        total_json_size,
        total_elapsed,
        stats.get("permanent_failure_count", 0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse PTR PDFs into JSON using the Gemini API."
    )
    parser.add_argument(
        "directories",
        nargs="*",
        type=Path,
        help="One or more directories to scan recursively for PDFs.",
    )
    parser.add_argument(
        "--file-list",
        type=Path,
        help="Text file with one PDF path per line; relative paths use the list file's directory.",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        help="Stop after attempting this many documents in this run.",
    )
    existing_group = parser.add_mutually_exclusive_group()
    existing_group.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace JSON output files that already exist.",
    )
    existing_group.add_argument(
        "--ignore-existing",
        "--skip-existing",
        action="store_true",
        help="Skip JSON output files that already exist (the default).",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry PDFs recorded in data/failed_pdfs.csv.",
    )
    args = parser.parse_args()
    logger = configure_logging()

    if not args.directories and args.file_list is None:
        parser.error("Provide at least one PDF directory or --file-list.")
    if args.max_documents is not None and args.max_documents < 1:
        parser.error("--max-documents must be greater than zero.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("Set GEMINI_API_KEY before running this script.")
        return 2
    try:
        from google import genai
    except ImportError:
        logger.exception("The google-genai package is required to parse PDFs.")
        return 2

    try:
        pdfs = collect_pdfs(args.directories, args.file_list, logger)
        failed_documents = load_failed_documents()
        stats_by_directory = {
            directory: load_stats(directory)
            for directory in sorted({directory for directory, _ in pdfs})
        }
    except (OSError, ValueError, json.JSONDecodeError):
        logger.exception("Could not load the input list or persistent parsing state.")
        return 1

    if not pdfs:
        logger.warning("No PDFs found to process.")
        return 0

    try:
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        client = genai.Client(api_key=api_key)
    except Exception:
        logger.exception("Could not initialize the output directory or Gemini client.")
        return 2
    logger.info("Found %d unique PDF files; using model %s.", len(pdfs), MODEL)
    attempted_count = 0
    session_errors: list[str] = []
    session_permanent_failures: list[Path] = []
    directory_stats_paths = {
        directory: stats_path_for(directory) for directory in stats_by_directory
    }
    stopped_at_limit = False

    for directory, pdf_path in pdfs:
        output_path = OUTPUT_DIRECTORY / f"{pdf_path.stem}.json"
        failed_record = failed_documents.get(str(pdf_path))
        if failed_record is not None and not args.retry_failed:
            logger.info("[skipped permanently failed] %s", pdf_path)
            continue

        should_retry_failure = failed_record is not None and args.retry_failed
        if output_path.exists() and not args.overwrite and not should_retry_failure:
            logger.info("[skipped existing] %s", output_path)
            stats = stats_by_directory[directory]
            stats["documents"].setdefault(
                str(pdf_path),
                {
                    "status": "existing",
                    "pdf_size_bytes": pdf_path.stat().st_size,
                    "json_size_bytes": output_path.stat().st_size,
                    "elapsed_seconds": 0.0,
                },
            )
            write_json_atomically(directory_stats_paths[directory], stats)
            continue

        if args.max_documents is not None and attempted_count >= args.max_documents:
            stopped_at_limit = True
            break

        attempted_count += 1
        stats = stats_by_directory[directory]
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                parsed_output, elapsed_seconds = parse_pdf(client, pdf_path)
            except Exception as error:
                failure_message = (
                    f"{pdf_path} (attempt {attempt}/{RETRY_COUNT}): {error}"
                )
                session_errors.append(failure_message)
                logger.exception("[error] %s", failure_message)
                if attempt < RETRY_COUNT:
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue

                record = failed_documents.setdefault(
                    str(pdf_path),
                    {
                        "permently_failed_count": 0,
                        "has_suceeded": False,
                    },
                )
                record["permently_failed_count"] += 1
                session_permanent_failures.append(pdf_path)
                stats["failed_documents"][str(pdf_path)] = (
                    stats["failed_documents"].get(str(pdf_path), 0) + 1
                )
                stats["permanent_failure_count"] = (
                    stats.get("permanent_failure_count", 0) + 1
                )
                save_failed_documents(failed_documents)
                write_json_atomically(directory_stats_paths[directory], stats)
                logger.error("[failed permanently] %s", pdf_path)
                break

            write_json_atomically(output_path, parsed_output)
            pdf_size_bytes = pdf_path.stat().st_size
            json_size_bytes = output_path.stat().st_size
            outlier = find_size_outlier(stats, pdf_size_bytes, json_size_bytes)
            stats["documents"][str(pdf_path)] = {
                "status": "succeeded",
                "pdf_size_bytes": pdf_size_bytes,
                "json_size_bytes": json_size_bytes,
                "elapsed_seconds": elapsed_seconds,
            }
            if outlier is not None:
                stats["outliers"][str(pdf_path)] = outlier
                logger.warning(
                    "[size-ratio outlier] %s | PDF=%d bytes | JSON=%d bytes | "
                    "JSON/PDF ratio=%.6f",
                    pdf_path,
                    pdf_size_bytes,
                    json_size_bytes,
                    outlier["json_to_pdf_ratio"],
                )

            if failed_record is not None:
                failed_record["has_suceeded"] = True
                save_failed_documents(failed_documents)
            write_json_atomically(directory_stats_paths[directory], stats)
            logger.info(
                "[saved] %s | PDF=%d bytes | JSON=%d bytes | time=%.2f s",
                output_path,
                pdf_size_bytes,
                json_size_bytes,
                elapsed_seconds,
            )
            break

    for directory, stats in stats_by_directory.items():
        log_directory_stats(directory, stats, logger)

    accumulated_outliers = sorted(
        {
            path
            for stats in stats_by_directory.values()
            for path in stats.get("outliers", {})
        }
    )
    logger.info("Session attempted %d documents.", attempted_count)
    logger.info("Attempt errors this session: %d", len(session_errors))
    for failure in session_errors:
        logger.info("[attempt failure] %s", failure)
    logger.info("Permanent failures this session: %d", len(session_permanent_failures))
    for pdf_path in session_permanent_failures:
        logger.info("[permanent failure] %s", pdf_path)
    input_paths = {str(pdf_path) for _, pdf_path in pdfs}
    unresolved_failures = sorted(
        file_path
        for file_path in input_paths
        if file_path in failed_documents
        and not failed_documents[file_path]["has_suceeded"]
    )
    logger.info(
        "Unresolved permanent failures in the input set: %d",
        len(unresolved_failures),
    )
    for file_path in unresolved_failures:
        logger.info("[unresolved permanent failure] %s", file_path)
    logger.info("Accumulated JSON-size outlier warnings: %d", len(accumulated_outliers))
    for pdf_path in accumulated_outliers:
        logger.warning("[accumulated size-ratio outlier] %s", pdf_path)
    if stopped_at_limit:
        logger.info("Stopped after reaching --max-documents=%d.", args.max_documents)
    return 1 if session_permanent_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
