import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { getNormalisedRows } from '../api/emissions'

export const fetchRows = createAsyncThunk('emissions/fetchRows', async (params, { rejectWithValue }) => {
  try { const { data } = await getNormalisedRows(params); return data } catch (e) { return rejectWithValue(e.response?.data) }
})

const emissionsSlice = createSlice({
  name: 'emissions',
  initialState: { rows: [], count: 0, loading: false, error: null, activeTab: 'SAP' },
  reducers: {
    setActiveTab: (s, a) => { s.activeTab = a.payload },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRows.pending, (s) => { s.loading = true; s.error = null })
      .addCase(fetchRows.fulfilled, (s, a) => { s.loading = false; s.rows = a.payload.results ?? []; s.count = a.payload.count ?? 0 })
      .addCase(fetchRows.rejected, (s, a) => { s.loading = false; s.error = a.payload })
  },
})

export const { setActiveTab } = emissionsSlice.actions
export default emissionsSlice.reducer
