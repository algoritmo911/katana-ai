from bs4 import BeautifulSoup
from readability import Document

def extract_main_content(html: str) -> dict:
    """
    Извлекает основную статью из HTML-документа, очищая от меню, рекламы и т.д.
    """
    doc = Document(html)

    return {
        "title": doc.title(),
        "content_text": BeautifulSoup(doc.summary(), 'html.parser').get_text(separator='\\n', strip=True),
        "content_html": doc.summary()
    }
