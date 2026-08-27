from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader

from .chunking import normalize_text


class ReadingExtractionError(Exception):
    code = "EXTRACTION_ERROR"


class UnsupportedReadingFile(ReadingExtractionError):
    code = "UNSUPPORTED_FILE_TYPE"


class ReadingFileTooLarge(ReadingExtractionError):
    code = "FILE_TOO_LARGE"


class ReadingDocumentTooLarge(ReadingExtractionError):
    code = "DOCUMENT_TOO_LARGE"


class EmptyReadingDocument(ReadingExtractionError):
    code = "EMPTY_DOCUMENT"


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    text: str
    page_count: int | None = None


def _validate_size(field_file) -> None:
    max_bytes = int(settings.READING_AI_MAX_FILE_SIZE_MB * 1024 * 1024)
    try:
        size = field_file.size
    except (OSError, ValueError):
        size = None

    if size is not None and size > max_bytes:
        raise ReadingFileTooLarge(f"File size is {size} bytes; maximum is {max_bytes} bytes.")


def _extract_pdf(field_file) -> ExtractedDocument:
    field_file.open("rb")
    try:
        reader = PdfReader(field_file.file)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # pragma: no cover - depends on PDF encryption
                raise ReadingExtractionError("Encrypted PDF is not supported.") from exc

        page_count = len(reader.pages)
        if page_count > settings.READING_AI_MAX_PDF_PAGES:
            raise ReadingDocumentTooLarge(
                f"PDF has {page_count} pages; maximum is {settings.READING_AI_MAX_PDF_PAGES}."
            )

        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            extracted = (page.extract_text() or "").strip()
            if extracted:
                pages.append(f"[Page {index}]\n{extracted}")

        text = normalize_text("\n\n".join(pages))
        if not text:
            raise EmptyReadingDocument(
                "No extractable text found. Scanned PDFs need an OCR pipeline."
            )

        return ExtractedDocument(text=text, page_count=page_count)
    finally:
        field_file.close()


def _extract_plain_text(field_file) -> ExtractedDocument:
    field_file.open("rb")
    try:
        raw = field_file.file.read()
    finally:
        field_file.close()

    if not raw:
        raise EmptyReadingDocument("The document is empty.")

    text = raw.decode("utf-8", errors="replace")
    text = normalize_text(text)
    if not text:
        raise EmptyReadingDocument("The document contains no readable text.")
    return ExtractedDocument(text=text)


def extract_reading_document(field_file) -> ExtractedDocument:
    _validate_size(field_file)
    suffix = Path(field_file.name or "").suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(field_file)
    if suffix in {".txt", ".md"}:
        return _extract_plain_text(field_file)

    raise UnsupportedReadingFile(
        f"Unsupported reading file type: {suffix or 'unknown'}. "
        "Supported types are PDF, TXT and Markdown."
    )
