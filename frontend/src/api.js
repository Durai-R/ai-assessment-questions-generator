import axios from 'axios'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const REQUEST_TIMEOUT_MILLISECONDS = 40_000
window.sessionStorage.removeItem('assessment_access_token')
let getAuthStatus = () => 'unauthenticated'

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: REQUEST_TIMEOUT_MILLISECONDS,
})

axiosClient.interceptors.request.use((config) => {
  config.authenticatedAtRequest = getAuthStatus() === 'authenticated'
  return config
})

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    const isPublicAuthEndpoint = ['/api/auth/login', '/api/auth/register', '/api/auth/logout'].includes(requestUrl)
    if (
      error.response?.status === 401
      && error.config?.authenticatedAtRequest
      && getAuthStatus() === 'authenticated'
      && !isPublicAuthEndpoint
    ) {
      window.dispatchEvent(new Event('auth:expired'))
    }
    return Promise.reject(error)
  },
)

export const configureAuthStatusReader = (reader) => { getAuthStatus = reader }

export default axiosClient
