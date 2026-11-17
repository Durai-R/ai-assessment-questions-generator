import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'react-redux'
import { configureAuthStatusReader } from './api.js'
import { store } from './app/store.js'
import AppRoutes from './routes/AppRoutes.jsx'
import './style.css'

configureAuthStatusReader(() => store.getState().auth.status)

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>,
)
