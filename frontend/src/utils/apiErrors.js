export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const actionFallback = (path, method, body) => {
  if (path.includes('/auth/login')) return "We couldn't sign you in. Check your connection and try again."
  if (path.includes('/auth/register')) return 'Account creation failed. Check your details and try again.'
  if (path.includes('/auth/logout')) return "We couldn't log you out. Check your connection and try again."
  if (path.includes('/topics/suggest')) {
    const subject = body?.subject || ''
    return `We couldn't load topics${subject ? ` for ${subject}` : ''}. Try again or enter a custom topic.`
  }
  if (path.includes('/questions/generate')) return 'Question generation failed. Your current draft is still available. Try again.'
  if (path.includes('/questions/bulk')) return "Questions couldn't be saved. Your current draft is still available. Try again."
  if (path.startsWith('/api/questions/') && method === 'PATCH') return "Question couldn't be updated. Your edits are still available. Try again."
  if (path.startsWith('/api/questions/') && method === 'DELETE') return "Question couldn't be deleted. Try again."
  if (path.includes('/filter-options')) return 'Filter options could not be loaded. Try again.'
  if (path.startsWith('/api/questions')) return "We couldn't load your questions. Try again."
  return 'This action could not be completed. Try again.'
}

export const readableError = (payload, fallback, status) => {
  if (status === 401) {
    return fallback === 'Incorrect email or password.'
      ? fallback
      : 'Your session has expired. Sign in again to continue.'
  }
  const detail = payload?.detail
  if (typeof detail === 'string') {
    const knownMessages = {
      'An account with this email already exists.': detail,
      'Invalid email or password.': 'Incorrect email or password.',
      'Authentication required.': 'Your session has expired. Sign in again to continue.',
      'Question not found.': 'This question is no longer available. Refresh the question bank and try again.',
      'Bulk save requires a MongoDB replica set with transaction support.': 'Bulk saving is temporarily unavailable because the database does not support transactions. Your current draft is still available.',
      'AI generation is not configured. Set GEMINI_API_KEY on the backend.': 'AI generation is not configured. Contact the administrator.',
      'AI generation reached its usage limit. Try again later.': detail,
      'The AI service is temporarily busy. Please wait a moment and try again.': detail,
      'Gemini generation timed out. Try again.': detail,
      'Gemini returned an empty response. Try generating again.': detail,
      'Gemini returned an invalid response. Try generating again.': detail,
      'Gemini returned fewer than five distinct topics. Try generating again.': detail,
      'Gemini returned fewer questions than requested. Try generating again.': detail,
      'Gemini returned more questions than requested. Try generating again.': detail,
      'Gemini is temporarily unavailable. Try again.': detail,
      'Gemini could not complete generation. Try again.': detail,
    }
    return knownMessages[detail] || fallback
  }
  if (Array.isArray(detail)) {
    const labels = {
      email: 'Email', password: 'Password', subject: 'Subject', topic: 'Topic',
      difficulty: 'Difficulty', count: 'Number of questions', questions: 'Questions',
      question_text: 'Question', options: 'Answer options', correct_option_index: 'Correct answer',
      explanation: 'Explanation',
    }
    const errors = detail.flatMap((item) => {
      const location = Array.isArray(item?.loc) ? item.loc : []
      const field = [...location].reverse().find((part) => typeof part === 'string' && labels[part])
      return field ? [`${labels[field]}: check this value and try again.`] : []
    })
    if (errors.length) return [...new Set(errors)].join(' ')
  }
  return fallback
}

export const getErrorMessage = (error) => {
  if (error?.name === 'AbortError') return ''
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string') return error.message
  return 'Something went wrong. Please try again.'
}
