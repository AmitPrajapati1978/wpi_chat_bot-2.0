from section_selector import select_sections
from link_explorer import explore
from page_fetcher import fetch_pages
from answer_generator import generate_answer


def ask_wpi(question: str) -> str:
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)

    # Step 1: Select top sections
    print("\n[Step 1] Identifying relevant sections...")
    sections = select_sections(question)
    for i, s in enumerate(sections, 1):
        print(f"  {i}. [{s['section_key']}] {s['url']}")

    # Step 2: Explore links
    print("\n[Step 2] Exploring website links...")
    start_urls = [s["url"] for s in sections]
    top_pages = explore(question, start_urls, max_depth=3, top_n=3)

    if not top_pages:
        return "Sorry, I couldn't find relevant pages on the WPI website."

    print(f"\n  Top {len(top_pages)} pages selected:")
    for i, p in enumerate(top_pages, 1):
        print(f"  {i}. {p['text']} — {p['url']}")

    # Step 3: Fetch page content
    print("\n[Step 3] Reading page content...")
    pages = fetch_pages(top_pages)

    # Step 4: Generate answer
    print("\n[Step 4] Generating answer...")
    answer = generate_answer(question, pages)

    return answer


if __name__ == "__main__":
    print("WPI AI Assistant — type a question, Ctrl+C to quit\n")
    while True:
        try:
            question = input("Your question: ").strip()
            if not question:
                continue
            answer = ask_wpi(question)
            print(f"\n{'='*60}")
            print("ANSWER:")
            print('='*60)
            print(answer)
            print()
        except KeyboardInterrupt:
            print("\nBye!")
            break
