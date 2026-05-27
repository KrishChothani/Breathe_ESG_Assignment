import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { approveRow, rejectRow, lockBatch } from '../api/review'

export const doApprove = createAsyncThunk('review/approve', async (payload, { rejectWithValue }) => {
  try { const { data } = await approveRow(payload); return data } catch (e) { return rejectWithValue(e.response?.data) }
})
export const doReject = createAsyncThunk('review/reject', async (payload, { rejectWithValue }) => {
  try { const { data } = await rejectRow(payload); return data } catch (e) { return rejectWithValue(e.response?.data) }
})
export const doLockBatch = createAsyncThunk('review/lock', async (ids, { rejectWithValue }) => {
  try { const { data } = await lockBatch(ids); return data } catch (e) { return rejectWithValue(e.response?.data) }
})

const reviewSlice = createSlice({
  name: 'review',
  initialState: { selected: [], actionLoading: false, error: null, detailRow: null },
  reducers: {
    toggleSelect: (s, a) => {
      const id = a.payload
      s.selected = s.selected.includes(id) ? s.selected.filter((x) => x !== id) : [...s.selected, id]
    },
    selectAll: (s, a) => { s.selected = a.payload },
    clearSelected: (s) => { s.selected = [] },
    setDetailRow: (s, a) => { s.detailRow = a.payload },
  },
  extraReducers: (builder) => {
    const pending = (s) => { s.actionLoading = true }
    const settled = (s) => { s.actionLoading = false }
    builder
      .addCase(doApprove.pending, pending).addCase(doApprove.fulfilled, settled).addCase(doApprove.rejected, settled)
      .addCase(doReject.pending, pending).addCase(doReject.fulfilled, settled).addCase(doReject.rejected, settled)
      .addCase(doLockBatch.pending, pending).addCase(doLockBatch.fulfilled, settled).addCase(doLockBatch.rejected, settled)
  },
})

export const { toggleSelect, selectAll, clearSelected, setDetailRow } = reviewSlice.actions
export default reviewSlice.reducer
