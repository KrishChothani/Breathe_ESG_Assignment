import { createSlice } from '@reduxjs/toolkit'
import { TOKEN_KEY } from '../utils/constants'

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user:            null,
    isAuthenticated: !!(localStorage.getItem(TOKEN_KEY) || localStorage.getItem('access_token')),
  },
  reducers: {
    setUser:   (s, a) => { s.user = a.payload; s.isAuthenticated = true },
    clearAuth: (s)    => { s.user = null;       s.isAuthenticated = false },
  },
})

export const { setUser, clearAuth } = authSlice.actions
export default authSlice.reducer
