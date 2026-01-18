import json
import re
import asyncio
import time
import traceback
import httpx
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    DEFAULT_SENTENCE_STARTERS,
    DEFAULT_CONTINUATION_WORDS
)
from models import ChatMessage

WORD_COUNT = 15  # 15 words for 4x4 grid (1 slot reserved for refresh button)

# Extended fallback words to ensure grid is always filled (200+ words each)
EXTENDED_STARTERS = [
    "I", "The", "What", "How", "Can", "Please", "Thank", "Yes", "No", "Hello",
    "Actually", "Maybe", "Perhaps", "Well", "So", "Now", "Then", "First", "Also", "But",
    "However", "Although", "Because", "Since", "If", "After", "Before", "While", "Until", "Unless",
    "Could", "Should", "Must", "Might", "May", "Would", "Will", "Do", "Does", "Did",
    "Let", "Help", "Want", "Need", "Like", "Think", "Know", "See", "Go", "Come",
    "Hey", "Hi", "Good", "Great", "Sure", "Okay", "Right", "Today", "Tomorrow", "Yesterday",
    "Here", "There", "Never", "Always", "Sometimes", "Often", "Usually", "Probably", "Certainly", "Definitely",
    "Absolutely", "Basically", "Honestly", "Seriously", "Obviously", "Clearly", "Simply", "Really", "Very", "Just",
    "Which", "Where", "When", "Why", "Whose", "Whom", "That", "These", "Those", "Such",
    "Each", "Every", "Any", "Some", "Most", "Many", "Few", "Several", "Both", "All",
    "Neither", "Either", "Another", "Other", "One", "Two", "Three", "Four", "Five", "Six",
    "Someone", "Somebody", "Anyone", "Anybody", "Everyone", "Everybody", "Nobody", "Nothing", "Something", "Everything",
    "Anywhere", "Somewhere", "Everywhere", "Nowhere", "Somehow", "Anyhow", "Anyway", "Meanwhile", "Therefore", "Furthermore",
    "Moreover", "Nevertheless", "Nonetheless", "Otherwise", "Instead", "Besides", "Hence", "Thus", "Still", "Yet",
    "Again", "Almost", "Already", "Soon", "Later", "Early", "Late", "Long", "Short", "Quick",
    "Slow", "Fast", "Hard", "Soft", "Loud", "Quiet", "Bright", "Dark", "Hot", "Cold",
    "New", "Old", "Young", "Big", "Small", "Large", "Tiny", "Huge", "Tall", "Wide",
    "Excuse", "Sorry", "Pardon", "Thanks", "Bye", "Welcome", "Congrats", "Wow", "Oops", "Uh"
]

EXTENDED_CONTINUATIONS = [
    "the", "a", "to", "and", "is", "it", "that", "for", "you", "with",
    "this", "be", "have", "from", "or", "was", "are", "but", "not", "what",
    "all", "can", "had", "her", "there", "been", "if", "more", "when", "will",
    "very", "just", "about", "into", "some", "could", "them", "other", "than", "then",
    "now", "look", "only", "come", "over", "such", "make", "like", "back", "most",
    "good.", "great.", "well.", "now.", "here.", "there.", "today.", "soon.", "please.", "thanks.",
    "really", "also", "still", "even", "much", "many", "any", "each", "every", "both",
    "few", "more", "most", "own", "same", "so", "too", "up", "down", "out",
    "in", "on", "off", "over", "under", "again", "further", "once", "here", "there",
    "where", "why", "how", "all", "both", "each", "few", "more", "most", "other",
    "sure.", "right.", "okay.", "yes.", "no.", "maybe.", "probably.", "definitely.", "absolutely.", "certainly.",
    "always", "never", "sometimes", "often", "usually", "already", "yet", "still", "just", "only",
    "me", "him", "her", "us", "them", "my", "your", "his", "its", "our",
    "their", "myself", "yourself", "himself", "herself", "itself", "ourselves", "themselves", "one", "two",
    "first", "second", "last", "next", "new", "old", "good", "bad", "great", "best",
    "better", "worse", "worst", "same", "different", "important", "possible", "able", "available", "free",
    "full", "empty", "open", "closed", "easy", "hard", "simple", "complex", "clear", "sure",
    "ready", "done", "finished", "complete", "perfect", "fine", "nice", "happy", "sad", "angry",
    "tired", "hungry", "thirsty", "sick", "healthy", "safe", "sorry", "glad", "proud", "afraid",
    "excited.", "amazing.", "wonderful.", "terrible.", "horrible.", "beautiful.", "awesome.", "fantastic.", "excellent.", "perfect."
]

class WordGenerator:
    def __init__(self):
        self.is_loaded = False
        self.http_client: httpx.AsyncClient | None = None

        self.word_cache: list[str] = []
        self.cache_context: list[str] = []
        self.sentence_starters_cache: list[str] = DEFAULT_SENTENCE_STARTERS[:WORD_COUNT]
        self.used_words: set[str] = set()  # Words used in the current sentence (cleared on sentence complete)
        self.refresh_excluded: set[str] = set()  # Words shown in current layer (cleared on word selection, not refresh)
        self.is_generating_cache: bool = False
        self.pending_cache_task: asyncio.Task | None = None
        self.two_step_predictions: dict[str, list[str]] = {}
        self.tree_context: str | None = None
        self.level1_words: list[str] = []
        self.level2_words: dict[str, list[str]] = {}
        self.level2_excluded: dict[str, set[str]] = {}

    def load_model(self):
        """Initialize the HTTP client for OpenRouter API calls."""
        if self.is_loaded:
            return

        print(f"Initializing OpenRouter client with model: {OPENROUTER_MODEL}")
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.is_loaded = True
        print("OpenRouter client ready!")

    async def close(self):
        if self.pending_cache_task:
            self.pending_cache_task.cancel()
        if self.http_client:
            await self.http_client.aclose()

    def clear_used_words(self):
        """Clear used words when starting a new sentence."""
        self.used_words.clear()
        self.refresh_excluded.clear()

    def clear_refresh_excluded(self):
        """Clear refresh exclusions when user selects a word (new layer)."""
        self.refresh_excluded.clear()

    def _build_context(self, chat_history: list[ChatMessage], current_sentence: list[str]) -> str:
        """Build context string from chat history and current sentence."""
        context_parts = []

        if chat_history:
            context_parts.append("Previous conversation:")
            for msg in chat_history[-10:]:
                speaker = "User" if msg.is_user else "Assistant"
                context_parts.append(f"{speaker}: {msg.text}")

        if current_sentence:
            context_parts.append(f"\nCurrent sentence being built: {' '.join(current_sentence)}")

        return "\n".join(context_parts)

    async def _generate_words(self, prompt: str, exclude_words: set[str] | None = None, retry_count: int = 0) -> list[str]:
        """Generate words using OpenRouter API with Gemini Flash. Retries if fewer than 15 words returned."""
        if not self.is_loaded or not self.http_client:
            print("Client not initialized!")
            return []

        exclude_words = exclude_words or set()
        exclude_list = ""
        if exclude_words:
            exclude_list = f"\n\nIMPORTANT: Do NOT include any of these words (already used): {', '.join(list(exclude_words)[:50])}"

        context_snippet = prompt[-1024:]

        full_prompt = f"""You are an AAC word prediction assistant.
You MUST respond with ONLY a JSON array of EXACTLY {WORD_COUNT} single words, in order of likelihood.
Some words should end with punctuation (. ! ?) to allow sentence completion.
No explanations, no markdown, just the raw JSON array with exactly {WORD_COUNT} words.{exclude_list}

Context:
{context_snippet}

Response (JSON array of exactly {WORD_COUNT} words):"""

        try:
            response = await self.http_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "user", "content": full_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 250,  # Increased to ensure full 15-word JSON array
                }
            )

            response.raise_for_status()
            data = response.json()

            output = data["choices"][0]["message"]["content"]
            print(f"OpenRouter raw response: {output}")

            # Parse JSON array from response
            match = re.search(r'\[.*?\]', output, re.DOTALL)
            if match:
                words = json.loads(match.group())
                # Filter out excluded words and empty strings
                words = [str(w).strip() for w in words if w and str(w).strip() and str(w).strip().lower() not in exclude_words]
                print(f"Parsed {len(words)} words after filtering: {words}")

                # If we got fewer than WORD_COUNT words and haven't retried too many times, retry
                if len(words) < WORD_COUNT and retry_count < 2:
                    print(f"Only got {len(words)} words, retrying (attempt {retry_count + 1})...")
                    # Add current words to exclusion to get different ones
                    new_exclude = exclude_words | {w.lower().rstrip('.!?') for w in words}
                    more_words = await self._generate_words(prompt, new_exclude, retry_count + 1)
                    words.extend(more_words)
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_words = []
                    for w in words:
                        w_lower = w.lower().rstrip('.!?')
                        if w_lower not in seen and w_lower not in exclude_words:
                            seen.add(w_lower)
                            unique_words.append(w)
                    return unique_words[:WORD_COUNT]

                return words[:WORD_COUNT]

            print("No JSON array found in response")
            return []

        except Exception as e:
            print(f"Error generating words: {repr(e)}")
            traceback.print_exc()
            return []

    def _filter_used_words(self, words: list[str]) -> list[str]:
        return [w for w in words if w.lower() not in self.used_words]

    def _pad_words(self, words: list[str], is_sentence_start: bool, exclude: set[str] | None = None) -> list[str]:
        """Pad word list to WORD_COUNT, GUARANTEEING exactly 15 words are returned."""
        return self._pad_words_relaxed(words, is_sentence_start, exclude)

    def _pad_words_relaxed(self, words: list[str], is_sentence_start: bool, exclude: set[str] | None = None) -> list[str]:
        """RELAXED padding - GUARANTEES exactly 15 words, allowing reuse if absolutely needed."""
        exclude = exclude or set()

        # First pass: add unique words not in exclude
        seen = set()
        unique_words = []
        for w in words:
            if not w or not w.strip():
                continue
            w_lower = w.lower().rstrip('.!?')
            if w_lower not in seen and w_lower not in exclude:
                seen.add(w_lower)
                unique_words.append(w)

        print(f"After first pass (excluding {len(exclude)} words): {len(unique_words)} words")

        # Second pass: add from fallback lists (not in seen, not in exclude)
        if is_sentence_start:
            fallback_sources = [DEFAULT_SENTENCE_STARTERS, EXTENDED_STARTERS]
        else:
            fallback_sources = [DEFAULT_CONTINUATION_WORDS, EXTENDED_CONTINUATIONS]

        for fallback_source in fallback_sources:
            if len(unique_words) >= WORD_COUNT:
                break
            for w in fallback_source:
                w_lower = w.lower().rstrip('.!?')
                if w_lower not in seen and w_lower not in exclude:
                    seen.add(w_lower)
                    unique_words.append(w)
                if len(unique_words) >= WORD_COUNT:
                    break

        print(f"After fallback lists: {len(unique_words)} words")

        # Third pass: If STILL not enough, ALLOW words from exclude (reuse previous words)
        if len(unique_words) < WORD_COUNT:
            print(f"Still need {WORD_COUNT - len(unique_words)} more words, allowing reuse...")
            for fallback_source in fallback_sources:
                if len(unique_words) >= WORD_COUNT:
                    break
                for w in fallback_source:
                    w_lower = w.lower().rstrip('.!?')
                    if w_lower not in seen:  # Only check seen, NOT exclude
                        seen.add(w_lower)
                        unique_words.append(w)
                    if len(unique_words) >= WORD_COUNT:
                        break

        # Fourth pass: Add punctuation variants if still needed
        if len(unique_words) < WORD_COUNT:
            print(f"Adding punctuation variants...")
            punctuation_words = ["yes.", "no.", "okay.", "sure.", "thanks.", "please.", "help.",
                                "good.", "great.", "fine.", "right.", "now.", "here.", "there.",
                                "yes!", "no!", "help!", "please!", "thanks!", "great!", "wow!",
                                "yes?", "no?", "really?", "okay?", "sure?", "right?", "now?"]
            for w in punctuation_words:
                w_lower = w.lower().rstrip('.!?')
                if w_lower not in seen:
                    seen.add(w_lower)
                    unique_words.append(w)
                if len(unique_words) >= WORD_COUNT:
                    break

        # ABSOLUTE FINAL: If somehow still not enough, duplicate with punctuation
        if len(unique_words) < WORD_COUNT:
            print(f"EMERGENCY: Adding duplicates with different punctuation...")
            base_words = ["more", "help", "yes", "no", "okay", "please", "thanks", "sure",
                         "right", "good", "fine", "well", "here", "there", "now"]
            punctuations = ["", ".", "!", "?"]
            for base in base_words:
                for punct in punctuations:
                    w = base + punct
                    if w not in [uw for uw in unique_words]:  # Check exact match
                        unique_words.append(w)
                    if len(unique_words) >= WORD_COUNT:
                        break
                if len(unique_words) >= WORD_COUNT:
                    break

        print(f"_pad_words_relaxed returning {len(unique_words)} words: {unique_words[:WORD_COUNT]}")
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

        words = await self._generate_words(prompt, exclude)
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
        is_sentence_start: bool,
        is_refresh: bool = False
    ) -> tuple[list[str], list[str], int]:
        print(f"\n=== generate_initial_words called ===")
        print(f"is_sentence_start={is_sentence_start}, is_refresh={is_refresh}")
        print(f"current_sentence={current_sentence}")
        print(f"used_words count: {len(self.used_words)}, refresh_excluded count: {len(self.refresh_excluded)}")

        # Only clear used_words when starting a genuinely new sentence (not on refresh)
        if is_sentence_start and not is_refresh:
            self.clear_used_words()

        # For non-refresh calls (word selection), clear refresh exclusions for new layer
        if not is_refresh:
            self.refresh_excluded.clear()

        context = self._build_context(chat_history, current_sentence)

        start_time = time.perf_counter()

        # LESS STRICT: Only use refresh_excluded for exclusion, limit its size
        # If refresh_excluded gets too large (more than 30 words), clear older ones
        if len(self.refresh_excluded) > 30:
            print(f"Clearing refresh_excluded (was {len(self.refresh_excluded)} words)")
            self.refresh_excluded.clear()

        # Only exclude words from current refresh cycle, not all used words
        exclude_set = set(self.refresh_excluded)  # Don't include used_words - allow reuse
        print(f"Total exclude_set size: {len(exclude_set)}")

        if is_sentence_start:
            prompt = f"""Based on this conversation context, predict the {WORD_COUNT} most likely words to START a new sentence.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

            display_words = await self._generate_words(prompt, exclude_set)
        else:
            prompt = f"""Based on this context, predict the {WORD_COUNT} most likely NEXT words to continue the sentence.
The user is building a sentence word by word. Predict what comes next.
Include some words with ending punctuation (. ! ?) for sentence completion.
Order from most likely (first) to least likely (last).

{context}

Respond with ONLY a JSON array of {WORD_COUNT} words."""

            display_words = await self._generate_words(prompt, exclude_set)

        print(f"Words from model (before padding): {len(display_words)} - {display_words}")

        # Use relaxed padding - allow previously used words if needed
        display_words = self._pad_words_relaxed(display_words, is_sentence_start, exclude_set)
        print(f"Words after padding: {len(display_words)} - {display_words}")

        # FINAL VALIDATION: Ensure we have exactly WORD_COUNT words
        if len(display_words) != WORD_COUNT:
            print(f"WARNING: Expected {WORD_COUNT} words but got {len(display_words)}")

        cache_words: list[str] = []

        # Only add to refresh_excluded (for this refresh cycle), not used_words
        for w in display_words:
            w_lower = w.lower().rstrip('.!?')
            self.refresh_excluded.add(w_lower)

        self.word_cache = cache_words
        self.cache_context = list(current_sentence)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        print(f"=== Returning {len(display_words)} words in {duration_ms}ms ===\n")
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
            return self.word_cache

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

            cache_words = await self._generate_words(prompt, self.used_words)
            cache_words = self._pad_words(cache_words, is_sentence_start, self.used_words)
            self.word_cache = cache_words
            self.cache_context = list(current_sentence)
            return cache_words
        finally:
            self.is_generating_cache = False

    def get_cached_words(self) -> list[str]:
        return self.word_cache

    def get_used_words(self) -> list[str]:
        """Return list of used words."""
        return list(self.used_words)


# Global instance
word_generator = WordGenerator()
