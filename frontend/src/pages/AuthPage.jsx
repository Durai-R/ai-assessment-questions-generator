import { useState } from 'react'
import { useDispatch } from 'react-redux'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../utils/apiErrors.js'
import { register, signIn } from '../features/auth/authSlice.js'
import { ROUTES } from '../constants/app.js'
import Brand from '../components/common/Brand.jsx'
import Spinner from '../components/common/Spinner.jsx'
import StatusNotice from '../components/common/StatusNotice.jsx'

const AuthPage = ({ mode }) => {
  const isRegister = mode === 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [pending, setPending] = useState(false)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const registered = location.state?.registered

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    const nextFieldErrors = {}
    const cleanEmail = email.trim()
    if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      nextFieldErrors.email = 'Enter a valid email address.'
    }
    const passwordLength = [...password].length
    if (!password) {
      nextFieldErrors.password = 'Password is required.'
    } else if (passwordLength < 8) {
      nextFieldErrors.password = 'Password must be at least 8 characters.'
    } else if (passwordLength > 128) {
      nextFieldErrors.password = 'Password must be no more than 128 characters.'
    }
    if (Object.keys(nextFieldErrors).length) {
      setFieldErrors(nextFieldErrors)
      return
    }
    setFieldErrors({})
    setPending(true)
    try {
      if (isRegister) {
        const hasSession = await dispatch(register({ email: cleanEmail, password })).unwrap()
        if (hasSession) navigate(ROUTES.generate, { replace: true })
        else navigate(ROUTES.login, { replace: true, state: { registered: true } })
      } else {
        await dispatch(signIn({ email: cleanEmail, password })).unwrap()
        navigate(location.state?.from?.pathname || ROUTES.generate, { replace: true })
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Brand />
        <div className="auth-heading">
          <p className="eyebrow">{isRegister ? 'GET STARTED' : 'WELCOME BACK'}</p>
          <h1>{isRegister ? 'Create your account' : 'Sign in to your account'}</h1>
          <p>{isRegister ? 'Build better assessments in less time.' : 'Pick up right where you left off.'}</p>
        </div>
        {registered && <StatusNotice type="success">Account created. Sign in to continue.</StatusNotice>}
        {error && <StatusNotice type="error">{error}</StatusNotice>}
        <form className="stack-form" onSubmit={submit} noValidate>
          <label className="field">
            <span>Email</span>
            <input type="email" autoComplete="email" value={email} onChange={(event) => { setEmail(event.target.value); setFieldErrors((current) => ({ ...current, email: '' })) }} placeholder="you@example.com" required aria-invalid={Boolean(fieldErrors.email)} aria-describedby={fieldErrors.email ? 'auth-email-error' : undefined} />
            {fieldErrors.email && <small className="field-error" id="auth-email-error">{fieldErrors.email}</small>}
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} value={password} onChange={(event) => { setPassword(event.target.value); setFieldErrors((current) => ({ ...current, password: '' })) }} placeholder="Enter your password" required aria-invalid={Boolean(fieldErrors.password)} aria-describedby={fieldErrors.password ? 'auth-password-hint auth-password-error' : 'auth-password-hint'} />
            <small id="auth-password-hint">Use 8–128 characters.</small>
            {fieldErrors.password && <small className="field-error" id="auth-password-error">{fieldErrors.password}</small>}
          </label>
          <button className="button primary full" disabled={pending} type="submit">
            {pending ? <><Spinner />{isRegister ? 'Creating account…' : 'Signing in…'}</> : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>
        <p className="auth-switch">
          {isRegister ? 'Already have an account?' : 'New to AI Assessment Generator?'}{' '}
          <NavLink to={isRegister ? ROUTES.login : ROUTES.register}>{isRegister ? 'Sign in' : 'Create an account'}</NavLink>
        </p>
      </section>
      <div className="auth-aside">
        <span className="aside-orb orb-one" /><span className="aside-orb orb-two" />
        <div className="aside-copy">
          <span className="aside-label">ASSESSMENTS, REIMAGINED</span>
          <h2>Thoughtful questions.<br />Made in moments.</h2>
          <p>Turn your subject expertise into ready-to-use assessments with a workflow that keeps you in control.</p>
          <div className="aside-metrics"><span><strong>01</strong> Generate topics</span><span><strong>02</strong> Review drafts</span><span><strong>03</strong> Save and share</span></div>
        </div>
      </div>
    </main>
  )
}

export default AuthPage
