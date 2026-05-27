import client from './client'

export const approveRow = (payload) => client.post('/review/approve/', payload)
export const rejectRow = (payload) => client.post('/review/reject/', payload)
export const lockBatch = (ids) => client.post('/review/lock/', { ids })
