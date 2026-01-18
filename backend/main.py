from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from models import WordRequest, WordResponse, RefreshRequest, ResetBranchRequest
from word_generator import word_generator
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - initialize OpenRouter client
    print("Starting up - initializing OpenRouter client...")
    word_generator.load_model()
    print("OpenRouter client ready!")
    yield
    # Shutdown
    await word_generator.close()

app = FastAPI(
    title="Jaw-Clench Word Generator API",
    description="Backend API for generating contextual word predictions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Jaw-Clench Word Generator API", "status": "running"}

@app.post("/api/words", response_model=WordResponse)
async def get_words(request: WordRequest):
    """
    Generate 24 contextual words based on chat history and current sentence.
    Returns both display words and cached words (different sets, no duplicates).
    Words are ordered by likelihood (index 0 = most likely).
    """
    try:
        display_words, cached_words, duration_ms = await word_generator.generate_initial_words(
            chat_history=request.chat_history,
            current_sentence=request.current_sentence,
            is_sentence_start=request.is_sentence_start
        )
        return WordResponse(
            words=display_words, 
            cached_words=cached_words, 
            two_step_time_ms=duration_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh", response_model=WordResponse)
async def refresh_words(request: RefreshRequest, background_tasks: BackgroundTasks):
    """
    Generate new words excluding previously shown words in this layer.
    Each refresh shows completely different words until a word is selected.
    """
    try:
        display_words, _, duration_ms = await word_generator.generate_initial_words(
            chat_history=request.chat_history,
            current_sentence=request.current_sentence,
            is_sentence_start=request.is_sentence_start,
            is_refresh=True  # Don't clear tracking, just add to exclusions
        )

        return WordResponse(
            words=display_words,
            cached_words=[],
            two_step_time_ms=duration_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-cache")
async def generate_cache(request: WordRequest):
    """
    Generate new cache in background. Called by frontend while user navigates.
    """
    try:
        cache_words = await word_generator.generate_cache_background(
            chat_history=request.chat_history,
            current_sentence=request.current_sentence,
            is_sentence_start=request.is_sentence_start
        )
        return {"cached_words": cache_words, "status": "generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache")
async def get_cache():
    """Get current cached words without regenerating."""
    return {
        "cached_words": word_generator.get_cached_words(),
        "used_words": word_generator.get_used_words()
    }

@app.post("/api/clear-used")
async def clear_used_words():
    """Clear used words tracking (called when starting new sentence)."""
    word_generator.clear_used_words()
    return {"status": "cleared"}

@app.post("/api/reset-branch")
async def reset_branch(request: ResetBranchRequest):
    try:
        words = await word_generator.reset_two_step_branch(
            chat_history=request.chat_history,
            current_sentence=request.current_sentence,
            is_sentence_start=request.is_sentence_start,
            first_word=request.first_word
        )
        return {"words": words}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": word_generator.is_loaded
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
