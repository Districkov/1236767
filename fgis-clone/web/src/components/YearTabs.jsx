import { YEARS, yearLabel } from "../helpers.js";

export default function YearTabs({ value, onChange }) {
  return (
    <div className="years">
      {YEARS.map((year) => (
        <button
          key={year}
          type="button"
          className={"year-tab" + (value === year ? " active" : "")}
          onClick={() => onChange(year)}
        >
          {yearLabel(year)}
        </button>
      ))}
    </div>
  );
}
