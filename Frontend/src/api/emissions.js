import client from './client'

export const getDashboardStats = () =>
  client.get('/emissions/dashboard/stats/')

export const getNormalisedRows = (params) =>
  client.get('/emissions/dashboard/', { params })

export const getRowDetail = (id) =>
  client.get(`/emissions/dashboard/${id}/`)
