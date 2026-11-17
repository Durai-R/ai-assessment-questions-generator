const PageHeader = ({ eyebrow, title, description }) => (
  <div className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div></div>
)

export default PageHeader
