import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = os.getenv("MODEL", "qwen2.5:1.5b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Default sentence starters (most common, ordered by frequency)
DEFAULT_SENTENCE_STARTERS = [
    "I", "The", "It", "You", "We",
    "This", "That", "My", "What", "How",
    "Can", "Do", "Is", "Are", "Would",
    "Please", "Yes", "No", "When", "Where",
    "Why", "Who", "Help", "Thank", "Sorry"
]

# Default continuation words
DEFAULT_CONTINUATION_WORDS = [
    "want", "need", "have", "feel", "think",
    "am", "is", "are", "was", "will",
    "can", "could", "would", "should", "might",
    "go", "come", "see", "know", "like",
    "good", "more", "help", "please", "now"
]
