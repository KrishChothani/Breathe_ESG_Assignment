// Centralised API constants
export const API_BASE = '/api/v1'
export const TOKEN_KEY = 'breathe_access'
export const REFRESH_KEY = 'breathe_refresh'

export const SOURCE_TYPES = {
  SAP: 'SAP',
  UTILITY: 'UTILITY',
  TRAVEL: 'TRAVEL',
}

export const ROW_STATUS = {
  PENDING: 'PENDING',
  FLAGGED: 'FLAGGED',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  LOCKED: 'LOCKED',
}

export const ROW_STATUS_LABELS = {
  PENDING: 'Pending',
  FLAGGED: 'Flagged',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  LOCKED: 'Locked',
}

export const EMISSION_UNIT = 'kgCO₂e'

export const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: 'LayoutDashboard' },
  { label: 'Upload', path: '/upload', icon: 'Upload' },
  { label: 'Review', path: '/review', icon: 'ClipboardCheck' },
  { label: 'Audit', path: '/audit', icon: 'Lock' },
]
