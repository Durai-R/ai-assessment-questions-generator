import { useSelector } from 'react-redux'
import { Navigate, useLocation } from 'react-router-dom'
import { ROUTES } from '../constants/app.js'
import Spinner from '../components/common/Spinner.jsx'

const ProtectedRoute = ({ children }) => {
  const { user, status } = useSelector((state) => state.auth)
  const location = useLocation()
  if (status === 'loading') return <div className="app-loading"><Spinner /><span>Checking your session…</span></div>
  return status === 'authenticated' && user ? children : <Navigate to={ROUTES.login} state={{ from: location }} replace />
}

export default ProtectedRoute
