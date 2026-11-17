import { useState } from 'react'
import { DIFFICULTIES, LETTERS } from '../../constants/app.js'
import { getErrorMessage } from '../../utils/apiErrors.js'
import { normalizeQuestion } from '../../utils/questions.js'
import Spinner from '../common/Spinner.jsx'
import StatusNotice from '../common/StatusNotice.jsx'
import DialogFrame from './DialogFrame.jsx'

const QuestionEditDialog = ({ question, sharedMetadata = false, onClose, onSave }) => {
  const [form, setForm] = useState(() => normalizeQuestion(question))
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [pending, setPending] = useState(false)
  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }))
    setFieldErrors((current) => ({ ...current, [key]: '' }))
    setError('')
  }
  const updateOption = (index, value) => {
    setForm((current) => ({ ...current, options: current.options.map((option, itemIndex) => itemIndex === index ? value : option) }))
    setFieldErrors((current) => ({ ...current, options: '' }))
    setError('')
  }

  const submit = async (event) => {
    event.preventDefault()
    const normalized = normalizeQuestion(form)
    const nextFieldErrors = {}
    if (!normalized.question_text.trim()) nextFieldErrors.question_text = 'Enter a question.'
    if (normalized.options.some((option) => !option.trim())) nextFieldErrors.options = 'Enter all four answer options.'
    else if (new Set(normalized.options.map((option) => option.trim().toLocaleLowerCase())).size !== 4) nextFieldErrors.options = 'Each answer option must be distinct.'
    if (!normalized.explanation.trim()) nextFieldErrors.explanation = 'Enter an explanation.'
    if (!Number.isInteger(normalized.correct_option_index) || normalized.correct_option_index < 0 || normalized.correct_option_index > 3) nextFieldErrors.correct_option_index = 'Select a valid correct answer.'
    if (Object.keys(nextFieldErrors).length) {
      setFieldErrors(nextFieldErrors)
      setError('')
      return
    }
    setPending(true)
    setError('')
    setFieldErrors({})
    try {
      const result = await onSave({ ...normalized, correct_option_index: Number(normalized.correct_option_index) })
      if (result) setError(result)
    } catch (saveError) {
      setError(getErrorMessage(saveError))
    } finally {
      setPending(false)
    }
  }

  return <DialogFrame title="Edit question" onClose={() => { if (!pending) onClose() }} wide labelledId="question-edit-title">
    <form className="edit-form" onSubmit={submit}>
      {sharedMetadata && <p className="dialog-description">Subject and topic are fixed. Difficulty applies to every question in this draft set.</p>}
      <div className="edit-meta-grid">
        <div className="field"><span>Subject</span><div className="edit-readonly-value">{form.subject || '—'}</div></div>
        <div className="field"><span>Topic</span><div className="edit-readonly-value">{form.topic || '—'}</div></div>
        <label className="field"><span>Difficulty</span><select value={form.difficulty || 'Medium'} onChange={(event) => update('difficulty', event.target.value)}>{DIFFICULTIES.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <label className="field"><span>Question <i className="required">*</i></span><textarea maxLength="2000" rows="3" value={form.question_text} onChange={(event) => update('question_text', event.target.value)} required aria-invalid={Boolean(fieldErrors.question_text)} aria-describedby={fieldErrors.question_text ? 'edit-question-error' : undefined} />{fieldErrors.question_text && <small className="field-error" id="edit-question-error">{fieldErrors.question_text}</small>}</label>
      <div className="field"><span>Answer options <i className="required">*</i></span>
        <div className="option-edit-grid">{form.options.map((option, index) => <label className="option-edit" key={index}><span className="option-letter">{LETTERS[index]}</span><input maxLength="500" aria-label={`Option ${LETTERS[index]}`} value={option} onChange={(event) => updateOption(index, event.target.value)} required aria-invalid={Boolean(fieldErrors.options)} aria-describedby={fieldErrors.options ? 'edit-options-error' : undefined} /></label>)}</div>
        {fieldErrors.options && <small className="field-error" id="edit-options-error">{fieldErrors.options}</small>}
      </div>
      <label className="field"><span>Correct answer <i className="required">*</i></span><select value={form.correct_option_index} onChange={(event) => update('correct_option_index', Number(event.target.value))} aria-invalid={Boolean(fieldErrors.correct_option_index)} aria-describedby={fieldErrors.correct_option_index ? 'edit-correct-error' : undefined}>{LETTERS.map((letter, index) => <option value={index} key={letter}>{letter} — {form.options[index] || 'Option text'}</option>)}</select>{fieldErrors.correct_option_index && <small className="field-error" id="edit-correct-error">{fieldErrors.correct_option_index}</small>}</label>
      <label className="field"><span>Explanation <i className="required">*</i></span><textarea maxLength="4000" rows="3" value={form.explanation} onChange={(event) => update('explanation', event.target.value)} required aria-invalid={Boolean(fieldErrors.explanation)} aria-describedby={fieldErrors.explanation ? 'edit-explanation-error' : undefined} />{fieldErrors.explanation && <small className="field-error" id="edit-explanation-error">{fieldErrors.explanation}</small>}</label>
      {error && <StatusNotice type="error">{error}</StatusNotice>}
      <div className="modal-actions"><button type="button" className="button secondary" onClick={onClose} disabled={pending}>Cancel</button><button type="submit" className="button primary" disabled={pending}>{pending ? <><Spinner /> Saving…</> : 'Save changes'}</button></div>
    </form>
  </DialogFrame>
}

export default QuestionEditDialog
