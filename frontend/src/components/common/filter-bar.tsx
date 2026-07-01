import { cn } from '@/lib/utils';

interface FilterOption {
  label: string;
  value: string;
}

interface FilterBarProps {
  options: FilterOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  className?: string;
}

export function FilterBar({ options, selected, onChange, className }: FilterBarProps) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => toggle(option.value)}
          className={cn(
            'rounded-full border px-3 py-1 text-sm transition-colors',
            selected.includes(option.value)
              ? 'border-purple-500 bg-purple-500/10 text-purple-400'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          )}
          style={{
            borderColor: selected.includes(option.value)
              ? 'rgba(124,58,237,0.5)'
              : 'rgba(255,255,255,0.06)',
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
