import StatusNotice from '../common/StatusNotice.jsx'
import DialogFrame from './DialogFrame.jsx'

const ConfirmDialog = ({ title, description, confirmText, onCancel, onConfirm }) => (
  <DialogFrame title={title} onClose={onCancel} labelledId="confirm-title">
    <StatusNotice type="warning">{description}</StatusNotice>
    <div className="modal-actions"><button className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" onClick={onConfirm}>{confirmText}</button></div>
  </DialogFrame>
)

export default ConfirmDialog
