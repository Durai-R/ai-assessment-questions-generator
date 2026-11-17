import request from './request.js'

export const topicService = {
  suggestTopics: (subject) => request('/api/topics/suggest', { method: 'POST', data: { subject } }),
}
