"use client";

interface Props {
  years: number[];
  value: number;
  onChange: (next: number) => void;
}

export function YearSlider({ years, value, onChange }: Props) {
  if (!years.length) {
    return (
      <div>
        <label className="block text-xs font-medium text-slate-500">Year</label>
        <p className="text-sm text-slate-400">loading …</p>
      </div>
    );
  }
  const min = Math.min(...years);
  const max = Math.max(...years);
  const safe = Math.min(Math.max(value, min), max);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label htmlFor="year-slider" className="text-xs font-medium text-slate-500">
          Year
        </label>
        <span className="font-mono text-sm">{safe}</span>
      </div>
      <input
        id="year-slider"
        type="range"
        min={min}
        max={max}
        step={1}
        value={safe}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-blue-600"
        list="year-ticks"
      />
      <datalist id="year-ticks">
        {years.map((y) => <option key={y} value={y} label={String(y)} />)}
      </datalist>
      <div className="mt-1 flex justify-between text-[10px] text-slate-500">
        <span>{min}</span>
        <span>also:
          <input
            type="number"
            value={safe}
            min={min}
            max={max}
            onChange={(e) => onChange(Number(e.target.value))}
            className="ml-1 w-16 rounded border border-slate-300 bg-transparent
                       px-1 py-0.5 text-xs dark:border-slate-700"
          />
        </span>
        <span>{max}</span>
      </div>
    </div>
  );
}
