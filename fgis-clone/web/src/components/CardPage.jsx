import { CARD_LABELS, CARD_SECTIONS, formatDate } from "../helpers.js";

function formatValue(key, value) {
  if (key === "verification_date" || key === "valid_date") return formatDate(value);
  if (key === "applicability") {
    if (value === true || value === "true") return "Да";
    if (value === false || value === "false") return "Нет";
  }
  return String(value);
}

function buildSections(card) {
  const raw = card.raw || {};
  const sections = [];

  CARD_SECTIONS.forEach((section) => {
    const rows = section.keys
      .filter((key) => raw[key] !== undefined && raw[key] !== null && raw[key] !== "")
      .map((key) => ({ label: CARD_LABELS[key] || key, value: formatValue(key, raw[key]) }));

    if (rows.length) sections.push({ title: section.title, rows });
  });

  const used = CARD_SECTIONS.reduce((all, s) => all.concat(s.keys), []);
  const rest = Object.keys(raw)
    .filter((key) => used.indexOf(key) === -1 && key !== "means")
    .filter((key) => typeof raw[key] !== "object")
    .map((key) => ({ label: CARD_LABELS[key] || key, value: formatValue(key, raw[key]) }));

  if (rest.length) sections.push({ title: "Прочие сведения", rows: rest });

  if (!sections.length && card.fields) {
    sections.push({
      title: "Сведения о поверке",
      rows: card.fields.map(([label, value]) => ({ label, value })),
    });
  }

  if (raw.means) {
    sections.push({ title: "Средства поверки", rows: [], text: String(raw.means) });
  }

  return sections;
}

export default function CardPage({ card, onBack }) {
  const sections = card.sections && card.sections.length ? card.sections : buildSections(card);

  return (
    <div className="card-page">
      <button className="back" type="button" onClick={onBack}>
        ← Назад к результатам
      </button>

      {sections.map((section) => (
        <section className="panel" key={section.title}>
          <h2 className="panel-title">{section.title}</h2>

          {section.rows.length > 0 && (
            <table className="card-table">
              <tbody>
                {section.rows.map((row, i) => {
                  const label = Array.isArray(row) ? row[0] : row.label;
                  const value = Array.isArray(row) ? row[1] : row.value;
                  return (
                    <tr key={i}>
                      <th>{label}</th>
                      <td>{value}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {section.text && <div className="panel-text">{section.text}</div>}
        </section>
      ))}
    </div>
  );
}
