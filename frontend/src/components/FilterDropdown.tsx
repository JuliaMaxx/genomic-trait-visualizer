import { useEffect, useMemo, useRef, useState } from 'react';
import arrowDownIcon from '../assets/icons/arrow-down.svg';
import arrowDownAccentIcon from '../assets/icons/arrow-down-accent.svg';
import arrowUpAccentIcon from '../assets/icons/arrow-up-accent.svg';

type DropdownOption<T extends string> = {
  label: string;
  value: T;
};

type Props<T extends string> = {
  ariaLabel?: string;
  className?: string;
  onChange: (value: T) => void;
  options: DropdownOption<T>[];
  value: T;
};

function FilterDropdown<T extends string>({
  ariaLabel,
  className = '',
  onChange,
  options,
  value,
}: Props<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? options[0],
    [options, value],
  );

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('keydown', handleEscape);

    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <div ref={rootRef} className={`ui-dropdown-root ${className}`}>
      <button
        type="button"
        className="ui-dropdown-trigger group"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
      >
        <span className="ui-dropdown-trigger-label">
          {selectedOption.label}
        </span>
        <span className="" aria-hidden="true">
          <img
            src={arrowDownIcon}
            alt=""
            className="ui-icon group-hover:hidden group-aria-expanded:hidden"
          />
          <img
            src={arrowDownAccentIcon}
            alt=""
            className="ui-icon hidden group-hover:block group-aria-expanded:hidden"
          />
          <img
            src={arrowUpAccentIcon}
            alt=""
            className="ui-icon hidden group-hover:hidden group-aria-expanded:block"
          />
        </span>
      </button>

      {isOpen ? (
        <div className="ui-dropdown-menu" role="listbox" aria-label={ariaLabel}>
          {options.map((option) => {
            const isSelected = option.value === value;

            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={
                  isSelected
                    ? 'ui-dropdown-option ui-dropdown-option-selected'
                    : 'ui-dropdown-option'
                }
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
              >
                <span>{option.label}</span>
                {isSelected ? (
                  <span className="ui-dropdown-option-check">Selected</span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default FilterDropdown;
