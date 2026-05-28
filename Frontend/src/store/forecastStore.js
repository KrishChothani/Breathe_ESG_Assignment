/**
 * src/store/forecastStore.js
 * Zustand store for emissions forecast state + what-if analysis.
 *
 * Per-FY caching: results are stored in `fyCache[fy]` so switching
 * between years shows data instantly without re-fetching.
 * Drivers change still triggers a fresh fetch (different dataset).
 */
import { create } from 'zustand'
import { getEmissionsForecast } from '../api/reports'

let _debounceTimer = null

/** Build list of selectable FYs: current + 2 prior */
export function getAvailableFYs(currentFY) {
  const startYear = parseInt(currentFY.split('-')[0], 10)
  const fys = []
  for (let y = startYear - 2; y <= startYear; y++) {
    fys.push(`${y}-${String(y + 1).slice(-2)}`)
  }
  return fys // ascending, e.g. ['2024-25', '2025-26', '2026-27']
}

export const useForecastStore = create((set, get) => ({
  selectedFY:  null,           // currently displayed FY
  forecastData: null,          // active FY data
  loading:      false,
  error:        null,

  // Per-FY cache: { '2025-26': responseData, '2024-25': responseData }
  fyCache: {},

  // What-if activity drivers (Scope 3 only, resets when FY changes)
  activityDrivers: {
    air_travel:       0,
    hotel_stays:      0,
    ground_transport: 0,
  },

  /**
   * Select a FY.
   * If cached data exists for that FY (and no driver overrides), show immediately.
   * Otherwise fetch from API.
   */
  selectFY: (fy) => {
    const { fyCache, activityDrivers } = get()
    const zeroDrivers = activityDrivers.air_travel === 0 &&
                        activityDrivers.hotel_stays === 0 &&
                        activityDrivers.ground_transport === 0

    // Reset drivers when switching FY
    set({ selectedFY: fy, activityDrivers: { air_travel: 0, hotel_stays: 0, ground_transport: 0 } })

    if (fyCache[fy] && zeroDrivers) {
      // Cache hit — show instantly
      set({ forecastData: fyCache[fy], error: null })
    } else {
      // Cache miss — fetch
      get().fetchForecast(fy, { air_travel: 0, hotel_stays: 0, ground_transport: 0 })
    }
  },

  /** Fetch forecast data for given FY and current drivers */
  fetchForecast: async (fy, driversOverride) => {
    const drivers = driversOverride ?? get().activityDrivers
    set({ loading: true, error: null, selectedFY: fy })
    try {
      const res = await getEmissionsForecast(fy, drivers)
      const isZeroDrivers = !drivers.air_travel && !drivers.hotel_stays && !drivers.ground_transport

      set(state => ({
        forecastData: res.data,
        loading:      false,
        // Only cache when no driver overrides (base state)
        fyCache: isZeroDrivers
          ? { ...state.fyCache, [fy]: res.data }
          : state.fyCache,
      }))
    } catch (err) {
      const msg = err?.response?.data?.message ?? err?.message ?? 'Forecast failed'
      set({ error: msg, loading: false })
    }
  },

  /** Update a single driver and re-fetch after 400ms debounce */
  setActivityDriver: (key, value) => {
    const newDrivers = { ...get().activityDrivers, [key]: value }
    set({ activityDrivers: newDrivers })

    if (_debounceTimer) clearTimeout(_debounceTimer)
    _debounceTimer = setTimeout(() => {
      const { selectedFY } = get()
      if (selectedFY) get().fetchForecast(selectedFY, newDrivers)
    }, 400)
  },

  /** Reset all drivers to zero and restore from cache if available */
  resetDrivers: () => {
    const zeroDrivers = { air_travel: 0, hotel_stays: 0, ground_transport: 0 }
    set({ activityDrivers: zeroDrivers })
    const { selectedFY, fyCache } = get()
    if (!selectedFY) return
    if (fyCache[selectedFY]) {
      set({ forecastData: fyCache[selectedFY] })
    } else {
      get().fetchForecast(selectedFY, zeroDrivers)
    }
  },
}))
