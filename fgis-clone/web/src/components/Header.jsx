export default function Header() {
  return (
    <header className="header">
      <div className="logo">
        <span className="logo-icon">
          <i></i>
          <i></i>
        </span>
        <span className="logo-text">
          <b>РСТ</b>
          <small>МЕТРОЛОГИЯ</small>
        </span>
      </div>

      <nav className="nav">
        <a className="nav-link" href="#">
          ФИБ ОЕИ
        </a>
        <a className="nav-link" href="#">
          ПОДДЕРЖКА
        </a>
      </nav>

      <div className="header-right">
        <button className="login-btn" type="button">
          Войти в личный кабинет
        </button>

        <a className="icon-btn" href="#" title="Поиск">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
          </svg>
        </a>

        <a className="icon-btn" href="#" title="На главную">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 11l9-8 9 8" />
            <path d="M5 10v10h14V10" />
          </svg>
        </a>
      </div>
    </header>
  );
}
