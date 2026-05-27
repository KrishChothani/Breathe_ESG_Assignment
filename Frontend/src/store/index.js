import { configureStore } from '@reduxjs/toolkit'
import authReducer         from './authSlice'
import organisationReducer from './organisationSlice'
import ingestionReducer    from './ingestionSlice'
import emissionsReducer    from './emissionsSlice'
import reviewReducer       from './reviewSlice'

const store = configureStore({
  reducer: {
    auth:         authReducer,
    organisation: organisationReducer,
    ingestion:    ingestionReducer,
    emissions:    emissionsReducer,
    review:       reviewReducer,
  },
})

export default store
