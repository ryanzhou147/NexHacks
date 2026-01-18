import { useGridStore, REFRESH_BUTTON_INDEX, TOTAL_CELLS } from '../../stores/useGridStore'
import { useAutoSelect } from '../../hooks/useAutoSelect'
import { WordCell } from './WordCell'
import { RefreshCell } from './RefreshCell'
import styles from './WordGrid.module.css'

interface WordGridProps {
  onWordSelected?: (word: string) => void
  onRefresh?: () => void
}

export function WordGrid({ onWordSelected, onRefresh }: WordGridProps) {
  const words = useGridStore((state) => state.words)
  const cursorPosition = useGridStore((state) => state.cursorPosition)
  const mode = useGridStore((state) => state.mode)
  const isBackendConnected = useGridStore((state) => state.isBackendConnected)
  const isLoading = useGridStore((state) => state.isLoading)

  const { progress } = useAutoSelect({
    onSelect: onWordSelected,
    onRefresh: onRefresh
  })

  // Build grid cells: 24 words + 1 refresh button at index 4
  const renderCell = (gridIndex: number) => {
    // Calculate stagger delay based on grid position (row by row)
    const delay = `${gridIndex * 0.05}s`

    if (gridIndex === REFRESH_BUTTON_INDEX) {
      return (
        <RefreshCell
          key="refresh"
          isActive={cursorPosition === REFRESH_BUTTON_INDEX}
          progress={cursorPosition === REFRESH_BUTTON_INDEX ? progress : 0}
          isAnimating={isLoading}
          animationDelay={delay}
        />
      )
    }

    // Calculate word index (accounting for refresh button)
    const wordIndex = gridIndex > REFRESH_BUTTON_INDEX ? gridIndex - 1 : gridIndex
    const word = words[wordIndex] || ''

    return (
      <WordCell
        key={`${gridIndex}-${word}`}
        word={word}
        index={gridIndex}
        isActive={gridIndex === cursorPosition}
        progress={gridIndex === cursorPosition ? progress : 0}
        isAnimating={isLoading}
        animationDelay={delay}
      />
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.modeLabel}>
          {mode === 'sentence-start' ? 'Start your sentence' : 'Continue...'}
        </span>
        {!isBackendConnected && (
          <span className={styles.offline}>Offline mode</span>
        )}
      </div>
      <div className={styles.grid}>
        {Array.from({ length: TOTAL_CELLS }, (_, i) => renderCell(i))}
      </div>
    </div>
  )
}
