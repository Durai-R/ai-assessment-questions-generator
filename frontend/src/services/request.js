import axios from 'axios'
import axiosClient from '../api.js'
import { actionFallback, ApiError, readableError } from '../utils/apiErrors.js'

const toAbortError = () => {
  const error = new Error('Request aborted')
  error.name = 'AbortError'
  return error
}

const request = async (path, { method = 'GET', data, params, signal } = {}) => {
  const fallback = actionFallback(path, method, data)
  try {
    const response = await axiosClient.request({ url: path, method, data, params, signal })
    return response.data
  } catch (error) {
    if (signal?.aborted || axios.isCancel(error) || error?.code === 'ERR_CANCELED') throw toAbortError()
    const failedResponse = error?.response
    if (!failedResponse) throw new ApiError(fallback, 0)
    const responseFallback = failedResponse.status === 401 && path.includes('/auth/login')
      ? 'Incorrect email or password.'
      : failedResponse.status === 409 && path.includes('/auth/register')
        ? 'An account with this email already exists.'
        : fallback
    throw new ApiError(readableError(failedResponse.data, responseFallback, failedResponse.status), failedResponse.status)
  }
}

export default request
