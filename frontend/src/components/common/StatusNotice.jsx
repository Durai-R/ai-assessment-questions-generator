const StatusNotice = ({ type, children, className = '', onDismiss }) => {
  const label = { error: 'Error', success: 'Success', warning: 'Warning', info: 'Notice' }[type] || 'Notice'
  return <div className={`notice ${type} ${className}`} role={type === 'error' ? 'alert' : 'status'} aria-live={type === 'error' ? 'assertive' : 'polite'}>
    <span className="notice-label">{label}</span>
    <span>{children}</span>
    {onDismiss && <button className="notice-dismiss" type="button" onClick={onDismiss} aria-label="Dismiss notification">×</button>}
  </div>
}

export default StatusNotice
