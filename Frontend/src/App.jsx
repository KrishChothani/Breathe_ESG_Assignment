import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Provider } from 'react-redux'
import { useSelector } from 'react-redux'
import store from './store'
import Layout from './components/Layout/Layout'
import ProtectedRoute from './pages/Auth/ProtectedRoute'
import LandingPage from './pages/Landing/LandingPage'
import Login from './pages/Auth/Login'
import Dashboard from './pages/Dashboard/index'
import Upload from './pages/Upload/index'
import Review from './pages/Review/index'
import Audit from './pages/Audit/index'
import PlantLookup from './pages/PlantLookup/index'
import Organisation from './pages/Organisation/index'
import BRSRReport from './pages/BRSRReport/index'
import EmissionFactors from './pages/EmissionFactors/index'

/**
 * PublicRoute — wraps public pages (Landing, Login).
 * If the user is already authenticated, redirect straight to /dashboard.
 */
function PublicRoute({ children }) {
  const isAuthenticated = useSelector((s) => s.auth.isAuthenticated)
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <Routes>
          {/* ── Public routes ──────────────────────────────────────────────── */}
          <Route
            path="/"
            element={
              <PublicRoute>
                <LandingPage />
              </PublicRoute>
            }
          />
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />

          {/* ── Protected app routes ───────────────────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard"        element={<Dashboard />} />
              <Route path="/upload"           element={<Upload />} />
              <Route path="/review"           element={<Review />} />
              <Route path="/audit"            element={<Audit />} />
              <Route path="/plant-lookup"     element={<PlantLookup />} />
              <Route path="/organisation"     element={<Organisation />} />
              <Route path="/brsr-report"      element={<BRSRReport />} />
              <Route path="/emission-factors" element={<EmissionFactors />} />
            </Route>
          </Route>

          {/* ── Fallback ───────────────────────────────────────────────────── */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </Provider>
  )
}
