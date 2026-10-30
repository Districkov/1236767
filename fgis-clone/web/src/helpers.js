
export function pick(obj, ...keys) {
  if (!obj) return "";
  for (const key of keys) {
    const value = obj[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return "";
}

export function formatDate(value) {
  if (!value) return "";
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(value);
  return `${m[3]}.${m[2]}.${m[1]}`;
}

export const COLUMNS = [
  { key: "org_title", label: "Организация-поверитель", width: "10%" },
  { key: "mit_number", label: "Регистрационный номер типа СИ", width: "10%" },
  { key: "mit_title", label: "Наименование типа СИ", width: "11%" },
  { key: "mit_notation", label: "Обозначение типа СИ", width: "10%" },
  { key: "mit_modification", label: "Модификация СИ", width: "12%" },
  {
    key: "mit_factory_num",
    label: "Заводской номер/ Буквенно-цифровое обозначение",
    width: "14%",
  },
  { key: "verification_date", label: "Дата поверки", width: "7%" },
  { key: "valid_date", label: "Действительна до", width: "7%" },
  { key: "sign_cipher", label: "Номер свидетельства/ Номер извещения", width: "13%" },
  { key: "applicability", label: "Пригодность", width: "6%" },
];

export const YEARS = ["all", 2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010, "before"];

export function yearLabel(year) {
  if (year === "all") return "Все";
  if (year === "before") return "до 2010";
  return String(year);
}

export const CARD_LABELS = {
  mit_number: "Регистрационный номер типа СИ",
  mit_notation: "Обозначение типа СИ",
  mit_title: "Наименование типа СИ",
  mit_factory_num: "Заводской номер СИ",
  mit_modification: "Модификация СИ",
  org_title: "Наименование организации-поверителя",
  sign_cipher: "Условный шифр знака поверки",
  owner_title: "Владелец СИ",
  vri_title: "Тип поверки",
  verification_date: "Дата поверки СИ",
  valid_date: "Поверка действительна до",
  doc_title: "Наименование документа, на основании которого выполнена поверка",
  applicability: "СИ пригодно",
  cert_num: "Номер свидетельства",
  sticker_num: "Номер наклейки",
  stamp: "Знак поверки в паспорте",
  stamp_si: "Знак поверки на СИ",
  means: "Средства поверки",
};

export const CARD_SECTIONS = [
  {
    title: "Сведения о результатах поверки СИ",
    keys: ["mit_number", "mit_notation", "mit_title", "mit_factory_num", "mit_modification"],
  },
  {
    title: "Сведения о поверке",
    keys: [
      "org_title",
      "sign_cipher",
      "owner_title",
      "vri_title",
      "verification_date",
      "valid_date",
      "doc_title",
      "applicability",
      "cert_num",
      "sticker_num",
      "stamp",
      "stamp_si",
    ],
  },
];

