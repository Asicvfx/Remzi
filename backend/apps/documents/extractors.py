from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from apps.common.text import repair_mojibake


class UnsupportedDocumentTypeError(ValueError):
    pass


class EmptyExtractedTextError(ValueError):
    pass


class DocumentTextExtractor:
    @classmethod
    def extract(cls, *, document):
        file_type = document.file_type.lower()
        file_path = Path(document.file.path)

        if file_type == "txt":
            text = cls._extract_txt(file_path)
        elif file_type == "pdf":
            text = cls._extract_pdf(file_path)
        elif file_type == "docx":
            text = cls._extract_docx(file_path)
        else:
            raise UnsupportedDocumentTypeError(f"Unsupported file type: {file_type}")

        normalized_text = repair_mojibake(text.strip())
        if not normalized_text:
            raise EmptyExtractedTextError("No extractable text was found in this document.")
        return normalized_text

    @staticmethod
    def _extract_txt(file_path):
        raw = file_path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1")

    @staticmethod
    def _extract_pdf(file_path):
        reader = PdfReader(str(file_path))
        page_texts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_texts.append(page_text.strip())
        return "\n\n".join(page_texts)

    @staticmethod
    def _extract_docx(file_path):
        document = DocxDocument(str(file_path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)
