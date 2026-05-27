/**
 * src/api/charts.js
 * API calls for all six analytics chart endpoints.
 */
import client from './client'

export const getTrendData          = (range = '6m', source)    => client.get('/emissions/charts/trend/',              { params: { range, ...(source ? { source } : {}) } })
export const getScopeBreakdown     = (range = '1y')             => client.get('/emissions/charts/scope-breakdown/',    { params: { range } })
export const getBySource           = (range = '6m')             => client.get('/emissions/charts/by-source/',          { params: { range } })
export const getByPlant            = (range = '1y', top = 10)   => client.get('/emissions/charts/by-plant/',           { params: { range, top } })
export const getIngestionActivity  = (range = '30d')            => client.get('/emissions/charts/ingestion-activity/', { params: { range } })
export const getReviewPipeline     = ()                         => client.get('/emissions/charts/review-pipeline/')
