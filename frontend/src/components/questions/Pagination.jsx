const Pagination = ({ page, pageCount, pageNumbers, total, pageSize, onPage }) => {
  const firstItem = total === 0 ? 0 : (page - 1) * pageSize + 1
  const lastItem = Math.min(page * pageSize, total)
  return <div className="pagination">
    <p>Showing <strong>{firstItem}–{lastItem}</strong> of <strong>{total}</strong></p>
    <nav aria-label="Pagination">
      <button className="page-arrow" aria-label="Previous page" onClick={() => onPage(page - 1)} disabled={page <= 1}>‹ <span>Previous</span></button>
      {pageNumbers.map((number) => <button key={number} className={`page-number ${number === page ? 'selected' : ''}`} aria-current={number === page ? 'page' : undefined} onClick={() => onPage(number)}>{number}</button>)}
      <button className="page-arrow" aria-label="Next page" onClick={() => onPage(page + 1)} disabled={page >= pageCount}><span>Next</span> ›</button>
    </nav>
  </div>
}

export default Pagination
