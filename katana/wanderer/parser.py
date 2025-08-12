from bs4 import BeautifulSoup
from readability import Document
from typing import Dict, List
from urllib.parse import urljoin

def extract_main_content(html: str, base_url: str) -> Dict:
    """
    Извлекает основную статью, а также все гиперссылки из HTML-документа.
    """
    doc = Document(html)
    soup = BeautifulSoup(html, 'html.parser')

    # Extract all links and their context from the original soup
    links: List[Dict[str, str]] = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href')
        if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
            continue

        # Resolve relative URLs to absolute URLs
        absolute_url = urljoin(base_url, href)

        # Get anchor text and a bit of surrounding context
        anchor_text = a_tag.get_text(strip=True)
        parent_text = a_tag.parent.get_text(strip=True) if a_tag.parent else ""

        links.append({
            "url": absolute_url,
            "anchor": anchor_text,
            "context": parent_text[:200] # Limit context length
        })

    return {
        "title": doc.title(),
        "content_text": BeautifulSoup(doc.summary(), 'html.parser').get_text(separator='\\n', strip=True),
        "content_html": doc.summary(),
        "links": links
    }
