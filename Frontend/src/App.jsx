import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Provider } from 'react-redux'
import store from './store'
import Layout from './components/Layout/Layout'
import ProtectedRoute from './pages/Auth/ProtectedRoute'
import Login from './pages/Auth/Login'
import Dashboard from './pages/Dashboard/index'
import Upload from './pages/Upload/index'
import Review from './pages/Review/index'
import Audit from './pages/Audit/index'
import PlantLookup from './pages/PlantLookup/index'
import Organisation from './pages/Organisation/index'
import BRSRReport from './pages/BRSRReport/index'
import EmissionFactors from './pages/EmissionFactors/index'

export default function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/"                  element={<Dashboard />} />
              <Route path="/upload"            element={<Upload />} />
              <Route path="/review"            element={<Review />} />
              <Route path="/audit"             element={<Audit />} />
              <Route path="/plant-lookup"      element={<PlantLookup />} />
              <Route path="/organisation"      element={<Organisation />} />
              <Route path="/brsr-report"       element={<BRSRReport />} />
              <Route path="/emission-factors"  element={<EmissionFactors />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </Provider>
  )
}


