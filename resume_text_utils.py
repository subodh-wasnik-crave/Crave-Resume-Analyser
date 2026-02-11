from pypdf import PdfReader
from docx import Document

def extract_text(file):
    """
    Extract text from PDF or DOCX resume
    """
    text = ""

    try:
        if file.name.lower().endswith(".pdf"):
            reader = PdfReader(file)
            pages = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)

            text = "\n".join(pages)

        elif file.name.lower().endswith(".docx"):
            doc = Document(file)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)

    except Exception as e:
        print(f"Text extraction error: {str(e)}")

    return text.strip()