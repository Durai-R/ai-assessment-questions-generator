export const makeId = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`

export const normalizeQuestion = (question) => ({
  ...question,
  question_text: question.question_text ?? '',
  options: Array.isArray(question.options) ? [...question.options, '', '', '', ''].slice(0, 4) : ['', '', '', ''],
  correct_option_index: Number.isInteger(question.correct_option_index) ? question.correct_option_index : 0,
  explanation: question.explanation ?? '',
})
