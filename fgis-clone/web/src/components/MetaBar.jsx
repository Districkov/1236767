export default function MetaBar({ total, page, rows, onRowsChange, onPageChange }) {
  const pages = Math.max(1, Math.ceil(total / rows));
  const from = total === 0 ? 0 : (page - 1) * rows + 1;
  const to = Math.min(page * rows, total);

  const numbers = [];
  for (let i = page; i < page + 3; i++) {
    if (i <= pages) numbers.push(i);
  }

  return (
    <div className="meta">
      <div className="meta-left">
        <span>
          {from} - {to} из {total}
        </span>
        <select className="rows-select" value={rows} onChange={(e) => onRowsChange(Number(e.target.value))}>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
        <span>на страницу</span>
      </div>

      <div className="pager">
        <button type="button" className="pager-btn" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          « Предыдущая
        </button>

        {numbers.map((n) => (
          <button
            key={n}
            type="button"
            className={"pager-num" + (n === page ? " active" : "")}
            onClick={() => onPageChange(n)}
          >
            {n}
          </button>
        ))}

        <button type="button" className="pager-btn" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
          Следующая »
        </button>
      </div>
    </div>
  );
}
