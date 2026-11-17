import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../utils/apiErrors.js'
import { questionService } from '../services/questionService.js'
import { DIFFICULTIES, QUESTIONS_PAGE_SIZE } from '../constants/app.js'
import { normalizeQuestion } from '../utils/questions.js'
import DeleteQuestionDialog from '../components/questions/DeleteQuestionDialog.jsx'
import Pagination from '../components/questions/Pagination.jsx'
import QuestionEditDialog from '../components/questions/QuestionEditDialog.jsx'
import QuestionsTable from '../components/questions/QuestionsTable.jsx'
import QuestionsTableSkeleton from '../components/questions/QuestionsTableSkeleton.jsx'
import PageHeader from '../components/common/PageHeader.jsx'
import Spinner from '../components/common/Spinner.jsx'
import StatusNotice from '../components/common/StatusNotice.jsx'

const QuestionsPage = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [subject, setSubject] = useState('')
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [subjects, setSubjects] = useState([])
  const [topics, setTopics] = useState([])
  const [optionsError, setOptionsError] = useState('')
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [refresh, setRefresh] = useState(0)
  const [editItem, setEditItem] = useState(null)
  const [deleteItem, setDeleteItem] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!location.state?.notice) return
    setNotice(location.state.notice)
    navigate(location.pathname, { replace: true, state: null })
  }, [location, navigate])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, subject, topic, difficulty])

  useEffect(() => {
    let active = true
    setOptionsError('')
    questionService.filterOptions(subject).then((result) => {
      if (!active) return
      if (!subject) setSubjects(Array.isArray(result?.subjects) ? result.subjects : [])
      setTopics(Array.isArray(result?.topics) ? result.topics : [])
    }).catch((requestError) => {
      if (active) setOptionsError(getErrorMessage(requestError))
    })
    return () => { active = false }
  }, [subject])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams()
    if (debouncedSearch) params.set('search', debouncedSearch)
    if (subject) params.set('subject', subject)
    if (topic) params.set('topic', topic)
    if (difficulty) params.set('difficulty', difficulty)
    params.set('page', String(page))
    params.set('page_size', String(QUESTIONS_PAGE_SIZE))
    setLoading(true)
    setError('')
    questionService.listQuestions(params, controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (!Array.isArray(result?.items) || !Number.isFinite(Number(result?.total))) {
        throw new Error('The questions response was not in the expected format.')
      }
      setRows(result.items.map(normalizeQuestion))
      setTotal(Number(result.total))
    }).catch((requestError) => {
      if (controller.signal.aborted || requestError.name === 'AbortError') return
      setError(getErrorMessage(requestError))
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [debouncedSearch, subject, topic, difficulty, page, retry, refresh])

  const pageCount = Math.max(1, Math.ceil(total / QUESTIONS_PAGE_SIZE))
  const hasFilters = Boolean(search.trim() || subject || topic || difficulty)
  const pageNumbers = useMemo(() => {
    const start = Math.max(1, Math.min(page - 2, pageCount - 4))
    return Array.from({ length: Math.min(5, pageCount) }, (_, index) => start + index)
  }, [page, pageCount])

  const clearFilters = () => {
    setSearch('')
    setSubject('')
    setTopic('')
    setDifficulty('')
  }

  const saveQuestion = async (updated) => {
    try {
      const payload = {
        question_text: updated.question_text,
        options: updated.options,
        correct_option_index: updated.correct_option_index,
        explanation: updated.explanation,
        subject: updated.subject,
        topic: updated.topic,
        difficulty: updated.difficulty,
      }
      await questionService.updateQuestion(editItem.id, payload)
      setEditItem(null)
      setNotice('Question updated.')
      setRefresh((value) => value + 1)
    } catch (requestError) {
      return getErrorMessage(requestError)
    }
    return ''
  }

  const confirmDelete = async () => {
    if (!deleteItem || deleting) return
    setDeleting(true)
    setDeleteError('')
    try {
      await questionService.deleteQuestion(deleteItem.id)
      setDeleteItem(null)
      setNotice('Question deleted.')
      if (rows.length === 1 && page > 1) setPage((value) => value - 1)
      else setRefresh((value) => value + 1)
    } catch (requestError) {
      setDeleteError(getErrorMessage(requestError))
    } finally {
      setDeleting(false)
    }
  }

  let questionResults
  if (loading && rows.length === 0) questionResults = <QuestionsTableSkeleton />
  else if (error) {
    questionResults = <div className="empty-panel state-panel">
      <div className="empty-icon warning">!</div><h3>We couldn’t load your questions</h3><p>{error}</p>
      <button className="button secondary" onClick={() => setRetry((value) => value + 1)}>Retry</button>
    </div>
  } else if (rows.length === 0) {
    questionResults = <div className="empty-panel state-panel">
      <div className="empty-icon">{hasFilters ? '⌕' : '☷'}</div>
      <h3>{hasFilters ? 'No matching questions' : 'Your question bank is empty'}</h3>
      <p>{hasFilters ? 'Try adjusting your search or filters to find what you need.' : 'Questions you save from the generator will show up here.'}</p>
      {hasFilters && <button className="button secondary" onClick={clearFilters}>Clear filters</button>}
    </div>
  } else {
    questionResults = <div className="table-region">
      {loading && <div className="table-loading" role="status"><Spinner /> Updating results…</div>}
      <QuestionsTable questions={rows} onEdit={(row) => setEditItem(row)} onDelete={(row) => { setDeleteItem(row); setDeleteError('') }} />
    </div>
  }

  return (
    <>
      <PageHeader eyebrow="LIBRARY" title="All questions" description="Search, filter, and manage every question in your library." />
      <section className="panel filters-panel">
        <div className="filter-toolbar">
          <label className="field search-field"><span>Search questions</span><span className="search-wrap"><span aria-hidden="true">⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by question text…" /></span></label>
          <label className="field"><span>Subject</span><select value={subject} onChange={(event) => { setSubject(event.target.value); setTopic('') }}><option value="">All subjects</option>{subjects.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field"><span>Topic</span><select value={topic} onChange={(event) => setTopic(event.target.value)}><option value="">All topics</option>{topics.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field"><span>Difficulty</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="">All difficulties</option>{DIFFICULTIES.map((item) => <option key={item}>{item}</option>)}</select></label>
        </div>
        {optionsError && <StatusNotice type="error" className="filter-error">{optionsError}</StatusNotice>}
      </section>
      <div className="results-heading"><div><h2>Question bank</h2><span className="results-count">{total} {total === 1 ? 'question' : 'questions'}</span></div>
        {hasFilters && <button className="text-button" onClick={clearFilters}>Clear filters <span aria-hidden="true">×</span></button>}
      </div>
      {notice && <StatusNotice type="success" className="page-notice" onDismiss={() => setNotice('')}>{notice}</StatusNotice>}
      {questionResults}
      {!loading && !error && rows.length > 0 && <Pagination page={page} pageCount={pageCount} pageNumbers={pageNumbers} total={total} pageSize={QUESTIONS_PAGE_SIZE} onPage={setPage} />}
      {editItem && <QuestionEditDialog key={editItem.local_id || editItem.id} question={editItem} onClose={() => setEditItem(null)} onSave={saveQuestion} />}
      {deleteItem && <DeleteQuestionDialog question={deleteItem} pending={deleting} error={deleteError} onCancel={() => { if (!deleting) setDeleteItem(null) }} onConfirm={confirmDelete} />}
    </>
  )
}

export default QuestionsPage
