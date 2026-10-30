
const DEMO_ITEMS = [
  {
    mit_title: "Тахографы",
    mit_notation: "Меркурий ТА-001",
    mit_number: "65015-16",
    mit_modification: "Нет модификации",
    mit_factory_num: "0000125810",
    verification_date: "2026-10-25",
    valid_date: "2033-10-24",
    org_title: 'ЗАО "ЭТИМ"',
    sign_cipher: "С-ГГХ/25-10-2026/568493099",
    applicability: true,
  },
  {
    mit_title: "Тахографы цифровые",
    mit_notation: "Drive 5",
    mit_number: "62918-15",
    mit_modification: "Нет модификации",
    mit_factory_num: "8539732066",
    verification_date: "2026-10-25",
    valid_date: "2033-10-24",
    org_title: 'ЗАО "ЭТИМ"',
    sign_cipher: "С-ГГХ/25-10-2026/568493096",
    applicability: true,
  },
  {
    mit_title: "Тахографы цифровые",
    mit_notation: "Drive Smart",
    mit_number: "62923-15",
    mit_modification: "Нет модификации",
    mit_factory_num: "19C-480027601603F3",
    verification_date: "2026-10-25",
    valid_date: "2033-10-24",
    org_title: 'ЗАО "ЭТИМ"',
    sign_cipher: "С-ГГХ/25-10-2026/568493095",
    applicability: true,
  },
  {
    mit_title: "Тахографы",
    mit_notation: "ШТРИХ ТахоРУС",
    mit_number: "62921-15",
    mit_modification: "SIM 100.42.00.00.14",
    mit_factory_num: "00206897/05/17/18/6A",
    verification_date: "2026-10-25",
    valid_date: "2033-10-24",
    org_title: 'ЗАО "ЭТИМ"',
    sign_cipher: "С-ГГХ/25-10-2026/568493099",
    applicability: true,
  },
];

export async function searchRegistry({ reg, year, query, page, rows, filters, sort }) {
  const params = new URLSearchParams({
    reg: reg || "4",
    q: query || "",
    page: String(page),
    rows: String(rows),
    year: year || "",
    filters: JSON.stringify(filters || {}),
  });
  if (sort && sort.key) {
    params.set("sort", sort.key);
    params.set("dir", sort.dir || "asc");
  }

  try {
    const res = await fetch("/api/search?" + params.toString());
    const data = await res.json();

    if (!data.items || data.items.length === 0) {
      if (!data.error) {
        return { items: [], total: 0, demo: false, error: "" };
      }
      return { items: DEMO_ITEMS, total: 74392927, demo: true, error: data.error };
    }
    return { ...data, demo: false };
  } catch (e) {
    return {
      items: DEMO_ITEMS,
      total: 74392927,
      demo: true,
      error: "Локальный сервер не запущен (" + e.message + ")",
    };
  }
}

export async function getCard(reg, id) {
  const res = await fetch("/api/card?reg=" + (reg || "4") + "&id=" + encodeURIComponent(id));
  return res.json();
}

export async function getHealth() {
  try {
    const res = await fetch("/api/health");
    return await res.json();
  } catch (e) {
    return { server: false, error: e.message };
  }
}

export async function getTree() {
  const res = await fetch("/api/tree");
  return res.json();
}

export function csvUrl({ reg, query, filters }) {
  const params = new URLSearchParams({
    reg: reg || "4",
    q: query || "",
    filters: JSON.stringify(filters || {}),
    pages: "5",
  });
  return "/api/export?" + params.toString();
}

export { DEMO_ITEMS };
