import request from './request.js'

const generateQuestions = (body) => request('/api/questions/generate', { method: 'POST', data: body })
const saveQuestions = (body) => request('/api/questions/bulk', { method: 'POST', data: body })
const listQuestions = (params, signal) => request('/api/questions', { params, signal })
const filterOptions = async (subject) => {
  const params = new URLSearchParams()
  if (subject) params.set('subject', subject)
  const result = await request('/api/questions/filter-options', { params })
  if (!Array.isArray(result?.subjects) || !Array.isArray(result?.topics)) {
    throw new Error('The filter options response was not in the expected format.')
  }
  return result
}
const updateQuestion = (id, body) => request(`/api/questions/${encodeURIComponent(id)}`, { method: 'PATCH', data: body })
const deleteQuestion = (id) => request(`/api/questions/${encodeURIComponent(id)}`, { method: 'DELETE' })

export const questionService = {
  generateQuestions,
  saveQuestions,
  listQuestions,
  filterOptions,
  updateQuestion,
  deleteQuestion,
}
