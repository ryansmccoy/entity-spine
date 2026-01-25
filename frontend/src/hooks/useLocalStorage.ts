import { useState, useCallback, useEffect } from 'react'

/**
 * Hook to persist state in localStorage with automatic serialization/deserialization
 */
export function useLocalStorage<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize state from localStorage or default
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key)
      if (stored !== null) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error)
    }
    return defaultValue
  })

  // Update localStorage when value changes
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.warn(`Error writing localStorage key "${key}":`, error)
    }
  }, [key, value])

  // Setter that handles both direct values and updater functions
  const setStoredValue = useCallback((newValue: T | ((prev: T) => T)) => {
    setValue((prev) => {
      const result = newValue instanceof Function ? newValue(prev) : newValue
      return result
    })
  }, [])

  return [value, setStoredValue]
}

/**
 * Hook to get/set a simple boolean preference
 */
export function usePreference(key: string, defaultValue: boolean): [boolean, () => void] {
  const [value, setValue] = useLocalStorage(key, defaultValue)
  const toggle = useCallback(() => setValue((prev) => !prev), [setValue])
  return [value, toggle]
}
