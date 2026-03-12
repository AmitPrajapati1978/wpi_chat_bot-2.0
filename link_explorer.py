import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.wpi.edu"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WPIChatBot/1.0)"}

# URLs that are navigation/utility pages — not useful content
BLOCKED_PATHS = {
    "/", "/topics", "/directories", "/contact", "/offices",
    "/parents", "/faculty-staff", "/admissions", "/academics",
    "/about", "/news", "/student-experience", "/students",
    "/about/locations", "/library",
}

# In-memory cache: url -> list of links
_page_cache: dict[str, list[dict]] = {}


def is_useful_link(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.fragment and not parsed.path.strip("/"):
        return False
    if parsed.path in BLOCKED_PATHS:
        return False
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return False
    return True


def fetch_links(url: str) -> list[dict]:
    """Fetch a WPI page and return all internal links. Uses in-memory cache."""
    if url in _page_cache:
        return _page_cache[url]

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"  [!] Could not fetch {url}: {e}")
        _page_cache[url] = []
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    seen = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        text = tag.get_text(strip=True)
        full_url = urljoin(BASE_URL, href)
        parsed = urlparse(full_url)

        if (
            parsed.netloc in ("www.wpi.edu", "wpi.edu")
            and parsed.scheme in ("http", "https")
            and full_url not in seen
            and text
            and len(text) > 2
            and not full_url.endswith((".pdf", ".jpg", ".png", ".zip"))
            and is_useful_link(full_url)
        ):
            links.append({"url": full_url, "text": text})
            seen.add(full_url)

    _page_cache[url] = links
    return links


def fetch_links_parallel(urls: list[str], max_workers: int = 10) -> dict[str, list[dict]]:
    """Fetch links from multiple pages in parallel. Returns {url: links}."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_links, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            results[url] = future.result()
    return results


def rank_links_batched(question: str, all_links: list[dict], top_n: int) -> list[dict]:
    """
    Single Claude call to rank all links across all pages at this depth.
    Much cheaper than one call per page.
    """
    if not all_links:
        return []

    client = anthropic.Anthropic()
    candidates = all_links[:120]  # cap to keep prompt size reasonable

    links_str = "\n".join(
        f"{i+1}. [{item['text']}] {item['url']}"
        for i, item in enumerate(candidates)
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system="""You are a web navigation assistant for the WPI website.
Given a user question and a list of page links, select the most relevant links likely to contain the answer.
Return ONLY a JSON array of link numbers (1-based integers), most relevant first.
Example: [3, 7, 12]""",
        messages=[{
            "role": "user",
            "content": f"""User question: {question}

Available links:
{links_str}

Return a JSON array of the top {top_n} most relevant link numbers."""
        }],
    )

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.find("]", start)
    if start == -1 or end == -1:
        return []

    indices = json.loads(raw[start:end + 1])
    selected = []
    for idx in indices:
        if 1 <= idx <= len(candidates):
            selected.append(candidates[idx - 1])

    return selected[:top_n]


def explore(question: str, start_urls: list[str], max_depth: int = 3, top_n: int = 3) -> list[dict]:
    """
    Optimized explorer:
    - Fetches all pages at each depth IN PARALLEL
    - ONE Claude call per depth (not one per page)
    - In-memory cache avoids re-fetching pages
    - Early stopping if no new links are found
    """
    frontier_urls = list(start_urls)
    visited = set(start_urls)
    all_candidates = []

    for depth in range(1, max_depth + 1):
        t0 = time.time()
        print(f"\n  [Depth {depth}] Fetching {len(frontier_urls)} page(s) in parallel...")

        # Step A: Fetch all pages at this depth in parallel
        page_links = fetch_links_parallel(frontier_urls)

        # Step B: Collect all fresh (unvisited) links across all pages
        fresh_links = []
        seen_this_depth = set()
        for url, links in page_links.items():
            for link in links:
                if link["url"] not in visited and link["url"] not in seen_this_depth:
                    fresh_links.append(link)
                    seen_this_depth.add(link["url"])

        print(f"    Total fresh links: {len(fresh_links)}")

        if not fresh_links:
            print("  No new links found. Stopping early.")
            break

        # Step C: ONE Claude call to rank all fresh links for this depth
        top = rank_links_batched(question, fresh_links, top_n=top_n * len(frontier_urls))
        print(f"    Claude selected {len(top)} link(s) in {time.time()-t0:.1f}s:")
        for t in top:
            print(f"      • {t['text']}  ({t['url']})")
            visited.add(t["url"])

        all_candidates.extend(top)
        frontier_urls = [t["url"] for t in top]

        # Early stopping: if we have confident matches and are deep enough
        if depth >= 2 and len(top) <= 2:
            print("  Few links selected — likely reached content pages. Stopping early.")
            break

    # Final ranking: one Claude call to pick top 5 from all candidates
    if not all_candidates:
        return []

    print(f"\n  Final ranking across {len(all_candidates)} candidates...")
    unique = {p["url"]: p for p in all_candidates}
    return rank_links_batched(question, list(unique.values()), top_n=5)


if __name__ == "__main__":
    from section_selector import select_sections

    print("WPI Link Explorer — type a question, Ctrl+C to quit\n")
    while True:
        try:
            question = input("Your question: ").strip()
            if not question:
                continue

            print("\n--- Step 1: Selecting top sections ---")
            sections = select_sections(question)
            for i, s in enumerate(sections, 1):
                print(f"  {i}. [{s['section_key']}] {s['url']}")

            print("\n--- Step 2: Exploring links ---")
            t0 = time.time()
            final_pages = explore(question, [s["url"] for s in sections])
            print(f"\n  Done in {time.time()-t0:.1f}s")

            print("\n--- Final pages to read ---")
            for i, page in enumerate(final_pages, 1):
                print(f"  {i}. {page['text']}")
                print(f"     {page['url']}")
            print()

        except KeyboardInterrupt:
            print("\nBye!")
            break
