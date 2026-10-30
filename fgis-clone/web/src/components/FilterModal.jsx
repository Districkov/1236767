export default function FilterModal({ open, filters, onChange, onApply, onClear, onClose }) {
  if (!open) return null;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Фильтр (поиск по Все)</h2>
          <button className="close" type="button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="frow">
            <label>Организация-поверитель</label>
            <input value={filters.org} onChange={(e) => onChange("org", e.target.value)} />
          </div>

          <div className="frow">
            <label>Регистрационный номер типа СИ</label>
            <input value={filters.number} onChange={(e) => onChange("number", e.target.value)} />
          </div>

          <div className="frow">
            <label>Наименование типа СИ</label>
            <input value={filters.title} onChange={(e) => onChange("title", e.target.value)} />
          </div>

          <div className="frow">
            <label>Обозначение типа СИ</label>
            <input value={filters.notation} onChange={(e) => onChange("notation", e.target.value)} />
          </div>

          <div className="frow">
            <label>Модификация СИ</label>
            <input value={filters.modification} onChange={(e) => onChange("modification", e.target.value)} />
          </div>

          <div className="frow">
            <label>Заводской номер/ Буквенно-цифровое обозначение</label>
            <input value={filters.factory} onChange={(e) => onChange("factory", e.target.value)} />
          </div>

          <div className="frow">
            <label>Дата поверки</label>
            <div className="two">
              <input
                placeholder="ДД.ММ.ГГГГ"
                value={filters.dateFrom}
                onChange={(e) => onChange("dateFrom", e.target.value)}
              />
              <input
                placeholder="ДД.ММ.ГГГГ"
                value={filters.dateTo}
                onChange={(e) => onChange("dateTo", e.target.value)}
              />
            </div>
          </div>

          <div className="frow">
            <label>Действительна до</label>
            <div className="two">
              <input
                placeholder="ДД.ММ.ГГГГ"
                value={filters.validFrom}
                onChange={(e) => onChange("validFrom", e.target.value)}
              />
              <input
                placeholder="ДД.ММ.ГГГГ"
                value={filters.validTo}
                onChange={(e) => onChange("validTo", e.target.value)}
              />
            </div>
          </div>

          <div className="frow">
            <label>Номер свидетельства/ Номер извещения</label>
            <input value={filters.cert} onChange={(e) => onChange("cert", e.target.value)} />
          </div>

          <div className="frow">
            <label>Номер наклейки</label>
            <input value={filters.sticker} onChange={(e) => onChange("sticker", e.target.value)} />
          </div>

          <div className="frow">
            <label>Пригодность</label>
            <select value={filters.applicability} onChange={(e) => onChange("applicability", e.target.value)}>
              <option value="">Все</option>
              <option value="true">Да</option>
              <option value="false">Нет</option>
            </select>
          </div>
        </div>

        <div className="modal-foot">
          <button className="btn-gray" type="button" onClick={onClose}>
            Отмена
          </button>
          <div className="modal-foot-right">
            <button className="btn-teal" type="button" onClick={onApply}>
              Применить
            </button>
            <button className="btn-teal" type="button" onClick={onClear}>
              Очистить
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
