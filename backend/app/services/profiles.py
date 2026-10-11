import io
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader

from app.security import redact_contacts

MAX_UPLOAD = 10 * 1024 * 1024


def extract_document(filename: str, content_type: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD:
        raise ValueError("File exceeds 10 MB")
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "txt":
        if content_type not in {"text/plain", "application/octet-stream"} or b"\x00" in content:
            raise ValueError("TXT MIME/content mismatch")
        text = content.decode("utf-8-sig")
    elif extension == "pdf":
        if content_type != "application/pdf" or not content.startswith(b"%PDF-"):
            raise ValueError("PDF MIME/content mismatch")
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError("Encrypted or oversized PDF; paste text instead")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif extension == "docx":
        if (
            content_type
            != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            raise ValueError("DOCX MIME mismatch")
        try:
            with ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 500 or sum(v.file_size for v in entries) > 30 * 1024 * 1024:
                    raise ValueError("DOCX expanded size exceeds limit")
                if any(
                    v.filename.startswith("/") or ".." in v.filename.split("/") for v in entries
                ):
                    raise ValueError("Unsafe DOCX archive path")
                xml = archive.read("word/document.xml")
                if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                    raise ValueError("XML entities are not allowed")
                root = ElementTree.fromstring(xml)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                text = "\n".join(
                    "".join(t.text or "" for t in p.findall(".//w:t", ns))
                    for p in root.findall(".//w:p", ns)
                )
        except (BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise ValueError("Malformed DOCX") from exc
    else:
        raise ValueError("Upload PDF, DOCX, or UTF-8 TXT")
    if not text.strip():
        raise ValueError("No extractable text; paste résumé text instead (OCR is not enabled)")
    return text[:250000]


def draft_profile(text: str, source: str = "pasted résumé") -> dict:
    """Local, conservative extraction. Every retained fact is an editable excerpt."""
    safe = redact_contacts(text)
    evidence, seen = [], set()
    for index, line in enumerate(safe.splitlines()):
        line = re.sub(r"^[\s•*\-]+", "", line).strip()
        if len(line) < 12 or line.lower() in seen:
            continue
        # A short opening name/address line is not career evidence.
        if index < 3 and (
            re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+){1,4}", line)
            or re.match(r"(?:name|address|date of birth|nationality)\s*:", line, re.I)
        ):
            continue
        if any(
            marker in line.lower()
            for marker in ["[email removed]", "[phone removed]", "[profile link removed]"]
        ):
            continue
        seen.add(line.lower())
        low = line.lower()
        category = "experience"
        if any(v in low for v in ["phd", "bachelor", "master of", "degree"]):
            category = "education"
        elif any(v in low for v in ["language", "fluent", "native", "dutch"]):
            category = "languages"
        elif any(v in low for v in ["relocat", "mobility", "travel globally"]):
            category = "preferences"
        elif any(v in low for v in ["led", "leadership", "team", "direct reports"]):
            category = "leadership"
        evidence.append(
            {
                "id": f"e{len(evidence) + 1}",
                "category": category,
                "text": line[:3000],
                "source": source,
            }
        )
    return {
        "label": "Imported candidate profile",
        "evidence": evidence,
        "work_authorization": "unknown",
        "salary_expectations": "unknown",
        "notes": "Review every excerpt and correct extraction before approving.",
    }


def validate_profile(data: dict) -> dict:
    if not isinstance(data.get("label"), str) or not data["label"].strip():
        raise ValueError("Profile label is required")
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list) or not evidence or len(evidence) > 500:
        raise ValueError("Add 1–500 evidence excerpts before approval")
    ids = set()
    for item in evidence:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(k), str) and item[k].strip()
            for k in ("id", "text", "source", "category")
        ):
            raise ValueError("Evidence requires id, text, source, and category")
        if item["id"] in ids or len(item["text"]) > 5000:
            raise ValueError("Duplicate evidence ID or excerpt exceeds 5000 characters")
        ids.add(item["id"])
    return data
