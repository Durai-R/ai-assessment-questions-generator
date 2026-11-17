import Spinner from '../common/Spinner.jsx'
import StatusNotice from '../common/StatusNotice.jsx'
import DialogFrame from './DialogFrame.jsx'

const DeleteQuestionDialog = ({ question, pending, error, onCancel, onConfirm }) => (
  <DialogFrame title="Delete question?" onClose={onCancel} labelledId="delete-title">
    <StatusNotice type="warning">This will permanently remove this question from your library. This action can’t be undone.</StatusNotice>
    <div className="delete-preview">{question.question_text}</div>
    {error && <StatusNotice type="error">{error}</StatusNotice>}
    <div className="modal-actions"><button className="button secondary" onClick={onCancel} disabled={pending}>Cancel</button><button className="button danger" onClick={onConfirm} disabled={pending}>{pending ? <><Spinner /> Deleting question…</> : 'Delete question'}</button></div>
  </DialogFrame>
)

export default DeleteQuestionDialog
