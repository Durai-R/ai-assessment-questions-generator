import { LETTERS } from '../../constants/app.js'
import { normalizeQuestion } from '../../utils/questions.js'

const QuestionsTable = ({ questions, onEdit, onDelete, showMetadata = true }) => (
  <div className="table-scroll">
    <table className="questions-table">
      <thead><tr>{showMetadata && <><th>Subject</th><th>Topic</th></>}<th>Question</th><th>Answer options</th><th>Correct answer</th><th>Explanation</th><th><span className="sr-only">Actions</span></th></tr></thead>
      <tbody>{questions.map((rawQuestion) => {
        const question = normalizeQuestion(rawQuestion)
        return <tr key={question.local_id || question.id || question.question_text}>
          {showMetadata && <><td><span className="cell-primary">{question.subject || '—'}</span>{question.difficulty && <span className="difficulty-tag">{question.difficulty}</span>}</td>
          <td>{question.topic || '—'}</td></>}
          <td className="question-cell">{question.question_text}</td>
          <td><div className="options-list">{question.options.map((option, index) => <div key={index}><b>{LETTERS[index]}.</b> {option}</div>)}</div></td>
          <td><span className="correct-answer"><b>{LETTERS[question.correct_option_index] || '—'}</b><span>{question.options[question.correct_option_index] || '—'}</span></span></td>
          <td className="explanation-cell">{question.explanation || '—'}</td>
          <td><div className="row-actions">
            <button className="icon-button" aria-label="Edit question" title="Edit question" onClick={() => onEdit(question)}><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m13.8 3.2 3 3-9.7 9.7-4.1 1.1 1.1-4.1 9.7-9.7Z" /><path d="m11.9 5.1 3 3" /></svg></button>
            <button className="icon-button danger-icon" aria-label="Delete question" title="Delete question" onClick={() => onDelete(question)}><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 5.5h13M8 5.5V3.7h4v1.8m-6.8 0 .7 11h7.2l.7-11M8.2 8.3v5.5m3.6-5.5v5.5" /></svg></button>
          </div></td>
        </tr>
      })}</tbody>
    </table>
  </div>
)

export default QuestionsTable
