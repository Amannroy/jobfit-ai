import io
import pytest
import pypdf
from app.services.pdf_service import (
    extract_text_from_pdf,
    validate_pdf_metadata,
    PDFValidationError,
    MAX_FILE_SIZE_BYTES,
)


def _build_pdf_bytes(text: str) -> bytes:
    """Helper to synthesize a valid, in-memory PDF containing the given text."""
    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT\n/F1 12 Tf\n72 700 Td\n({safe_text}) Tj\nET".encode("latin-1", errors="replace")
    stream_len = len(stream_content)
    pdf_bytes = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length {stream_len} >>
stream
""".encode("latin-1") + stream_content + b"""
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000227 00000 n
0000000306 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
500
%%EOF"""
    return pdf_bytes


def _build_blank_pdf_bytes() -> bytes:
    """Helper to synthesize a valid PDF with an empty page (zero extractable text)."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _build_encrypted_pdf_bytes(password: str = "secret") -> bytes:
    """Helper to synthesize a password-protected PDF."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

def test_valid_pdf_extraction():
    sample_text = (
        "Experienced Software Engineer with 5+ years building scalable microservices in Python, "
        "FastAPI, and React. Architected high-throughput data processing systems and REST APIs."
    )
    raw_pdf = _build_pdf_bytes(sample_text)
    extracted = extract_text_from_pdf(raw_pdf, filename="john_doe_resume.pdf", content_type="application/pdf")

    assert sample_text in extracted
    assert len(extracted) >= 100


def test_empty_file_rejected():
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(b"", filename="empty.pdf")

    assert exc_info.value.status_code == 400
    assert "empty (0 bytes)" in exc_info.value.message


def test_corrupt_file_rejected():
    garbage_bytes = b"This is not a real PDF document at all. It is just plain corrupted garbage bytes."
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(garbage_bytes, filename="broken.pdf")

    assert exc_info.value.status_code == 400
    assert "corrupt or not a valid PDF" in exc_info.value.message


def test_oversized_file_rejected():
    oversized_length = MAX_FILE_SIZE_BYTES + 1024  # Just over 5 MB
    dummy_bytes = b"0" * oversized_length

    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(dummy_bytes, filename="large_resume.pdf")

    assert exc_info.value.status_code == 413
    assert "exceeds the 5 MB limit" in exc_info.value.message


def test_insufficient_text_scanned_pdf_rejected():
    blank_pdf = _build_blank_pdf_bytes()
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(blank_pdf, filename="scanned_resume.pdf")

    assert exc_info.value.status_code == 400
    assert "insufficient extractable text" in exc_info.value.message
    assert "Scanned or image-only resumes are not supported yet" in exc_info.value.message


def test_encrypted_pdf_rejected():
    encrypted_pdf = _build_encrypted_pdf_bytes("password123")
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(encrypted_pdf, filename="locked_resume.pdf")

    assert exc_info.value.status_code == 400
    assert "password-protected or encrypted" in exc_info.value.message


def test_invalid_extension_rejected():
    raw_pdf = _build_pdf_bytes("Some text that would otherwise be long enough to parse if extension were valid.")
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(raw_pdf, filename="resume.docx")

    assert exc_info.value.status_code == 400
    assert "Invalid file extension" in exc_info.value.message


def test_invalid_content_type_rejected():
    raw_pdf = _build_pdf_bytes("Some text that would otherwise be long enough to parse if content-type were valid.")
    with pytest.raises(PDFValidationError) as exc_info:
        extract_text_from_pdf(raw_pdf, filename="resume.pdf", content_type="image/png")

    assert exc_info.value.status_code == 400
    assert "Invalid file content type" in exc_info.value.message
