import FilterDropdown from './FilterDropdown';
import closeIcon from '../assets/icons/close.svg';
import closeAccentIcon from '../assets/icons/close-accent.svg';

type FilterOption = {
  value: string;
  label: string;
};

type SelectFilter = {
  id: string;
  label: string;
  ariaLabel: string;
  value: string;
  onChange: (value: string) => void;
  options: FilterOption[];
};

type Props = {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder: string;
  filters: SelectFilter[];
  hasActiveFilters: boolean;
  onReset: () => void;
};

function FilterPanel({
  searchValue,
  onSearchChange,
  searchPlaceholder,
  filters,
  hasActiveFilters,
  onReset,
}: Props) {
  return (
    <div className="ui-filter-panel">
      <div className="flex items-start justify-between gap-inline-gap-sm">
        <div className="ui-filter-grid min-w-0 flex-1">
          <label className="ui-filter-label">
            <span>Search</span>
            <input
              className="ui-search-input"
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={searchPlaceholder}
              type="search"
            />
          </label>

          {filters.map((filter) => (
            <div className="ui-filter-label" key={filter.id}>
              <span>{filter.label}</span>
              <FilterDropdown
                ariaLabel={filter.ariaLabel}
                value={filter.value}
                onChange={filter.onChange}
                options={filter.options}
              />
            </div>
          ))}
        </div>

        {hasActiveFilters ? (
          <button
            className="group ui-icon-button shrink-0"
            type="button"
            aria-label="Reset filters"
            onClick={onReset}
          >
            <img
              src={closeIcon}
              alt=""
              className="ui-icon-sm group-hover:hidden"
            />
            <img
              src={closeAccentIcon}
              alt=""
              className="hidden ui-icon-sm group-hover:block"
            />
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default FilterPanel;
