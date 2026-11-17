import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { authService } from '../../services/authService.js'

export const restoreSession = createAsyncThunk('auth/restoreSession', async (_, { rejectWithValue }) => {
  try {
    const result = await authService.me()
    return result?.user ?? result
  } catch (error) {
    return rejectWithValue({ signedOut: error?.status === 401 })
  }
})

export const signIn = createAsyncThunk('auth/signIn', async (credentials) => {
  const user = await authService.login(credentials)
  return user?.user ?? user
})

export const register = createAsyncThunk('auth/register', async (credentials) => {
  await authService.register(credentials)
  return false
})

export const signOut = createAsyncThunk('auth/signOut', async () => {
  await authService.logout()
})

const authSlice = createSlice({
  name: 'auth',
  initialState: { user: null, status: 'loading' },
  reducers: {
    clearUser(state) {
      state.user = null
      state.status = 'unauthenticated'
    },
  },
  extraReducers(builder) {
    builder
      .addCase(restoreSession.pending, (state) => {
        state.user = null
        state.status = 'loading'
      })
      .addCase(restoreSession.fulfilled, (state, action) => {
        state.user = action.payload
        state.status = 'authenticated'
      })
      .addCase(restoreSession.rejected, (state, action) => {
        state.user = null
        state.status = action.payload?.signedOut ? 'unauthenticated' : 'error'
      })
      .addCase(signIn.fulfilled, (state, action) => {
        state.user = action.payload
        state.status = 'authenticated'
      })
      .addCase(signOut.fulfilled, (state) => {
        state.user = null
        state.status = 'unauthenticated'
      })
  },
})

export const { clearUser } = authSlice.actions
export default authSlice.reducer
