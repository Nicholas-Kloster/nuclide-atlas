import type { ChangeEvent } from 'react';

interface Props {
  value: string;
  onChange: (v: string) => void;
  matchCount: number;
}

export function SearchFilter({ value, onChange, matchCount }: Props) {
  const onInput = (e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value);
  return (
    <div className="search-filter">
      <input
        type="search"
        value={value}
        onChange={onInput}
        placeholder="Search nodes…"
        aria-label="search nodes"
      />
      {value && (
        <span className="match-count">{matchCount} match{matchCount === 1 ? '' : 'es'}</span>
      )}
    </div>
  );
}
