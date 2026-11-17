import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Navigate, Route, Routes } from 'react-router-dom'
import { clearUser, restoreSession } from '../features/auth/authSlice.js'
import { ROUTES } from '../constants/app.js'
import Spinner from '../components/common/Spinner.jsx'
import StatusNotice from '../components/common/StatusNotice.jsx'
import DashboardLayout from '../components/layout/DashboardLayout.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'
import AuthPage from '../pages/AuthPage.jsx'
import GeneratePage from '../pages/GeneratePage.jsx'
import QuestionsPage from '../pages/QuestionsPage.jsx'

const AppRoutes = () => {
  const dispatch = useDispatch()
  const { status, user } = useSelector((state) => state.auth)

  useEffect(() => {
    const expire = () => dispatch(clearUser())
    window.addEventListener('auth:expired', expire)
    dispatch(restoreSession())
    return () => window.removeEventListener('auth:expired', expire)
  }, [dispatch])

  if (status === 'loading') return <div className="app-loading"><Spinner /><span>Checking your session…</span></div>
  if (status === 'error') return <div className="app-loading">
    <StatusNotice type="error">We couldn’t verify your session. Check your connection and try again.</StatusNotice>
    <button className="button secondary" onClick={() => dispatch(restoreSession())}>Retry</button>
  </div>
  const signedIn = status === 'authenticated' && Boolean(user)

  return (
    <Routes>
      <Route path={ROUTES.login} element={signedIn ? <Navigate to={ROUTES.generate} replace /> : <AuthPage mode="login" />} />
      <Route path={ROUTES.register} element={signedIn ? <Navigate to={ROUTES.generate} replace /> : <AuthPage mode="register" />} />
      <Route path={ROUTES.dashboard} element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="generate" replace />} />
        <Route path="generate" element={<GeneratePage />} />
        <Route path="questions" element={<QuestionsPage />} />
      </Route>
      <Route path="*" element={<Navigate to={signedIn ? ROUTES.generate : ROUTES.login} replace />} />
    </Routes>
  )
}

export default AppRoutes
