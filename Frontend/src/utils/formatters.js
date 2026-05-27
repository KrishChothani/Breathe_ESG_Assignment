import { EMISSION_UNIT } from './constants'

export const formatCO2e = (val) => {
  if (val === null || val === undefined) return '—'
  const n = parseFloat(val)
  if (n >= 1000) return `${(n / 1000).toFixed(2)} t${EMISSION_UNIT.replace('kg', '')}`
  return `${n.toFixed(2)} ${EMISSION_UNIT}`
}

export const formatKwh = (val) => {
  if (val === null || val === undefined) return '—'
  const n = parseFloat(val)
  if (n >= 1000) return `${(n / 1000).toFixed(2)} MWh`
  return `${n.toFixed(2)} kWh`
}

export const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  try {
    return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(dateStr))
  } catch { return dateStr }
}

export const formatNumber = (val, decimals = 2) => {
  if (val === null || val === undefined) return '—'
  return parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export const truncate = (str, n = 30) => str && str.length > n ? str.slice(0, n) + '…' : (str ?? '—')
