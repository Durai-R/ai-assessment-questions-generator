import { useRef } from 'react'
import useDialogFocus from '../../hooks/useDialogFocus.js'

const DialogFrame = ({ title, children, onClose, wide = false, labelledId }) => {
  const dialogRef = useRef(null)
  useDialogFocus(dialogRef, onClose)
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby={labelledId} ref={dialogRef}>
      <div className="modal-header"><div><p className="eyebrow">QUESTION DETAILS</p><h2 id={labelledId}>{title}</h2></div><button className="icon-button close-button" aria-label="Close dialog" onClick={onClose}>×</button></div>
      {children}
    </section>
  </div>
}

export default DialogFrame
