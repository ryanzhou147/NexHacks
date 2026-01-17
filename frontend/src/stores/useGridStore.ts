import { create } from 'zustand'
import { fetchWords, refreshWords, ChatMessage as ApiChatMessage } from '../api/wordApi'
import { sentenceStarters } from '../data/sentenceStarters'

type GridMode = 'normal' | 'sentence-start'

interface GridState {
  cursorPosition: number
  words: string[]
  cachedWords: string[]
  mode: GridMode
  isLoading: boolean
  isBackendConnected: boolean
  lookahead: Record<string, string[]>
  generationTime: number | null

  moveRight: () => void
  moveDown: () => void
  refreshGrid: () => void
  setMode: (mode: GridMode) => void
  getCurrentWord: () => string | null
  isOnRefreshButton: () => boolean
  setWords: (words: string[], cached?: string[]) => void
  setWordsFromLookahead: (word: string) => void
  setLookahead: (map: Record<string, string[]>) => void
  setGenerationTime: (ms: number | null) => void
  fetchNewWords: (
    chatHistory: Array<{ text: string; isUser: boolean }>,
    currentSentence: string[],
    isSentenceStart: boolean
  ) => Promise<void>
  setBackendConnected: (connected: boolean) => void
  resetToSentenceStarters: () => void
}

const GRID_SIZE = 4
const TOTAL_CELLS = GRID_SIZE * GRID_SIZE
const WORD_COUNT = 15
const REFRESH_BUTTON_INDEX = 3  // Top right corner in 4x4 grid

const DEFAULT_STARTERS = sentenceStarters.slice(0, WORD_COUNT)

export const useGridStore = create<GridState>((set, get) => ({
  cursorPosition: 0,
  words: new Array(WORD_COUNT).fill(''),
  cachedWords: new Array(WORD_COUNT).fill(''),
  mode: 'sentence-start',
  isLoading: false,
  isBackendConnected: false,
  lookahead: {},
  generationTime: null,

  moveRight: () => set((state) => {
    const col = state.cursorPosition % GRID_SIZE
    const row = Math.floor(state.cursorPosition / GRID_SIZE)
    const newCol = (col + 1) % GRID_SIZE
    return { cursorPosition: row * GRID_SIZE + newCol }
  }),

  moveDown: () => set((state) => {
    const row = Math.floor(state.cursorPosition / GRID_SIZE)
    const col = state.cursorPosition % GRID_SIZE
    const newRow = (row + 1) % GRID_SIZE
    return { cursorPosition: newRow * GRID_SIZE + col }
  }),

  refreshGrid: () => set({
    words: new Array(WORD_COUNT).fill(''),
    cursorPosition: 0
  }),

  setMode: (mode) => set({ mode }),

  getCurrentWord: () => {
    const state = get()
    if (state.cursorPosition === REFRESH_BUTTON_INDEX) {
      return null
    }
    const wordIndex = state.cursorPosition > REFRESH_BUTTON_INDEX
      ? state.cursorPosition - 1
      : state.cursorPosition
    return state.words[wordIndex] || ''
  },

  isOnRefreshButton: () => {
    return get().cursorPosition === REFRESH_BUTTON_INDEX
  },

  setWords: (words, cached) => set({
    words: words.slice(0, WORD_COUNT),
    cachedWords: cached ? cached.slice(0, WORD_COUNT) : get().cachedWords,
    cursorPosition: 0
  }),

  setWordsFromLookahead: (word) => {
    const state = get()
    const nextWords = state.lookahead[word]
    if (!nextWords || nextWords.length === 0) {
      return
    }
    set({
      words: nextWords.slice(0, WORD_COUNT),
      cachedWords: nextWords.slice(0, WORD_COUNT),
      cursorPosition: 0
    })
  },

  setLookahead: (map) => set({ lookahead: map }),

  setGenerationTime: (ms) => set({ generationTime: ms }),

  fetchNewWords: async (chatHistory, currentSentence, isSentenceStart) => {
    set({
      isLoading: true,
      words: new Array(WORD_COUNT).fill('')
    })

    try {
      const apiChatHistory: ApiChatMessage[] = chatHistory.map(msg => ({
        text: msg.text,
        is_user: msg.isUser
      }))

      const response = await fetchWords({
        chat_history: apiChatHistory,
        current_sentence: currentSentence,
        is_sentence_start: isSentenceStart
      })

      set({
        words: response.words.slice(0, WORD_COUNT),
        cachedWords: response.cached_words.slice(0, WORD_COUNT),
        lookahead: {},
        generationTime: response.two_step_time_ms || null,
        cursorPosition: 0,
        isLoading: false,
        isBackendConnected: true,
        mode: isSentenceStart ? 'sentence-start' : 'normal'
      })
    } catch (error) {
      console.error('Failed to fetch words from backend:', error)
      set({
        isLoading: false,
        isBackendConnected: false
      })
    }
  },

  setBackendConnected: (connected) => set({ isBackendConnected: connected }),

  resetToSentenceStarters: () => set({
    words: DEFAULT_STARTERS,
    cachedWords: DEFAULT_STARTERS, // Initial cache is same as starters
    cursorPosition: 0,
    mode: 'sentence-start',
    isLoading: false // Assume instant
  })
}))

export { REFRESH_BUTTON_INDEX, WORD_COUNT, GRID_SIZE, TOTAL_CELLS }
