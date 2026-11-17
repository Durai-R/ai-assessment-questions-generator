import request from './request.js'

export const authService = {
  register: (body) => request('/api/auth/register', { method: 'POST', data: body }),
  login: (body) => request('/api/auth/login', { method: 'POST', data: body }),
  me: () => request('/api/auth/me'),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
}
