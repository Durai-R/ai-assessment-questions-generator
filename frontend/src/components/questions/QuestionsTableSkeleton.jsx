const QuestionsTableSkeleton = () => (
  <div className="table-scroll table-skeleton" role="status" aria-label="Loading questions">
    <span className="sr-only">Loading questions…</span>
    <table className="questions-table" aria-hidden="true">
      <thead><tr><th>Subject</th><th>Topic</th><th>Question</th><th>Answer options</th><th>Correct answer</th><th>Explanation</th><th>Actions</th></tr></thead>
      <tbody>{Array.from({ length: 5 }, (_, row) => <tr key={row}>
        {Array.from({ length: 7 }, (_, column) => <td key={column}><span className={`skeleton-line skeleton-${column}`} /></td>)}
      </tr>)}</tbody>
    </table>
  </div>
)

export default QuestionsTableSkeleton
