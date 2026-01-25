import { useState, useCallback, useEffect, useRef } from 'react'
import { useLocalStorage } from './useLocalStorage'

interface UseResizableOptions {
  /** Direction of resize: 'horizontal' for width, 'vertical' for height */
  direction: 'horizontal' | 'vertical'
  /** Initial size in pixels */
  initialSize: number
  /** Minimum size constraint */
  minSize: number
  /** Maximum size constraint */
  maxSize: number
  /** LocalStorage key for persistence (optional) */
  storageKey?: string
  /** Which side the resize handle is on (determines drag direction) */
  handlePosition: 'left' | 'right' | 'top' | 'bottom'
}

interface UseResizableReturn {
  /** Current size in pixels */
  size: number
  /** Whether resize is happening */
  isResizing: boolean
  /** Start resize handler - attach to mouse down on handle */
  startResize: (e: React.MouseEvent) => void
  /** Reset to initial size */
  reset: () => void
  /** Set a specific size */
  setSize: (size: number) => void
}

export function useResizable({
  direction,
  initialSize,
  minSize,
  maxSize,
  storageKey,
  handlePosition,
}: UseResizableOptions): UseResizableReturn {
  // Use localStorage for persistence if storageKey is provided
  const [persistedSize, setPersistedSize] = useLocalStorage(
    storageKey || `__resizable_${direction}_${initialSize}`,
    initialSize
  )

  const [size, setLocalSize] = useState(storageKey ? persistedSize : initialSize)
  const [isResizing, setIsResizing] = useState(false)
  const startSizeRef = useRef(size)
  const startPosRef = useRef(0)

  // Sync with persisted size if storageKey changes
  useEffect(() => {
    if (storageKey) {
      setLocalSize(persistedSize)
    }
  }, [persistedSize, storageKey])

  const setSize = useCallback((newSize: number) => {
    const clampedSize = Math.max(minSize, Math.min(maxSize, newSize))
    setLocalSize(clampedSize)
    if (storageKey) {
      setPersistedSize(clampedSize)
    }
  }, [minSize, maxSize, storageKey, setPersistedSize])

  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    startSizeRef.current = size
    startPosRef.current = direction === 'horizontal' ? e.clientX : e.clientY
  }, [size, direction])

  const reset = useCallback(() => {
    setSize(initialSize)
  }, [initialSize, setSize])

  // Handle mouse move and mouse up globally
  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const currentPos = direction === 'horizontal' ? e.clientX : e.clientY
      let delta = currentPos - startPosRef.current

      // Invert delta based on handle position
      if (handlePosition === 'left' || handlePosition === 'top') {
        delta = -delta
      }

      const newSize = startSizeRef.current + delta
      setSize(newSize)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    // Set cursor style during resize
    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'
    document.body.style.userSelect = 'none'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, direction, handlePosition, setSize])

  return {
    size,
    isResizing,
    startResize,
    reset,
    setSize,
  }
}
