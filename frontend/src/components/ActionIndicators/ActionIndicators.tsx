import { useClenchStore } from '../../stores/useClenchStore'
import { IndicatorLight } from './IndicatorLight'
import styles from './ActionIndicators.module.css'

const INDICATORS = [
  { id: 0, label: '0 - Pause' },
  { id: 1, label: '1 - Right' },
  { id: 2, label: '2 - Down' },
  { id: 3, label: '3 - Select' }
]

interface ActionIndicatorsProps {
  isBackendConnected?: boolean
  generationTime?: number | null
}

export function ActionIndicators({ isBackendConnected, generationTime }: ActionIndicatorsProps) {
  const activeIndicator = useClenchStore((state) => state.activeIndicator)
  const isFading = useClenchStore((state) => state.isFading)

  return (
    <div className={styles.container}>
      <div className={styles.indicators}>
        {INDICATORS.map((indicator) => (
          <IndicatorLight
            key={indicator.id}
            label={indicator.label}
            isActive={activeIndicator === indicator.id}
            isFading={isFading && activeIndicator === indicator.id}
          />
        ))}
      </div>
      <div className={styles.status}>
        {generationTime && (
          <span className={styles.statusText} style={{ marginRight: '1rem', opacity: 0.7 }}>
            Lookahead: {generationTime}ms
          </span>
        )}
        <span className={`${styles.statusDot} ${isBackendConnected ? styles.connected : styles.disconnected}`} />
        <span className={styles.statusText}>
          {isBackendConnected ? 'AI Connected' : 'Offline'}
        </span>
      </div>
    </div>
  )
}
