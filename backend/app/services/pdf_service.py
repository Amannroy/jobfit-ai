import io
from typing import Optional
import pypdf
from pypdf.errors import PdfReadError

# Validation constants
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_EXTRACTED_TEXT_LENGTH = 100


class PDFValidationError(Exception):
    """
    Exception raised when PDF validation or text extraction fails.
    Carries a human-friendly message and an appropriate HTTP status code.
    """
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_pdf_metadata(
    filename: Optional[str],
    content_type: Optional[str],
    file_size: int,
) -> None:
    """
    Validates file extension, MIME type, and size in memory.
    """
    # 1. Extension check
    if not filename or not filename.lower().endswith(".pdf"):
        raise PDFValidationError(
            "Invalid file extension. Please upload a file with a '.pdf' extension.",
            status_code=400,
        )

    # 2. Content type check
    valid_content_types = {
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
        "application/octet-stream",
    }
    if content_type and content_type.lower() not in valid_content_types:
        raise PDFValidationError(
            f"Invalid file content type '{content_type}'. Expected 'application/pdf'.",
            status_code=400,
        )

    # 3. Empty file check
    if file_size <= 0:
        raise PDFValidationError(
            "The uploaded PDF file is empty (0 bytes).",
            status_code=400,
        )

    # 4. Maximum size check (5 MB)
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        raise PDFValidationError(
            f"File size exceeds the 5 MB limit (received {size_mb:.2f} MB). Please upload a smaller file.",
            status_code=413,
        )


def extract_text_from_pdf(
    pdf_bytes: bytes,
    filename: Optional[str] = "resume.pdf",
    content_type: Optional[str] = "application/pdf",
) -> str:
    """
    Extracts text from in-memory PDF bytes after validating structure and readability.
    Never writes the file or content to disk.
    """
    # Validate metadata first
    validate_pdf_metadata(
        filename=filename,
        content_type=content_type,
        file_size=len(pdf_bytes),
    )

    # Process stream strictly in memory
    stream = io.BytesIO(pdf_bytes)

    try:
        reader = pypdf.PdfReader(stream)
    except PdfReadError as e:
        raise PDFValidationError(
            "The uploaded file is corrupt or not a valid PDF document.",
            status_code=400,
        ) from e
    except Exception as e:
        raise PDFValidationError(
            "Failed to parse PDF document. Please verify the file is not damaged.",
            status_code=400,
        ) from e

    # Reject encrypted / password-protected files
    if reader.is_encrypted:
        raise PDFValidationError(
            "The uploaded PDF is password-protected or encrypted. Please upload an unencrypted PDF.",
            status_code=400,
        )

    # Verify document has pages
    if len(reader.pages) == 0:
        raise PDFValidationError(
            "The uploaded PDF contains no pages.",
            status_code=400,
        )

    # Extract text from all pages
    extracted_chunks = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                extracted_chunks.append(page_text.strip())
        except Exception:
            continue

    full_text = "\n\n".join(extracted_chunks).strip()

    # Reject PDFs with insufficient extractable text (e.g. scanned images, blanks)
    if len(full_text) < MIN_EXTRACTED_TEXT_LENGTH:
        raise PDFValidationError(
            f"The uploaded PDF contains insufficient extractable text ({len(full_text)} characters found). "
            "Scanned or image-only resumes are not supported yet. "
            "Please upload a text-readable PDF generated directly from Word, Docs, or a text editor.",
            status_code=400,
        )

    return full_text
