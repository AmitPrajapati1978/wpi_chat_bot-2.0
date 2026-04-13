from groq import Groq
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a friendly, upbeat student advisor for Worcester Polytechnic Institute (WPI).

You have been given content retrieved directly from the WPI website to answer a student's question.

Rules:
- Answer based ONLY on the provided page content
- Be warm, conversational and engaging — like a helpful upperclassman, not a brochure
- Use emojis where they feel natural (don't overdo it)
- Use short bullet points for lists, bold for key names/places
- Keep it scannable — no long walls of text
- If specific details like names, locations, hours, or contacts are in the content, include them
- End with one helpful tip or encouragement
- If the content doesn't fully answer the question, say what you found and suggest where to look"""


def generate_answer(question: str, pages: list[dict]) -> str:
    """
    Given a question and fetched page contents, use Groq (free) to generate an answer.
    """
    client = Groq()

    context_parts = []
    for page in pages:
        if page["text"]:
            context_parts.append(
                f"--- Source: {page['title']} ---\nURL: {page['url']}\n\n{page['text']}"
            )

    if not context_parts:
        return "Sorry, I couldn't retrieve any content from the WPI website to answer your question."

    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""Question: {question}

Here is content retrieved from the WPI website:

{context}

Please answer the question based on this content."""}
        ],
    )

    return response.choices[0].message.content.strip()
