import { COLUMNS, formatDate, pick } from "../helpers.js";

function fallbackCell(item, key) {
  if (key === "verification_date" || key === "valid_date") return formatDate(pick(item, key));
  if (key === "applicability") {
    const value = pick(item, "applicability", "status");
    if (value === false || value === "false") return "";
    return value === "" ? "" : "✓";
  }
  if (key === "mit_modification") return pick(item, "mit_modification") || "Нет модификации";
  return pick(item, key);
}

export default function ResultsTable({ items, loading, columns, onOpen, sort, onSort }) {
  if (loading) {
    return (
      <div className="table-wrap">
        <div className="empty">
          <span className="spinner"></span> запрос к fgis.gost.ru…
        </div>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="table-wrap">
        <div className="empty">Ничего не найдено</div>
      </div>
    );
  }

  const dynamic = Array.isArray(columns) && columns.length > 0;
  const cols = dynamic ? columns.slice(0, 12) : COLUMNS;

  return (
    <div className="table-wrap">
      <table className="results">
        <thead>
          <tr>
            {cols.map((col, index) => (
              <th
                key={col.key || index}
                style={!dynamic ? { width: col.width } : undefined}
                onClick={() => onSort(col.key)}
              >
                <span className="th-label">{dynamic ? col.title : col.label}</span>
                <span className={"sort" + (sort.key === col.key ? " on" : "")}>
                  {sort.key === col.key && sort.dir === "desc" ? "▼" : "▲"}
                </span>
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {items.map((item, index) => (
            <tr key={index} onClick={() => onOpen(item)}>
              {cols.map((col, i) => (
                <td key={col.key || i} className={col.key === "applicability" ? "center" : ""}>
                  {dynamic ? (item.cells && item.cells[col.key]) || "" : fallbackCell(item, col.key)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
