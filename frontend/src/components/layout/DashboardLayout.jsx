import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { signOut } from '../../features/auth/authSlice.js'
import { ROUTES } from '../../constants/app.js'
import { getErrorMessage } from '../../utils/apiErrors.js'
import Brand from '../common/Brand.jsx'

const DashboardLayout = () => {
  const dispatch = useDispatch()
  const user = useSelector((state) => state.auth.user)
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')

  const logout = async () => {
    setLogoutError('')
    setLoggingOut(true)
    try {
      await dispatch(signOut()).unwrap()
      navigate(ROUTES.login, { replace: true })
    } catch (error) {
      setLogoutError(getErrorMessage(error))
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <Brand />
        <div className="topbar-right">
          <span className="user-email">{user?.email || 'Your workspace'}</span>
          {logoutError && <span className="logout-error" role="alert">{logoutError}</span>}
          <button className="button button-quiet" onClick={logout} disabled={loggingOut}>{loggingOut ? 'Signing out…' : 'Log out'} <span aria-hidden="true">↗</span></button>
        </div>
      </header>
      <div className="dashboard-body">
        <aside className="sidebar">
          <p className="nav-caption">WORKSPACE</p>
          <nav aria-label="Dashboard">
            <NavLink to={ROUTES.generate} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="nav-icon" aria-hidden="true">✦</span> Generate Questions
            </NavLink>
            <NavLink to={ROUTES.questions} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="nav-icon list-icon" aria-hidden="true">☷</span> All Questions
            </NavLink>
          </nav>
          <div className="sidebar-footer"><span className="status-dot" /> Your workspace is ready</div>
        </aside>
        <main className="main-content"><Outlet /></main>
      </div>
    </div>
  )
}

export default DashboardLayout
