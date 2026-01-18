import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

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
