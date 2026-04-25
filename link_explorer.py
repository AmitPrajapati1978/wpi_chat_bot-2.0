import json
import os
import boto3
import anthropic
from dotenv import load_dotenv

load_dotenv()

BUCKET = "wpi-knowledge"

# File extensions treated as direct files (not folder prefixes)
DIRECT_FILE_EXTENSIONS = (".csv", ".json", ".md", ".txt")

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


def list_prefix_files(prefix: str) -> list[dict]:
    """
    List all files in an S3 prefix (non-recursive first level).
    Returns [{key, name}] for each real file found.
    """
    s3 = get_s3()
    results = []
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            name = key.split("/")[-1]
            # Skip directories, hidden files, and empty placeholder files
            if not name or name.startswith(".") or obj["Size"] == 0:
                continue
            results.append({"key": key, "name": name})

    return results


def rank_files_by_name(question: str, files: list[dict], top_n: int) -> list[dict]:
    """
    One Claude Haiku call to pick the most relevant files by their names.
    Returns top_n items from the input list.
    """
    if not files:
        return []

    client = anthropic.Anthropic()
    candidates = files[:150]  # cap prompt size

    file_list = "\n".join(
        f"{i + 1}. {item['name']}"
        for i, item in enumerate(candidates)
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system="""You are a knowledge retrieval assistant for WPI's data.
Given a user question and a list of filenames, select the most relevant files likely to answer it.
Return ONLY a JSON array of file numbers (1-based integers), most relevant first.
Example: [3, 7, 12]""",
        messages=[{
            "role": "user",
            "content": f"""User question: {question}

Available files:
{file_list}

Return a JSON array of the top {top_n} most relevant file numbers."""
        }],
    )

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.find("]", start)
    if start == -1 or end == -1:
        return candidates[:top_n]

    indices = json.loads(raw[start:end + 1])
    selected = []
    for idx in indices:
        if 1 <= idx <= len(candidates):
            selected.append(candidates[idx - 1])

    return selected[:top_n]


def explore(question: str, start_refs: list[str], max_depth: int = 3, top_n: int = 3) -> list[dict]:
    """
    For each S3 reference (folder prefix or direct file key):
      - If it's a direct file: include it as-is
      - If it's a folder with ≤ 8 files: include all files
      - If it's a folder with many files: ask Claude to pick the most relevant by filename

    Returns list of {url, text, key} for use by fetch_pages().
    url  = source URL (extracted later from file content, or S3 key as fallback)
    text = display name
    key  = S3 key to read
    """
    all_candidates = []

    for ref in start_refs:
        if ref.endswith(DIRECT_FILE_EXTENSIONS):
            # Single file — include directly
            name = ref.split("/")[-1]
            all_candidates.append({"key": ref, "name": name})
        else:
            # Folder — list files and rank
            files = list_prefix_files(ref)
            if not files:
                continue

            if len(files) <= 8:
                all_candidates.extend(files)
            else:
                picked = rank_files_by_name(question, files, top_n=top_n * 2)
                all_candidates.extend(picked)

    if not all_candidates:
        return []

    # Deduplicate by key
    seen = {}
    for item in all_candidates:
        seen[item["key"]] = item
    unique = list(seen.values())

    # Final ranking across everything if we have more than we need
    if len(unique) > top_n:
        final = rank_files_by_name(question, unique, top_n=top_n)
    else:
        final = unique

    # Shape output to match the interface fetch_pages() + app.py expect:
    # {url, text, key}
    return [
        {
            "url": item["key"],   # will be replaced with source_url after fetch
            "text": item["name"].replace("_", " ").replace("-", " ").rsplit(".", 1)[0],
            "key": item["key"],
        }
        for item in final
    ]


if __name__ == "__main__":
    from section_selector import select_sections

    print("WPI S3 Explorer — type a question, Ctrl+C to quit\n")
    while True:
        try:
            question = input("Your question: ").strip()
            if not question:
                continue

            print("\n--- Step 1: Selecting top categories ---")
            sections = select_sections(question)
            for i, s in enumerate(sections, 1):
                print(f"  {i}. [{s['section_key']}] {s['url']}")

            print("\n--- Step 2: Finding relevant files ---")
            pages = explore(question, [s["url"] for s in sections])

            print(f"\n  Top {len(pages)} files:")
            for i, p in enumerate(pages, 1):
                print(f"  {i}. {p['text']}")
                print(f"     {p['key']}")
            print()

        except KeyboardInterrupt:
            print("\nBye!")
            break
