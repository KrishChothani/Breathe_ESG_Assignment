import axios from 'axios'
import { TOKEN_KEY, REFRESH_KEY } from '../utils/constants'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Helper — reads token from either key variant
const getToken  = () => localStorage.getItem(TOKEN_KEY)  || localStorage.getItem('access_token')
const getRefresh = () => localStorage.getItem(REFRESH_KEY) || localStorage.getItem('refresh_token')

// Attach JWT on every request
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401, attempt silent token refresh then retry original request
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = getRefresh()
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh/', { refresh })
          // Store under both key names to keep everything in sync
          localStorage.setItem(TOKEN_KEY,       data.access)
          localStorage.setItem('access_token',  data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return client(original)
        } catch {
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(REFRESH_KEY)
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default client
