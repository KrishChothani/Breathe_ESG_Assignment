import client from './client'

// ── Multipart config — lets browser set Content-Type + boundary automatically ─
// IMPORTANT: Do NOT set Content-Type: multipart/form-data manually.
// The browser must set it so the boundary token is included.
const MULTIPART = { headers: { 'Content-Type': undefined } }

export const uploadSAPFile = (file, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('source_type', 'SAP')
  return client.post('/ingestion/upload/', fd, {
    ...MULTIPART,
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
}

export const uploadUtilityCSV = (file, onProgress) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('source_type', 'UTILITY')
  return client.post('/ingestion/upload/', fd, {
    ...MULTIPART,
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
}

export const pullTravelData = (credentials) =>
  client.post('/ingestion/travel/navan/sync/', credentials)

export const getUploads = (params) => client.get('/ingestion/upload/', { params })

// ── AI Bill OCR ───────────────────────────────────────────────────────────────

/**
 * Upload a bill image/PDF for AI extraction.
 * Returns { upload_id, extracted, message }
 */
export const extractBill = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  // Must use MULTIPART config — Content-Type: application/json causes 415
  return client.post('/ingestion/utility/ocr-extract/', fd, MULTIPART)
}

/**
 * Confirm analyst-reviewed OCR fields and save as UtilityRow.
 * @param {string} uploadId - The upload_id from extractBill response
 * @param {object} fields   - The confirmed field values
 */
export const confirmBill = (uploadId, fields) =>
  client.post('/ingestion/utility/ocr-confirm/', {
    upload_id: uploadId,
    fields,
  })
