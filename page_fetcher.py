import csv
import io
import json
import os
import re
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

BUCKET = "wpi-knowledge"
MAX_CHARS = 1500  # keep total prompt within Groq free tier TPM limit

_s3_client = None
_nid_to_url: dict[str, str] = {}  # nid → real wpi.edu alias URL


def get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
    return _s3_client


def _get_nid_url_map() -> dict[str, str]:
    """Lazy-load nid → wpi.edu alias from track-data.csv (cached after first call)."""
    if _nid_to_url:
        return _nid_to_url
    try:
        raw = get_s3().get_object(Bucket=BUCKET, Key="data/drupal/track-data.csv")["Body"].read().decode()
        reader = csv.DictReader(io.StringIO(raw))
        for row in reader:
            nid = row.get("nid", "").strip()
            alias = row.get("alias", "").strip()
            if nid and alias and alias.startswith("http"):
                _nid_to_url[nid] = alias
    except Exception:
        pass
    return _nid_to_url


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    """
    If text starts with YAML frontmatter (--- ... ---), parse it.
    Returns (metadata_dict, body_text).
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    front = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in front.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"')
    return meta, body


def _parse_markdown(key: str, raw: str) -> dict:
    """Parse a markdown file, extracting frontmatter for source URL and title."""
    meta, body = _extract_frontmatter(raw)

    title = meta.get("title", key.split("/")[-1].replace("_", " ").rsplit(".", 1)[0])

    # Prefer the real wpi.edu alias URL over the internal staging source_url
    nid = meta.get("nid", "").strip()
    real_url = _get_nid_url_map().get(nid, "") if nid else ""
    source_url = real_url or meta.get("source_url", "") or key

    text = body
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [content trimmed]"

    return {
        "url": source_url,
        "title": title,
        "text": text,
        "error": None,
    }


def _parse_csv(key: str, raw: str, query: str = "") -> dict:
    """
    Parse a CSV file into readable text.
    Strips HTML from body fields and formats each row as key: value pairs.
    For the expert profiles CSV, filters rows by query keywords before truncating.
    """
    title = key.split("/")[-1].replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()

    try:
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
    except Exception as e:
        return {"url": key, "title": title, "text": raw[:MAX_CHARS], "error": str(e)}

    if not rows:
        return {"url": key, "title": title, "text": "No data found.", "error": None}

    # For large CSVs with a query, rank rows by keyword relevance before truncating.
    # Without this, alphabetical truncation hides relevant rows (e.g. "data-science"
    # advisor cut off before "biochemistry" entries reach MAX_CHARS).
    if query:
        _STOP_WORDS = {
            "tell", "more", "about", "what", "which", "where", "when", "does",
            "have", "this", "that", "with", "from", "they", "will", "been",
            "their", "there", "your", "much", "some", "such", "than", "into",
            "over", "also", "only", "then", "very", "just", "like", "know",
            "make", "come", "give", "same", "well", "want", "look", "here",
            "help", "find", "show", "need", "work", "time", "year", "them",
            "same", "take", "good", "many", "most", "these", "those", "please",
        }
        search_terms = [
            w.lower() for w in query.split()
            if len(w) > 3 and w.lower() not in _STOP_WORDS
        ]
        if search_terms:
            def _row_score(row: dict) -> int:
                blob = " ".join(v for v in row.values() if v and v != "NULL").lower()
                return sum(1 for t in search_terms if t in blob)

            scored = sorted(rows, key=_row_score, reverse=True)
            matched = [r for r in scored if _row_score(r) > 0]
            rows = matched[:8] if matched else scored[:5]

    # Fields to skip (internal IDs, timestamps, PII, irrelevant metadata)
    skip_fields = {
        "nid", "uid", "created", "changed", "status", "body_format", "body_summary",
        "field_image_target_id", "field_tags_target_id",
        "field_announcements_checkbox_value", "field_events_checkbox_value",
        "field_exclude_value", "field_full_bleed_value",
        "field_media_coverage_checkbox_value", "field_news_widget_value",
        "field_number_of_announcements_value", "field_number_of_articles_value",
        "field_number_of_events_value", "field_published_at__value",
        "field_two_columns_checkbox_value", "field_two_columns_events_value",
        # Student PII — names and IDs from project CSVs
        "Creator", "Identifier", "Orcid", "Rights Statement", "License",
        "Date created", "Model",
    }

    # HTML fields to strip tags from
    html_fields = {
        "body_value", "field_description_value", "field_body_value",
        "field_application_materials_value", "field_what_they_are_looking_for_value",
        "expert_bio", "faculty_bio",
    }

    lines = []
    for row in rows:
        row_lines = []
        for k, v in row.items():
            if k in skip_fields or not v or not v.strip():
                continue
            if k in html_fields:
                v = _strip_html(v)
            if v.strip():
                row_lines.append(f"{k}: {v.strip()}")
        if row_lines:
            lines.append("\n".join(row_lines))
            lines.append("---")

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [content trimmed]"

    return {"url": key, "title": title, "text": text, "error": None}


def _parse_json(key: str, raw: str) -> dict:
    """Parse a JSON file into readable text. Handles course catalog, blog posts, and tuition formats."""
    title = key.split("/")[-1].replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()

    try:
        data = json.loads(raw)
    except Exception as e:
        return {"url": key, "title": title, "text": raw[:MAX_CHARS], "error": str(e)}

    source_url = key

    # Course catalog: list of course objects
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                parts = []
                for field in ("code", "title", "credits", "description", "prerequisites"):
                    val = item.get(field)
                    if val:
                        parts.append(f"{field}: {val}")
                if parts:
                    lines.append("\n".join(parts))
                    lines.append("---")
        text = "\n".join(lines)

    # Blog posts feed (data/catalyst/posts.json)
    elif isinstance(data, dict) and isinstance(data.get("posts"), list):
        source_url = data.get("feed_url", key)
        lines = []
        for post in data["posts"]:
            parts = []
            if post.get("title"):
                parts.append(f"Title: {post['title']}")
            if post.get("categories"):
                parts.append(f"Topics: {', '.join(post['categories'])}")
            if post.get("excerpt"):
                parts.append(f"Summary: {post['excerpt'][:350]}")
            if post.get("url"):
                parts.append(f"URL: {post['url']}")
            if parts:
                lines.append("\n".join(parts))
                lines.append("---")
        text = "\n".join(lines)

    # Tuition / cost-of-attendance JSON (data/tuition-costs/cost-rate-current.json)
    elif isinstance(data, dict) and "academic_years" in data:
        urls = data.get("source_urls", [])
        source_url = urls[0] if urls else key
        scraped = data.get("scraped_at", "")
        lines = [f"WPI Tuition & Cost of Attendance (as of {scraped})\n"]
        for year, ay in data.get("academic_years", {}).items():
            lines.append(f"=== {year} ===")
            ug = ay.get("undergraduate", {})
            if ug:
                t = ug.get("tuition", {})
                if t.get("annual_full_time"):
                    lines.append(f"Undergraduate tuition: ${t['annual_full_time']:,}/year full-time")
                if t.get("per_credit_part_time"):
                    lines.append(f"  Part-time: ${t['per_credit_part_time']:,}/credit")
                fees = ug.get("fees", {})
                fee_parts = []
                if fees.get("student_life_annual"):
                    fee_parts.append(f"Student Life ${fees['student_life_annual']:,}")
                if fees.get("health_wellness_annual"):
                    fee_parts.append(f"Health & Wellness ${fees['health_wellness_annual']:,}")
                if fee_parts:
                    lines.append(f"UG annual fees: {', '.join(fee_parts)}")
            grad = ay.get("graduate", {})
            if grad:
                gt = grad.get("tuition", {})
                per_credit = gt.get("general_per_credit") or gt.get("per_credit") or gt.get("per_credit_hour")
                if per_credit:
                    lines.append(f"Graduate tuition: ${per_credit:,}/credit (general rate)")
            hi = ay.get("health_insurance", {})
            if hi and hi.get("annual_cost"):
                lines.append(f"Health insurance: ${hi['annual_cost']:,}/year")
        text = "\n".join(lines)

    else:
        text = json.dumps(data, indent=2)

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [content trimmed]"

    return {"url": source_url, "title": title, "text": text, "error": None}


def fetch_page_s3(item: dict) -> dict:
    """
    Read one file from S3 and return {url, title, text, error}.
    item must have a 'key' field with the S3 object key.
    Optional 'query' field is forwarded to parsers that can use it for filtering.
    """
    key = item.get("key") or item.get("url", "")
    query = item.get("query", "")

    try:
        response = get_s3().get_object(Bucket=BUCKET, Key=key)
        raw = response["Body"].read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"url": key, "title": key.split("/")[-1], "text": "", "error": str(e)}

    if key.endswith(".md"):
        return _parse_markdown(key, raw)
    elif key.endswith(".csv"):
        return _parse_csv(key, raw, query=query)
    elif key.endswith(".json"):
        return _parse_json(key, raw)
    else:
        text = raw[:MAX_CHARS]
        return {
            "url": key,
            "title": key.split("/")[-1],
            "text": text,
            "error": None,
        }


def fetch_pages(pages: list[dict], max_workers: int = 8) -> list[dict]:
    """Fetch all pages from S3 IN PARALLEL. Returns results in original order."""
    results = [None] * len(pages)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(fetch_page_s3, page): i
            for i, page in enumerate(pages)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            result = future.result()
            results[i] = result

            if result["error"]:
                print(f"  [!] {result['title']}: {result['error']}")
            else:
                print(f"  ✓ {result['title']} ({len(result['text'])} chars)")

    return results
