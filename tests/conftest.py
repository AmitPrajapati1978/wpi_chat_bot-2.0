import sys
from unittest.mock import MagicMock

# Stub out all heavy/external packages before any module under test is imported.
# This keeps CI fast — no model downloads, no real API calls.
for mod in [
    "anthropic",
    "dotenv",
    "sentence_transformers",
    "supabase",
    "boto3",
    "groq",
    "streamlit",
    "markdown",
]:
    sys.modules.setdefault(mod, MagicMock())
