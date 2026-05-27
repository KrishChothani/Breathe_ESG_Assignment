import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { getUploads } from '../api/ingestion'

export const fetchUploads = createAsyncThunk('ingestion/fetchUploads', async (params, { rejectWithValue }) => {
  try { const { data } = await getUploads(params); return data } catch (e) { return rejectWithValue(e.response?.data) }
})

const ingestionSlice = createSlice({
  name: 'ingestion',
  initialState: { uploads: [], loading: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUploads.pending, (s) => { s.loading = true; s.error = null })
      .addCase(fetchUploads.fulfilled, (s, a) => { s.loading = false; s.uploads = a.payload.results ?? a.payload })
      .addCase(fetchUploads.rejected, (s, a) => { s.loading = false; s.error = a.payload })
  },
})

export default ingestionSlice.reducer
