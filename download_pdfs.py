import argparse
import logging
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "clerk_directories"
PDF_ROOT = ROOT / "data" / "pdf"
LOG_PATH = ROOT / "data" / "log" / "download_pdfs.log"
PDF_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{document_id}.pdf"


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
    return logging.getLogger("download_pdfs")


def find_xml_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".xml":
            raise ValueError(f"Input file must be XML: {input_path}")
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    return sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() == ".xml"
    )


def read_documents(xml_files: list[Path], logger: logging.Logger) -> dict[int, str]:
    documents: dict[int, str] = {}
    for xml_file in xml_files:
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            logger.exception("Could not parse XML file: %s", xml_file)
            continue
        except OSError:
            logger.exception("Could not read XML file: %s", xml_file)
            continue

        for member in root.findall(".//Member"):
            filing_type = member.findtext("FilingType", "").strip()
            if filing_type != "P":
                continue

            document_id_text = member.findtext("DocID", "").strip()
            year = member.findtext("Year", "").strip()
            try:
                document_id = int(document_id_text)
                int(year)
            except ValueError:
                logger.warning(
                    "Skipping member with invalid DocID or Year in %s: DocID=%r Year=%r",
                    xml_file,
                    document_id_text,
                    year,
                )
                continue

            if document_id in documents:
                if documents[document_id] != year:
                    logger.warning(
                        "Duplicate DocID %s has conflicting years %s and %s; keeping the first",
                        document_id,
                        documents[document_id],
                        year,
                    )
                continue
            documents[document_id] = year
    return documents


def download_pdf(
    document_id: int, year: str, overwrite: bool, logger: logging.Logger
) -> str:
    category = "handwritten_ptr" if document_id < 20_000_000 else "digital_ptr"
    output_path = PDF_ROOT / category / f"{document_id}.pdf"
    if output_path.exists() and not overwrite:
        logger.info("[skipped existing] %s", output_path)
        return "skipped"

    url = PDF_URL.format(year=year, document_id=document_id)
    temporary_path: Path | None = None
    try:
        with urlopen(url, timeout=60) as response:
            content = response.read()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output_path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
        temporary_path.replace(output_path)
    except (HTTPError, URLError, TimeoutError, OSError):
        logger.exception("[failed to download or save] %s", url)
        return "failed"
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    output_path.write_bytes(content)
    logger.info("[downloaded] %s", output_path)
    return "downloaded"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download PTR PDFs listed in Office of the Clerk XML files."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="An XML file or a directory containing XML files (default: data/clerk_directories).",
    )
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--overwrite",
        action="store_true",
        help="Download PDFs even when the destination already exists.",
    )
    cache_group.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip PDFs already present (the default).",
    )
    args = parser.parse_args()
    logger = configure_logging()

    try:
        xml_files = find_xml_files(args.input.resolve())
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    if not xml_files:
        parser.error(f"No XML files found in {args.input}")

    documents = read_documents(xml_files, logger)
    logger.info("Found %d unique document IDs in %d XML files.", len(documents), len(xml_files))
    results = {"downloaded": 0, "skipped": 0, "failed": 0}
    for document_id, year in documents.items():
        result = download_pdf(document_id, year, args.overwrite, logger)
        results[result] += 1

    logger.info(
        "Finished: %d downloaded, %d skipped, %d failed.",
        results["downloaded"],
        results["skipped"],
        results["failed"],
    )
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
