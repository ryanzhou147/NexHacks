import { motion } from 'framer-motion'
import styles from './WordGrid.module.css'

interface RefreshCellProps {
  isActive: boolean
  progress?: number  // Unused now, kept for compatibility
  isAnimating?: boolean
  animationDelay?: string
}

export function RefreshCell({ isActive, isAnimating, animationDelay }: RefreshCellProps) {
  return (
    <motion.div
      className={`${styles.cell} ${styles.refreshCell} ${isActive ? styles.active : ''} ${isAnimating ? styles.cellAnimating : ''}`}
      style={{ animationDelay }}
      initial={false}
      animate={{
        scale: isActive ? 1.02 : 1,
        boxShadow: isActive
          ? '0 0 20px rgba(201, 183, 138, 0.4)'
          : '0 1px 2px rgba(0, 0, 0, 0.05)'
      }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
    >
      <motion.svg
        className={styles.refreshIcon}
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={isActive ? { rotate: 360 } : { rotate: 0 }}
        transition={{ duration: 0.8, ease: 'easeInOut', repeat: isActive ? Infinity : 0 }}
      >
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
        <path d="M3 3v5h5" />
        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
        <path d="M16 16h5v5" />
      </motion.svg>
    </motion.div>
  )
}
