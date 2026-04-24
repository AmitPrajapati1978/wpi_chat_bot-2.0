import anthropic
from dotenv import load_dotenv

load_dotenv()

REWRITER_PROMPT = """You are a query rewriter for a WPI university chatbot.

Given a conversation history and a new user message, rewrite the new message as a complete, standalone question that includes all necessary context from the history.

Rules:
- If the new message is already a complete standalone question about WPI, return it as-is
- If the new message references something from history (e.g. "what about fees?", "tell me more", "what about the first one?"), rewrite it to be fully self-contained
- Keep it concise — one clear question
- Return ONLY the rewritten question, nothing else"""


def rewrite_query(history: list[dict], new_message: str) -> str:
    """
    Takes conversation history and a new user message,
    returns a standalone contextualized query.
    If no history, returns the message as-is.
    """
    if not history:
        return new_message

    client = anthropic.Anthropic()

    history_text = ""
    for msg in history[-6:]:  # last 3 turns
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content'][:300]}\n"

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        system=REWRITER_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Conversation history:\n{history_text}\nNew message: {new_message}\n\nRewrite as a standalone question:"
        }],
    )

    return response.content[0].text.strip()
