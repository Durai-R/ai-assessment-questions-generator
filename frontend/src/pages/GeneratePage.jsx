import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../utils/apiErrors.js'
import { questionService } from '../services/questionService.js'
import { topicService } from '../services/topicService.js'
import { DIFFICULTIES, ROUTES } from '../constants/app.js'
import { makeId, normalizeQuestion } from '../utils/questions.js'
import ConfirmDialog from '../components/questions/ConfirmDialog.jsx'
import QuestionEditDialog from '../components/questions/QuestionEditDialog.jsx'
import QuestionsTable from '../components/questions/QuestionsTable.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import Spinner from '../components/common/Spinner.jsx'
import StatusNotice from '../components/common/StatusNotice.jsx'

const GeneratePage = () => {
  const [subject, setSubject] = useState('')
  const [topics, setTopics] = useState([])
  const [topic, setTopic] = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [difficulty, setDifficulty] = useState('Medium')
  const [count, setCount] = useState('5')
  const [topicPending, setTopicPending] = useState(false)
  const [operation, setOperation] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [notice, setNotice] = useState('')
  const [drafts, setDrafts] = useState([])
  const [batch, setBatch] = useState(null)
  const [edited, setEdited] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [confirmReplace, setConfirmReplace] = useState(false)
  const topicRequestId = useRef(0)
  const topicRequestLock = useRef(false)
  const operationLock = useRef(false)
  const navigate = useNavigate()
  const currentTopic = topic === '__custom__' ? customTopic.trim() : topic
  const validCount = count !== '' && /^\d+$/.test(count) && Number(count) >= 1 && Number(count) <= 30
  const hasPipelineOperation = Boolean(operation)

  const changeSubject = (value) => {
    setSubject(value)
    setTopics([])
    setTopic('')
    setCustomTopic('')
    topicRequestId.current += 1
    setError('')
    setFieldErrors((current) => ({ ...current, subject: '' }))
  }

  const generateTopics = async () => {
    const requestedSubject = subject.trim()
    if (topicPending || topicRequestLock.current) return
    if (!requestedSubject) {
      setFieldErrors((current) => ({ ...current, subject: 'Enter a subject before generating topics.' }))
      return
    }
    const requestId = ++topicRequestId.current
    topicRequestLock.current = true
    setTopicPending(true)
    setError('')
    setTopics([])
    setTopic('')
    try {
      const result = await topicService.suggestTopics(requestedSubject)
      if (requestId === topicRequestId.current && requestedSubject === subject.trim()) {
        setTopics(Array.isArray(result?.topics) ? result.topics : [])
        if (!Array.isArray(result?.topics)) setError('The topics response was not in the expected format. Please retry.')
      }
    } catch (requestError) {
      if (requestId === topicRequestId.current) setError(getErrorMessage(requestError))
    } finally {
      topicRequestLock.current = false
      setTopicPending(false)
    }
  }

  const validForm = () => {
    const nextFieldErrors = {}
    if (!subject.trim()) nextFieldErrors.subject = 'Enter a subject before generating topics.'
    if (!topic || !currentTopic) nextFieldErrors.topic = 'Choose a topic or enter a custom topic.'
    if (!validCount) nextFieldErrors.count = 'Enter a whole number from 1 to 30.'
    setFieldErrors(nextFieldErrors)
    if (Object.keys(nextFieldErrors).length) {
      setError('')
      return false
    }
    return true
  }

  const generate = async (payload, replacing = false) => {
    if (operationLock.current) return
    if (!replacing && !validForm()) return
    operationLock.current = true
    setError('')
    setOperation(replacing ? 'regenerate' : 'generate')
    try {
      const result = await questionService.generateQuestions(payload)
      if (!Array.isArray(result?.questions)) throw new Error('The questions response was not in the expected format. Please retry.')
      setDrafts(result.questions.map((question) => ({ ...normalizeQuestion(question), local_id: makeId() })))
      setBatch(payload)
      setEdited(false)
      setNotice('')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      operationLock.current = false
      setOperation('')
    }
  }

  const requestGenerate = (event) => {
    event.preventDefault()
    if (operationLock.current) return
    if (!validForm()) return
    const payload = { subject: subject.trim(), topic: currentTopic, difficulty, count: Number(count) }
    generate(payload)
  }

  const requestRegenerate = () => {
    if (!batch || hasPipelineOperation || operationLock.current) return
    if (edited) setConfirmReplace(true)
    else performRegenerate()
  }

  const performRegenerate = () => {
    setConfirmReplace(false)
    generate(batch, true)
  }

  const saveAll = async () => {
    if (!batch || !drafts.length || operationLock.current) return
    operationLock.current = true
    setError('')
    setOperation('save')
    try {
      await questionService.saveQuestions({
        subject: batch.subject,
        topic: batch.topic,
        difficulty: batch.difficulty,
        questions: drafts.map(({ question_text, options, correct_option_index, explanation }) => ({
          question_text, options, correct_option_index, explanation,
        })),
      })
      const savedCount = drafts.length
      navigate(ROUTES.questions, { state: { notice: `${savedCount} ${savedCount === 1 ? 'question' : 'questions'} saved to All Questions.` } })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      operationLock.current = false
      setOperation('')
    }
  }

  const saveEdit = (updated) => {
    if (editItem?.local_id) {
      setDrafts((current) => current.map((row) => row.local_id === editItem.local_id ? { ...row, ...updated } : row))
      setBatch((current) => current ? {
        ...current,
        subject: updated.subject,
        topic: updated.topic,
        difficulty: updated.difficulty,
      } : current)
      setEdited(true)
      setNotice('Question updated.')
    }
    setEditItem(null)
  }

  return (
    <>
      <PageHeader eyebrow="CREATE" title="Generate questions" description="Create a focused question set and review every detail before saving." />
      <section className="panel generation-panel">
        <div className="section-title"><div><h2>Question details</h2><p>Choose a subject and let AI help you find a starting point.</p></div><span className="step-pill">STEP 01 <i /> BUILD</span></div>
        <form className="generation-form" onSubmit={requestGenerate} noValidate>
          <div className="field subject-field">
            <label htmlFor="subject">Subject <span className="required">*</span></label>
            <div className="subject-control"><input id="subject" value={subject} onChange={(event) => changeSubject(event.target.value)} placeholder="e.g. Frontend development" required aria-invalid={Boolean(fieldErrors.subject)} aria-describedby={fieldErrors.subject ? 'subject-error' : undefined} />
              <button className="button secondary" type="button" onClick={generateTopics} disabled={topicPending || topicRequestLock.current}>
                {topicPending ? <><Spinner /> Generating topics…</> : <><span aria-hidden="true">✧</span> Generate topics</>}
              </button>
            </div>
            {fieldErrors.subject && <small className="field-error" id="subject-error">{fieldErrors.subject}</small>}
            <small>Enter the subject you want to assess.</small>
          </div>
          <div className="field">
            <label htmlFor="topic">Topic <span className="required">*</span></label>
            <select id="topic" value={topic} onChange={(event) => { setTopic(event.target.value); setFieldErrors((current) => ({ ...current, topic: '' })) }} required aria-invalid={Boolean(fieldErrors.topic)} aria-describedby={fieldErrors.topic ? 'topic-error' : undefined}>
              <option value="">Select a topic</option>
              {topics.map((item, index) => <option value={item} key={`${item}-${index}`}>{item}</option>)}
              <option value="__custom__">Custom topic</option>
            </select>
            {fieldErrors.topic && <small className="field-error" id="topic-error">{fieldErrors.topic}</small>}
            {topic === '__custom__' && <><label htmlFor="custom-topic">Custom topic <span className="required">*</span></label><input id="custom-topic" className="custom-topic" value={customTopic} onChange={(event) => { setCustomTopic(event.target.value); setFieldErrors((current) => ({ ...current, topic: '' })) }} placeholder="Enter a custom topic" required /></>}
          </div>
          <div className="field">
            <label htmlFor="difficulty">Difficulty</label>
            <select id="difficulty" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>{DIFFICULTIES.map((item) => <option key={item}>{item}</option>)}</select>
          </div>
          <div className="field">
            <label htmlFor="count">Number of questions <span className="required">*</span></label>
            <input id="count" type="number" min="1" max="30" step="1" value={count} onChange={(event) => { setCount(event.target.value); setFieldErrors((current) => ({ ...current, count: '' })) }} required aria-invalid={Boolean(fieldErrors.count)} aria-describedby={fieldErrors.count ? 'count-error' : undefined} />
            {fieldErrors.count && <small className="field-error" id="count-error">{fieldErrors.count}</small>}
            <small>Choose between 1 and 30 questions.</small>
          </div>
          {error && <StatusNotice type="error" className="form-notice">{error}</StatusNotice>}
          <div className="form-actions"><span className="privacy-note"><span aria-hidden="true">◈</span> AI-generated drafts are only saved when you choose to save them.</span>
            <button className="button primary" type="submit" disabled={hasPipelineOperation || operationLock.current}>
              {operation === 'generate' ? <><Spinner /> Generating questions…</> : <><span aria-hidden="true">✦</span> Generate questions</>}
            </button>
          </div>
        </form>
      </section>
      <section className="draft-section">
        {notice && <StatusNotice type="success" className="page-notice" onDismiss={() => setNotice('')}>{notice}</StatusNotice>}
        <div className="list-heading"><div><p className="eyebrow">YOUR WORK</p><h2>Draft questions <span className="count-badge">{drafts.length}</span></h2></div>
          {drafts.length > 0 && <div className="batch-actions">
            <button className="button secondary" onClick={requestRegenerate} disabled={hasPipelineOperation || operationLock.current || !batch}>{operation === 'regenerate' ? <><Spinner /> Regenerating…</> : <><span aria-hidden="true">↻</span> Regenerate</>}</button>
            <button className="button primary" onClick={saveAll} disabled={!drafts.length || hasPipelineOperation}>{operation === 'save' ? <><Spinner /> Saving questions…</> : 'Save all questions'}</button>
          </div>}
        </div>
        {drafts.length === 0 ? <div className="empty-panel"><div className="empty-icon">✦</div><h3>Your drafts will appear here</h3><p>Fill in the details above and generate your first set of questions.</p></div> :
          <QuestionsTable showMetadata={false} questions={drafts} onEdit={(row) => setEditItem(row)} onDelete={(row) => { setDrafts((current) => current.filter((item) => item.local_id !== row.local_id)); setEdited(true); setNotice('Question deleted.') }} />}
      </section>
      {editItem && <QuestionEditDialog question={{ ...editItem, subject: batch?.subject, topic: batch?.topic, difficulty: batch?.difficulty }} sharedMetadata onClose={() => setEditItem(null)} onSave={saveEdit} />}
      {confirmReplace && <ConfirmDialog title="Replace your draft?" description="Replace this draft? Your edits to the current questions will be lost." confirmText="Replace draft" onCancel={() => setConfirmReplace(false)} onConfirm={performRegenerate} />}
    </>
  )
}

export default GeneratePage
