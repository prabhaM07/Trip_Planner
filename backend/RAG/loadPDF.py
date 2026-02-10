from pathlib import Path
from typing import List
import pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path
from langchain_core.documents import Document


class PDFProcessor:
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    def load(self) -> List[Document]:
        reader = PdfReader(self.pdf_path)
        documents: List[Document] = []

        # PyPDF text only
        for page_num, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(self.pdf_path),
                            "page": page_num + 1,
                            "extraction_method": "pypdf",
                        },
                    )
                )

        # OCR fallback only if nothing extracted
        if not documents:
            images = convert_from_path(self.pdf_path)
            for page_num, image in enumerate(images):
                ocr_text = pytesseract.image_to_string(image).strip()
                if ocr_text:
                    documents.append(
                        Document(
                            page_content=ocr_text,
                            metadata={
                                "source": str(self.pdf_path),
                                "page": page_num + 1,
                                "extraction_method": "ocr",
                            },
                        )
                    )

        if not documents:
            raise ValueError(f"No content extracted from PDF: {self.pdf_path}")

        return documents
