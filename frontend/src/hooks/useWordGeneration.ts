import { useEffect, useCallback } from 'react'
import { useGridStore } from '../stores/useGridStore'
import { useChatStore } from '../stores/useChatStore'
import { checkHealth, refreshWords, ChatMessage as ApiChatMessage } from '../api/wordApi'

export function useWordGeneration() {
  const fetchNewWords = useGridStore((state) => state.fetchNewWords)
  const setWords = useGridStore((state) => state.setWords)
  const setWordsFromLookahead = useGridStore((state) => state.setWordsFromLookahead)
  const setLookahead = useGridStore((state) => state.setLookahead)
  const setGenerationTime = useGridStore((state) => state.setGenerationTime)
  const setBackendConnected = useGridStore((state) => state.setBackendConnected)
  const resetToSentenceStarters = useGridStore((state) => state.resetToSentenceStarters)
  const isBackendConnected = useGridStore((state) => state.isBackendConnected)
  const mode = useGridStore((state) => state.mode)
  const cachedWords = useGridStore((state) => state.cachedWords)

  const messages = useChatStore((state) => state.messages)
  const currentSentence = useChatStore((state) => state.currentSentence)

  useEffect(() => {
    const checkBackend = async () => {
      const healthy = await checkHealth()
      setBackendConnected(healthy)

      if (healthy) {
        const chatHistory = messages.map(msg => ({
          text: msg.text,
          isUser: msg.isUser
        }))
        fetchNewWords(chatHistory, currentSentence, mode === 'sentence-start')
      }
    }

    checkBackend()

    const interval = setInterval(checkBackend, 30000)
    return () => clearInterval(interval)
  }, [])

  const onSentenceComplete = useCallback(async () => {
    // Immediately show sentence starters
    resetToSentenceStarters()

    if (!isBackendConnected) return

    const chatHistory = messages.map(msg => ({
      text: msg.text,
      isUser: msg.isUser
    }))

    // Fetch updated predictions in background (though likely same as default)
    await fetchNewWords(chatHistory, [], true)
  }, [isBackendConnected, messages, fetchNewWords, resetToSentenceStarters])

  const onWordSelected = useCallback(async (word: string) => {
    if (!isBackendConnected) return

    const chatHistory = messages.map(msg => ({
      text: msg.text,
      isUser: msg.isUser
    }))

    const newSentence = [...currentSentence, word]
    const isSentenceEnd = /[.!?]$/.test(word)

    if (!isSentenceEnd) {
      await fetchNewWords(chatHistory, newSentence, false)
    }
  }, [isBackendConnected, messages, currentSentence, fetchNewWords])

  const onRefresh = useCallback(async () => {
    if (!isBackendConnected) return

    try {
      const chatHistory = messages.map(msg => ({
        text: msg.text,
        isUser: msg.isUser
      }))

      const apiChatHistory: ApiChatMessage[] = chatHistory.map(msg => ({
        text: msg.text,
        is_user: msg.isUser
      }))

      const response = await refreshWords({
        chat_history: apiChatHistory,
        current_sentence: currentSentence,
        is_sentence_start: currentSentence.length === 0
      })

      setWords(response.words, response.cached_words)
      setLookahead(response.two_step_predictions || {})
      setGenerationTime(response.two_step_time_ms || null)
    } catch (error) {
      console.error('Failed to refresh words:', error)
    }
  }, [isBackendConnected, messages, currentSentence, cachedWords, setWords, setLookahead, setGenerationTime])

  return {
    onSentenceComplete,
    onWordSelected,
    onRefresh,
    isBackendConnected
  }
}
