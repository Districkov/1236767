import { useEffect, useState } from "react";
import Header from "./components/Header.jsx";
import Hero from "./components/Hero.jsx";
import YearTabs from "./components/YearTabs.jsx";
import Toolbar from "./components/Toolbar.jsx";
import MetaBar from "./components/MetaBar.jsx";
import ResultsTable from "./components/ResultsTable.jsx";
import FilterModal from "./components/FilterModal.jsx";
import CardPage from "./components/CardPage.jsx";
import { csvUrl, getCard, getHealth, getTree, searchRegistry } from "./api.js";
import { pick } from "./helpers.js";

function errorHint(error) {
  if (/Локальный сервер не запущен|Failed to fetch|NetworkError/i.test(error)) {
    return "Сервер не отвечает. Запустите python server.py и откройте http://127.0.0.1:8017";
  }
  if (/ERR |HTTP 0|timed out|SSL/i.test(error)) {
    return "Нет доступа к fgis.gost.ru: таймаут или ошибка TLS. Нужен российский IP или VPN.";
  }
  if (/HTTP 4|HTTP 5|Forbidden|сбой на сервере/i.test(error)) {
    return "Сайт ответил ошибкой. Нажмите «проверить соединение» и посмотрите подробности.";
  }
  return "Проверьте, что python server.py запущен в этой же папке.";
}

const EMPTY_FILTERS = {
  org: "",
  number: "",
  title: "",
  notation: "",
  modification: "",
  factory: "",
  dateFrom: "",
  dateTo: "",
  validFrom: "",
  validTo: "",
  cert: "",
  sticker: "",
  applicability: "",
};

export default function App() {
  const [reg, setReg] = useState("pov");
  const [registries, setRegistries] = useState([]);
  const [year, setYear] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState(20);

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState({});
  const [showFilter, setShowFilter] = useState(false);

  const [items, setItems] = useState([]);
  const [columns, setColumns] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [demo, setDemo] = useState(false);

  const [card, setCard] = useState(null);
  const [health, setHealth] = useState(null);
  const [sort, setSort] = useState({ key: "", dir: "asc" });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    searchRegistry({ reg, year, query, page, rows, filters: applied, sort }).then((data) => {
      if (cancelled) return;
      setItems(data.items || []);
      setColumns(data.columns || []);
      setTotal(data.total || 0);
      setDemo(!!data.demo);
      setError(data.error || "");
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [reg, year, query, page, rows, applied, sort]);

  useEffect(() => {
    const openId = new URLSearchParams(window.location.search).get("open");
    if (openId) {
      getCard("pov", openId).then((data) => {
        if (data.card) setCard(data.card);
      });
    }
  }, []);

  useEffect(() => {
    getTree().then((data) => {
      if (data.registries && data.registries.length) setRegistries(data.registries);
    });
  }, []);

  function changeFilter(field, value) {
    setFilters({ ...filters, [field]: value });
  }

  function applyFilters() {
    setApplied(filters);
    setPage(1);
    setShowFilter(false);
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setApplied({});
    setPage(1);
    setShowFilter(false);
  }

  function resetAll() {
    setFilters(EMPTY_FILTERS);
    setApplied({});
    setQuery("");
    setYear("all");
    setPage(1);
  }

  function openCard(item) {
    if (demo) {
      setCard({ raw: item, fields: [] });
      return;
    }

    const id = (item.raw && item.raw.id) || pick(item, "vri_id", "id");
    if (!id) {
      setCard({ raw: item, fields: [] });
      return;
    }

    getCard(reg, id).then((data) => {
      if (data.card) setCard(data.card);
      else setCard({ raw: item, fields: [] });
    });
  }

  function toggleSort(key) {
    if (sort.key === key) {
      setSort({ key, dir: sort.dir === "asc" ? "desc" : "asc" });
    } else {
      setSort({ key, dir: "asc" });
    }
  }

  function valueOf(item, key) {
    if (item.cells && item.cells[key]) return item.cells[key];
    return pick(item, key);
  }

  const sortedItems = reg === "pov" ? items : [...items].sort((a, b) => {
    if (!sort.key) return 0;
    const av = String(valueOf(a, sort.key));
    const bv = String(valueOf(b, sort.key));
    return sort.dir === "asc" ? av.localeCompare(bv, "ru") : bv.localeCompare(av, "ru");
  });

  return (
    <>
      <Header />
      <Hero />

      {card ? (
        <div className="content">
          <CardPage card={card} onBack={() => setCard(null)} />
        </div>
      ) : (
        <div className="content">
          <YearTabs
            value={year}
            onChange={(value) => {
              setYear(value);
              setPage(1);
            }}
          />

          <Toolbar
            reg={reg}
            registries={registries}
            onRegChange={(value) => {
              setReg(value);
              setPage(1);
            }}
            query={query}
            onQueryChange={setQuery}
            onSearch={() => setPage(1)}
            onOpenFilter={() => setShowFilter(true)}
            onReset={resetAll}
            onExport={() => {
              window.location.href = csvUrl({ reg, query, filters: applied });
            }}
          />

          <MetaBar
            total={total}
            page={page}
            rows={rows}
            demo={demo}
            onRowsChange={(value) => {
              setRows(value);
              setPage(1);
            }}
            onPageChange={setPage}
          />

          {error && (
            <div className={"banner " + (demo ? "banner-error" : "banner-info")}>
              <b>{demo ? "Данные с fgis.gost.ru не получены:" : "Ошибка запроса:"}</b> {error}
              <div className="banner-hint">{errorHint(error)}</div>
              <button
                className="link-btn"
                type="button"
                onClick={() => getHealth().then(setHealth)}
              >
                проверить соединение
              </button>
              {health && (
                <pre className="health">{JSON.stringify(health, null, 2)}</pre>
              )}
            </div>
          )}

          <ResultsTable
            items={sortedItems}
            loading={loading}
            columns={columns}
            onOpen={openCard}
            sort={sort}
            onSort={toggleSort}
          />
        </div>
      )}

      <footer className="footer">Локальное зеркало ФГИС «Аршин» · данные с fgis.gost.ru</footer>

      <FilterModal
        open={showFilter}
        filters={filters}
        onChange={changeFilter}
        onApply={applyFilters}
        onClear={clearFilters}
        onClose={() => setShowFilter(false)}
      />
    </>
  );
}
