import client from './client'

/** GET /api/v1/reports/brsr-summary/?fy=2024-25 */
export const getBRSRSummary = (fy) =>
  client.get('/reports/brsr-summary/', { params: fy ? { fy } : {} })

/** GET /api/v1/ingestion/emission-factors/ */
export const getEmissionFactors = (params) =>
  client.get('/ingestion/emission-factors/', { params })
