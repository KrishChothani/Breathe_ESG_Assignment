import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { Outlet } from 'react-router-dom'
import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setUser } from '../../store/authSlice'
import { getMe } from '../../api/auth'
import { setActiveOrganisation } from '../../store/organisationSlice'

export default function Layout() {
  const dispatch = useDispatch()
  const user = useSelector((s) => s.auth.user)

  useEffect(() => {
    if (!user) {
      getMe().then(({ data }) => {
        dispatch(setUser(data))
        if (data.active_organisation) {
          dispatch(setActiveOrganisation({
            organisation: data.active_organisation,
            role: data.active_role,
            available_organisations: []
          }))
        }
      }).catch(err => console.error("Failed to fetch user data on reload", err))
    }
  }, [user, dispatch])

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <TopBar />
      <main className="ml-56 pt-16 min-h-screen">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
