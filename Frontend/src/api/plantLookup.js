import client from './client'

export const getPlantLookups = (params) =>
  client.get('/emissions/plant-lookup/', { params })

export const getPlantLookup = (id) =>
  client.get(`/emissions/plant-lookup/${id}/`)

export const createPlantLookup = (data) =>
  client.post('/emissions/plant-lookup/', data)

export const updatePlantLookup = (id, data) =>
  client.patch(`/emissions/plant-lookup/${id}/`, data)

export const deactivatePlant = (id) =>
  client.post(`/emissions/plant-lookup/${id}/deactivate/`)

export const deletePlantLookup = (id) =>
  client.delete(`/emissions/plant-lookup/${id}/`)

export const bulkImportCSV = (file, overwriteExisting = false) => {
  const form = new FormData()
  form.append('file', file)
  form.append('overwrite_existing', overwriteExisting ? 'true' : 'false')
  return client.post('/emissions/plant-lookup/bulk-import/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getUnresolvedWERKS = () =>
  client.get('/emissions/plant-lookup/unresolved/')

export const exportPlantCSV = () =>
  client.get('/emissions/plant-lookup/export/', { responseType: 'blob' }).then((res) => {
    const url  = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href  = url
    link.setAttribute('download', 'plant_lookup_export.csv')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
