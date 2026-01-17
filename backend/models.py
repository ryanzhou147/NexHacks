from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    text: str
    is_user: bool

class WordRequest(BaseModel):
    chat_history: list[ChatMessage] = []
    current_sentence: list[str] = []
    is_sentence_start: bool = True

class WordResponse(BaseModel):
    words: list[str]
    cached_words: list[str]
    two_step_predictions: dict[str, list[str]] | None = None
    two_step_time_ms: int | None = None

class RefreshRequest(BaseModel):
    chat_history: list[ChatMessage] = []
    current_sentence: list[str] = []
    is_sentence_start: bool = True

class ResetBranchRequest(BaseModel):
    chat_history: list[ChatMessage] = []
    current_sentence: list[str] = []
    is_sentence_start: bool = True
    first_word: str
