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
MAX_CHARS = 4000  # slightly larger than before since S3 content is already clean

_s3_client = None


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

    source_url = meta.get("source_url", "")
    title = meta.get("title", key.split("/")[-1].replace("_", " ").rsplit(".", 1)[0])

    text = body
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [content trimmed]"

    return {
        "url": source_url if source_url else key,
        "title": title,
        "text": text,
        "error": None,
    }


def _parse_csv(key: str, raw: str) -> dict:
    """
    Parse a CSV file into readable text.
    Strips HTML from body fields and formats each row as key: value pairs.
    """
    title = key.split("/")[-1].replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()

    try:
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
    except Exception as e:
        return {"url": key, "title": title, "text": raw[:MAX_CHARS], "error": str(e)}

    if not rows:
        return {"url": key, "title": title, "text": "No data found.", "error": None}

    # Fields to skip (internal Drupal IDs, timestamps, irrelevant metadata)
    skip_fields = {
        "nid", "uid", "created", "changed", "status",
        "field_image_target_id", "field_tags_target_id",
        "field_announcements_checkbox_value", "field_events_checkbox_value",
        "field_exclude_value", "field_full_bleed_value",
        "field_media_coverage_checkbox_value", "field_news_widget_value",
        "field_number_of_announcements_value", "field_number_of_articles_value",
        "field_number_of_events_value", "field_published_at__value",
        "field_two_columns_checkbox_value", "field_two_columns_events_value",
    }

    # HTML fields to strip tags from
    html_fields = {"body_value", "field_description_value", "field_body_value"}

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
    """Parse a JSON file (e.g. course catalog) into readable text."""
    title = key.split("/")[-1].replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title()

    try:
        data = json.loads(raw)
    except Exception as e:
        return {"url": key, "title": title, "text": raw[:MAX_CHARS], "error": str(e)}

    # Course catalog JSON: list of course objects
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
    elif isinstance(data, dict):
        text = json.dumps(data, indent=2)
    else:
        text = str(data)

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... [content trimmed]"

    return {"url": key, "title": title, "text": text, "error": None}


def fetch_page_s3(item: dict) -> dict:
    """
    Read one file from S3 and return {url, title, text, error}.
    item must have a 'key' field with the S3 object key.
    """
    key = item.get("key") or item.get("url", "")

    try:
        response = get_s3().get_object(Bucket=BUCKET, Key=key)
        raw = response["Body"].read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"url": key, "title": key.split("/")[-1], "text": "", "error": str(e)}

    if key.endswith(".md"):
        return _parse_markdown(key, raw)
    elif key.endswith(".csv"):
        return _parse_csv(key, raw)
    elif key.endswith(".json"):
        return _parse_json(key, raw)
    else:
        # Plain text fallback
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
