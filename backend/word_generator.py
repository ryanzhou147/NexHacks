import httpx
import json
import re
import asyncio
import time
from config import (
    MODEL,
    OLLAMA_BASE_URL,
    DEFAULT_SENTENCE_STARTERS,
    DEFAULT_CONTINUATION_WORDS
)
from models import ChatMessage

WORD_COUNT = 15  # 15 words for 4x4 grid (1 slot reserved for refresh button)

class WordGenerator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache: list[str] = []
        self.cache_context: list[str] = []  # Track context for which cache was generated
        self.sentence_starters_cache: list[str] = DEFAULT_SENTENCE_STARTERS[:WORD_COUNT]  # Cache for sentence starters
        self.used_words: set[str] = set()  # Track words already shown
        self.is_generating_cache: bool = False
        self.pending_cache_task: asyncio.Task | None = None
        self.two_step_predictions: dict[str, list[str]] = {}
        self.tree_context: str | None = None
        self.level1_words: list[str] = []
        self.level2_words: dict[str, list[str]] = {}
        self.level2_excluded: dict[str, set[str]] = {}

    async def close(self):
        if self.pending_cache_task:
            self.pending_cache_task.cancel()
        await self.client.aclose()

    def clear_used_words(self):
        """Clear used words when starting a new sentence."""
        self.used_words.clear()

    def _build_context(self, chat_history: list[ChatMessage], current_sentence: list[str]) -> str:
        """Build context string from chat history and current sentence."""
        context_parts = []

        if chat_history:
            context_parts.append("Previous conversation:")
            for msg in chat_history[-10:]:  # Last 10 messages for context
                speaker = "User" if msg.is_user else "Assistant"
                context_parts.append(f"{speaker}: {msg.text}")

        if current_sentence:
            context_parts.append(f"\nCurrent sentence being built: {' '.join(current_sentence)}")

        return "\n".join(context_parts)

    async def _call_openrouter(self, prompt: str, exclude_words: set[str] | None = None) -> list[str]:
        """Call local Ollama server with Qwen2.5 1.5B."""
        exclude_list = ""
        if exclude_words:
            exclude_list = f"\n\nIMPORTANT: Do NOT include any of these words (already used): {', '.join(list(exclude_words)[:50])}"

        try:
            response = await self.client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": f"""You are a word prediction assistant for an AAC (Augmentative and Alternative Communication) device.
Your task is to predict the most likely next words a user might want to say.
Always respond with ONLY a JSON array of exactly {WORD_COUNT} single words, ordered from most likely to least likely.
Words should be common, useful for daily communication, and contextually appropriate.
Include a mix of: verbs, nouns, adjectives, pronouns, and common phrases.
Some words should end with punctuation (. ! ?) to allow sentence completion.
Do not include any explanation, just the JSON array.{exclude_list}

Context:
{prompt}
""",
                    "options": {
                        "num_predict": 128,
                        "top_k": 15
                    },
                    "stream": False
                }
            )

            if response.status_code != 200:
                print(f"Ollama error: {response.status_code} - {response.text}")
                return []

            data = response.json()
            content = data.get("response", "")

            # Parse JSON array from response
            match = re.search(r'\[.*?\]', content, re.DOTALL)
            if match:
                words = json.loads(match.group())
                # Filter out excluded words and ensure WORD_COUNT
                words = [str(w).strip() for w in words if w and str(w).strip().lower() not in (exclude_words or set())]
                return words[:WORD_COUNT]

            return []

        except Exception as e:
            print(f"Error calling OpenRouter: {e}")
            return []

    def _filter_used_words(self, words: list[str]) -> list[str]:
        return [w for w in words if w.lower() not in self.used_words]

    def _pad_words(self, words: list[str], is_sentence_start: bool, exclude: set[str] | None = None) -> list[str]:
        exclude = exclude or set()

        seen = set(exclude)
        unique_words = []
        for w in words:
            w_lower = w.lower()
            if w_lower not in seen:
                seen.add(w_lower)
                unique_words.append(w)

        while len(unique_words) < WORD_COUNT:
            unique_words.append("")

        return unique_words[:WORD_COUNT]

    async def generate_two_step_predictions(
        self,
        chat_history: list[ChatMessage],
        current_sentence: list[str],
        is_sentence_start: bool,
        first_words: list[str]
    ) -> tuple[dict[str, list[str]], int]:
        if not first_words:
            self.two_step_predictions = {}
            return {}, 0

        self.two_step_predictions = {}
        return {}, 0

    async def reset_two_step_branch(
        self,
        chat_history: list[ChatMessage],
        current_sentence: list[str],
        is_sentence_start: bool,
        first_word: str
    ) -> list[str]:
        extended_sentence = current_sentence + [first_word]
        context = self._build_context(chat_history, extended_sentence)
        prompt = f"""Based on this context, predict the {WORD_COUNT} most likely NEXT words to continue the sentence.
The user is building a sentence word by word. Predict what comes next.
Include some words with ending punctuation (. ! ?) for sentence completion.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

        previous = self.two_step_predictions.get(first_word, [])
        base_exclude = self.used_words | {first_word.lower()}
        exclude = base_exclude | {w.lower() for w in previous}

        words = await self._call_openrouter(prompt, exclude)
        if not words:
            words = []

        next_words = self._pad_words(words, False, exclude)

        self.two_step_predictions[first_word] = next_words
        if first_word not in self.level2_excluded:
            self.level2_excluded[first_word] = set(previous)
        self.level2_excluded[first_word].update(next_words)

        self.tree_context = context
        if not self.level1_words:
            self.level1_words = list(self.two_step_predictions.keys())
        self.level2_words[first_word] = next_words

        return next_words

    async def generate_initial_words(
        self,
        chat_history: list[ChatMessage],
        current_sentence: list[str],
        is_sentence_start: bool
    ) -> tuple[list[str], list[str], int]:
        if is_sentence_start:
            self.clear_used_words()

        context = self._build_context(chat_history, current_sentence)

        start_time = time.perf_counter()

        if is_sentence_start:
            prompt = f"""Based on this conversation context, predict the {WORD_COUNT} most likely words to START a new sentence.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

            display_words = await self._call_openrouter(prompt, self.used_words)
        else:
            prompt = f"""Based on this context, predict the {WORD_COUNT} most likely NEXT words to continue the sentence.
The user is building a sentence word by word. Predict what comes next.
Include some words with ending punctuation (. ! ?) for sentence completion.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

            display_words = await self._call_openrouter(prompt, self.used_words)

        display_words = self._pad_words(display_words, is_sentence_start, self.used_words)

        cache_words: list[str] = []

        for w in display_words:
            self.used_words.add(w.lower())

        self.cache = cache_words
        self.cache_context = list(current_sentence)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return display_words, cache_words, duration_ms

    def _get_alternative_starters(self, exclude: set[str]) -> list[str]:
        """Get alternative sentence starters not in exclude set."""
        alternatives = [
            "Actually", "Maybe", "Perhaps", "Well", "So",
            "Now", "Then", "First", "Also", "But",
            "However", "Although", "Because", "Since", "If",
            "After", "Before", "While", "Until", "Unless",
            "Could", "Should", "Must", "Might", "May"
        ]
        result = [w for w in alternatives if w.lower() not in exclude]
        return result[:WORD_COUNT]

    async def get_refresh_words(
        self,
        chat_history: list[ChatMessage],
        current_sentence: list[str],
        is_sentence_start: bool
    ) -> tuple[list[str], list[str]]:
        display_words, _, _ = await self.generate_initial_words(
            chat_history,
            current_sentence,
            is_sentence_start
        )
        return display_words, []

    async def generate_cache_background(
        self,
        chat_history: list[ChatMessage],
        current_sentence: list[str],
        is_sentence_start: bool
    ) -> list[str]:
        if self.is_generating_cache:
            return self.cache

        self.is_generating_cache = True
        try:
            context = self._build_context(chat_history, current_sentence)

            if is_sentence_start:
                prompt = f"""Based on this conversation context, predict {WORD_COUNT} alternative words to start a new sentence.
These should be less common but still useful sentence starters.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""
            else:
                prompt = f"""Based on this context, predict {WORD_COUNT} alternative next words to continue the sentence.
These should be less common but contextually appropriate alternatives.
Include some words with ending punctuation (. ! ?) for sentence completion.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

            cache_words = await self._call_openrouter(prompt, self.used_words)
            cache_words = self._pad_words(cache_words, is_sentence_start, self.used_words)
            self.cache = cache_words
            self.cache_context = list(current_sentence)
            return cache_words
        finally:
            self.is_generating_cache = False

    def get_cached_words(self) -> list[str]:
        return self.cache

    def get_used_words(self) -> list[str]:
        """Return list of used words."""
        return list(self.used_words)


# Global instance
word_generator = WordGenerator()
