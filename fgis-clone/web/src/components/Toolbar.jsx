export default function Toolbar({ reg, registries, onRegChange, query, onQueryChange, onSearch, onOpenFilter, onReset, onExport }) {
  return (
    <div className="toolbar">
      <select className="reg-select" value={reg} onChange={(e) => onRegChange(e.target.value)} title="Реестр">
        <option value="pov">Результаты поверок СИ</option>
        {registries.length > 0 ? (
          registries.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))
        ) : (
          <option value="4">Поверки СИ</option>
        )}
      </select>

      <label className="search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9aa0a6" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <line x1="16.5" y1="16.5" x2="21" y2="21" />
        </svg>
        <input
          type="text"
          placeholder="Поиск"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSearch();
          }}
        />
      </label>

      <button className="btn btn-search" type="button" onClick={onSearch}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#5b6167" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <line x1="16.5" y1="16.5" x2="21" y2="21" />
        </svg>
        Найти
      </button>

      <button className="btn" type="button" onClick={onOpenFilter}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#5b6167" strokeWidth="2">
          <path d="M3 5h18l-7 8v6l-4 2v-8z" />
        </svg>
        Настроить фильтр
      </button>

      <button className="btn" type="button" onClick={onReset}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#5b6167" strokeWidth="2">
          <line x1="5" y1="5" x2="19" y2="19" />
          <line x1="19" y1="5" x2="5" y2="19" />
        </svg>
        Сбросить фильтр
      </button>

      <button className="btn" type="button" onClick={onExport}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#5b6167" strokeWidth="2">
          <path d="M6 17a4 4 0 010-8 5 5 0 019.6-1.5A3.5 3.5 0 1117 17H6z" />
          <path d="M12 12v6" />
          <path d="M9.5 15.5L12 18l2.5-2.5" />
        </svg>
        Выгрузить
      </button>
    </div>
  );
}
