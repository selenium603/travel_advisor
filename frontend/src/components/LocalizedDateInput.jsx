import { useState } from "react";
import { CalendarDays } from "lucide-react";

function parseDate(text) {
  const match = text.trim().match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$/);
  if (!match) return "";
  const iso = `${match[1]}-${match[2].padStart(2, "0")}-${match[3].padStart(2, "0")}`;
  const date = new Date(`${iso}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === iso ? iso : "";
}

export default function LocalizedDateInput({ id, label, value, min, onChange, invalid }) {
  const [draft, setDraft] = useState(value ? value.replaceAll("-", "/") : "");

  const handleTextChange = (event) => {
    const text = event.target.value;
    setDraft(text);
    onChange(parseDate(text));
  };

  const handlePickerChange = (event) => {
    const date = event.target.value;
    setDraft(date.replaceAll("-", "/"));
    onChange(date);
  };

  return (
    <div className="relative">
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={draft}
        onChange={handleTextChange}
        placeholder="年/月/日"
        aria-invalid={invalid || undefined}
        className={`w-full rounded-lg border px-3 py-2.5 pr-11 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          invalid ? "border-red-300" : "border-slate-300"
        }`}
      />
      <CalendarDays size={17} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
      <input
        type="date"
        value={value}
        min={min}
        onChange={handlePickerChange}
        onClick={(event) => event.currentTarget.showPicker?.()}
        aria-label={`打开${label}选择器`}
        className="absolute right-0 top-0 h-full w-10 opacity-0 cursor-pointer"
      />
    </div>
  );
}
