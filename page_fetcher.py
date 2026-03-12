import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WPIChatBot/1.0)"}
SKIP_TAGS = {"nav", "header", "footer", "script", "style", "noscript", "aside"}

# In-memory cache: url -> page text
_content_cache: dict[str, dict] = {}


def fetch_page_text(url: str, max_chars: int = 3000) -> dict:
    """Fetch and extract clean text from a WPI page. Uses in-memory cache."""
    if url in _content_cache:
        return _content_cache[url]

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"url": url, "text": "", "error": str(e)}

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup.find_all(SKIP_TAGS):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find(id="main-content")
        or soup.find(class_="main-content")
        or soup.find("article")
        or soup.body
    )

    if not main:
        return {"url": url, "text": "", "error": "No content found"}

    raw_text = main.get_text(separator="\n")
    lines = [line.strip() for line in raw_text.splitlines()]
    clean_lines = [l for l in lines if l and len(l) > 1]
    text = "\n".join(clean_lines)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [content trimmed]"

    result = {"url": url, "text": text, "error": None}
    _content_cache[url] = result
    return result


def fetch_pages(pages: list[dict], max_workers: int = 5) -> list[dict]:
    """Fetch all pages IN PARALLEL. Returns results in original order."""
    results = [None] * len(pages)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(fetch_page_text, page["url"]): i
            for i, page in enumerate(pages)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            page = pages[i]
            result = future.result()
            result["title"] = page.get("text", page["url"])
            results[i] = result

            if result["error"]:
                print(f"  [!] {result['title']}: {result['error']}")
            else:
                print(f"  ✓ {result['title']} ({len(result['text'])} chars)")

    return results
