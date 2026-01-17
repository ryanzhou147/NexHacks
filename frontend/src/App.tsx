import { useEffect, useCallback } from 'react'
import { Layout } from './components/Layout'
import { WordGrid } from './components/WordGrid'
import { ChatPanel } from './components/ChatPanel'
import { ActionIndicators } from './components/ActionIndicators'
import { useKeyboardSimulation } from './hooks/useKeyboardSimulation'
import { useWordGeneration } from './hooks/useWordGeneration'
import { useGridStore } from './stores/useGridStore'
import { useChatStore } from './stores/useChatStore'
import { useClenchStore } from './stores/useClenchStore'

function App() {
  const { onWordSelected, onSentenceComplete, onRefresh, isBackendConnected } = useWordGeneration()

  const mode = useGridStore((state) => state.mode)
  const getCurrentWord = useGridStore((state) => state.getCurrentWord)
  const isOnRefreshButton = useGridStore((state) => state.isOnRefreshButton)
  const refreshGrid = useGridStore((state) => state.refreshGrid)
  const setMode = useGridStore((state) => state.setMode)
  const generationTime = useGridStore((state) => state.generationTime)

  const messages = useChatStore((state) => state.messages)
  const addWord = useChatStore((state) => state.addWord)

  // Handle manual selection (3 clenches)
  const handleManualSelect = useCallback(() => {
    if (isOnRefreshButton()) {
      refreshGrid()
      onRefresh()
      return
    }

    const word = getCurrentWord()
    if (!word) return

    const sentenceCompleted = addWord(word)

    if (sentenceCompleted) {
      setMode('sentence-start')
    } else {
      setMode('normal')
    }

    onWordSelected(word)
  }, [getCurrentWord, isOnRefreshButton, addWord, setMode, refreshGrid, onRefresh, onWordSelected])

  // Enable keyboard simulation for dev mode
  useKeyboardSimulation({
    enabled: true,
    onSelect: handleManualSelect
  })

  // Watch for mode changes to sentence-start (sentence completed)
  useEffect(() => {
    if (mode === 'sentence-start' && messages.length > 0) {
      onSentenceComplete()
    }
  }, [mode, messages.length, onSentenceComplete])

  return (
    <Layout
      devMode={true}
      leftPanel={
        <WordGrid
          onWordSelected={onWordSelected}
          onRefresh={onRefresh}
        />
      }
      rightPanel={<ChatPanel />}
      bottomBar={<ActionIndicators isBackendConnected={isBackendConnected} generationTime={generationTime} />}
    />
  )
}

export default App
