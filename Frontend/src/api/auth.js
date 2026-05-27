/**
 * api/auth.js — Updated for multi-tenant JWT
 * Login response includes: { access, refresh, user, organisation, role }
 * OR: { requires_org_selection: true, organisations: [...] }
 */

import client from './client'
import { TOKEN_KEY, REFRESH_KEY } from '../utils/constants'

export const login = async (username, password) => {
  const { data } = await client.post('/auth/login/', { username, password })

  if (data.requires_org_selection) {
    // Store a preliminary temporary token for the org-switch call if provided
    // (no token in multi-org flow yet — the switch endpoint will issue it)
    return data
  }

  // Single org — store both key variants
  if (data.access) {
    localStorage.setItem(TOKEN_KEY,        data.access)
    localStorage.setItem(REFRESH_KEY,      data.refresh)
    localStorage.setItem('access_token',   data.access)
    localStorage.setItem('refresh_token',  data.refresh)
    client.defaults.headers.common['Authorization'] = `Bearer ${data.access}`
  }
  return data
}

export const logout = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  delete client.defaults.headers.common['Authorization']
}

export const getMe = () => client.get('/auth/me/')
