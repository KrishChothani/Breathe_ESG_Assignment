import { create } from 'zustand'
import { getDashboardStats } from '../api/emissions'
import {
  getTrendData,
  getScopeBreakdown,
  getBySource,
  getByPlant,
  getIngestionActivity,
  getReviewPipeline
} from '../api/charts'

export const useDashboardStore = create((set, get) => ({
  // Global filter
  globalRange: '6m',
  setGlobalRange: (range) => {
    set({ globalRange: range })
    get().fetchDashboardData(range) // Refetch when global range changes
  },

  // State for all dashboard widgets
  stats: null,
  trend: [],
  scopeBreakdown: [],
  bySource: [],
  byPlant: [],
  ingestionActivity: [],
  reviewPipeline: [],

  // Loading states
  loadingStats: true,
  loadingTrend: true,
  loadingScope: true,
  loadingSource: true,
  loadingPlant: true,
  loadingActivity: true,
  loadingPipeline: true,
  
  // Overall fetcher to run them sequentially to avoid DB connection exhaustion (max 15 on Supabase)
  fetchDashboardData: async (range) => {
    const currentRange = range || get().globalRange
    
    // Set all to loading initially
    set({
      loadingStats: true,
      loadingTrend: true,
      loadingScope: true,
      loadingSource: true,
      loadingPlant: true,
      loadingActivity: true,
      loadingPipeline: true,
    })

    // 1. Fetch Stats
    try {
      const statsRes = await getDashboardStats()
      set({ stats: statsRes.data, loadingStats: false })
    } catch (e) {
      set({ stats: null, loadingStats: false })
    }

    // 2. Fetch Trend
    try {
      const trendRes = await getTrendData(currentRange)
      set({ trend: trendRes.data, loadingTrend: false })
    } catch (e) {
      set({ trend: [], loadingTrend: false })
    }

    // 3. Fetch Scope Breakdown
    try {
      const scopeRes = await getScopeBreakdown(currentRange)
      set({ scopeBreakdown: scopeRes.data, loadingScope: false })
    } catch (e) {
      set({ scopeBreakdown: [], loadingScope: false })
    }

    // 4. Fetch By Source
    try {
      const sourceRes = await getBySource(currentRange)
      set({ bySource: sourceRes.data, loadingSource: false })
    } catch (e) {
      set({ bySource: [], loadingSource: false })
    }

    // 5. Fetch By Plant
    try {
      const plantRes = await getByPlant(currentRange)
      set({ byPlant: plantRes.data, loadingPlant: false })
    } catch (e) {
      set({ byPlant: [], loadingPlant: false })
    }

    // 6. Fetch Ingestion Activity (usually fixed 30d, but we'll use standard call)
    try {
      const activityRes = await getIngestionActivity('30d')
      set({ ingestionActivity: activityRes.data, loadingActivity: false })
    } catch (e) {
      set({ ingestionActivity: [], loadingActivity: false })
    }

    // 7. Fetch Review Pipeline
    try {
      const pipelineRes = await getReviewPipeline()
      set({ reviewPipeline: pipelineRes.data, loadingPipeline: false })
    } catch (e) {
      set({ reviewPipeline: [], loadingPipeline: false })
    }
  },

  // Individual fetcher for Ingestion Activity since it has a separate range toggle
  fetchIngestionActivity: async (range) => {
    set({ loadingActivity: true })
    try {
      const activityRes = await getIngestionActivity(range)
      set({ ingestionActivity: activityRes.data, loadingActivity: false })
    } catch (e) {
      set({ ingestionActivity: [], loadingActivity: false })
    }
  }
}))

