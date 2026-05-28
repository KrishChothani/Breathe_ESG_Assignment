import client from './client'

/** GET /api/v1/reports/brsr-summary/?fy=2024-25 */
export const getBRSRSummary = (fy) =>
  client.get('/reports/brsr-summary/', { params: fy ? { fy } : {} })

/** GET /api/v1/ingestion/emission-factors/ */
export const getEmissionFactors = (params) =>
  client.get('/ingestion/emission-factors/', { params })

/**
 * GET /api/v1/reports/emissions-forecast/
 * @param {string} fy
 * @param {object} drivers
 */
export const getEmissionsForecast = (fy, drivers = {}) => {
  const params = { fy }
  if (drivers.air_travel    !== undefined) params.driver_air    = drivers.air_travel
  if (drivers.hotel_stays   !== undefined) params.driver_hotel  = drivers.hotel_stays
  if (drivers.ground_transport !== undefined) params.driver_ground = drivers.ground_transport
  return client.get('/reports/emissions-forecast/', { params })
}
