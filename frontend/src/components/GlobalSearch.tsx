import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { searchCatalog } from '../services/traitApi';
import type { SearchResult } from '../types/analysis';

function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const trimmedQuery = query.trim();

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    inputRef.current?.focus();

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    window.addEventListener('keydown', closeOnEscape);

    return () => {
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [isOpen]);

  useEffect(() => {
    if (trimmedQuery.length < 2) {
      setResults([]);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = await searchCatalog(trimmedQuery);
        if (!controller.signal.aborted) {
          setResults([...data.traits, ...data.rsids]);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Search is unavailable right now.',
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }, 180);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [trimmedQuery]);

  const statusCopy = useMemo(() => {
    if (trimmedQuery.length < 2) {
      return 'Type at least two characters to search traits, rsIDs, and keywords.';
    }

    if (isLoading) {
      return 'Searching catalog.';
    }

    if (errorMessage) {
      return errorMessage;
    }

    if (results.length === 0) {
      return 'No matching traits or rsIDs found.';
    }

    return '';
  }, [errorMessage, isLoading, results.length, trimmedQuery.length]);

  function closeSearch() {
    setIsOpen(false);
    setQuery('');
    setResults([]);
    setErrorMessage('');
  }

  return (
    <>
      <button
        className="ui-icon-button ui-search-icon-button"
        type="button"
        aria-label="Open global search"
        onClick={() => setIsOpen(true)}
      />

      {isOpen ? (
        <div
          className="ui-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="global-search-title"
        >
          <button
            className="absolute inset-0 h-full w-full cursor-default"
            type="button"
            aria-label="Close global search"
            onClick={closeSearch}
          />
          <div className="ui-search-modal">
            <div className="flex items-start justify-between gap-inline-gap">
              <div>
                <p className="ui-eyebrow">global search</p>
                <h2
                  id="global-search-title"
                  className="mt-section-offset-sm text-2xl leading-tight text-content"
                >
                  Search the genomic explorer
                </h2>
              </div>
              <button
                className="ui-icon-button ui-close-icon-button"
                type="button"
                aria-label="Close global search"
                onClick={closeSearch}
              />
            </div>

            <label className="sr-only" htmlFor="global-search">
              Search traits, rsIDs, or keywords
            </label>
            <input
              ref={inputRef}
              id="global-search"
              className="ui-search-input mt-section-offset-xl"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search traits, rsIDs, keywords"
              type="search"
            />

            <div className="ui-search-results-panel">
              {statusCopy ? (
                <p className="ui-search-status">{statusCopy}</p>
              ) : (
                results.map((result) => (
                  <Link
                    key={`${result.kind}-${result.url}`}
                    to={result.url}
                    className="ui-search-result-link"
                    onClick={closeSearch}
                  >
                    <div className="min-w-0">
                      <p className="ui-eyebrow">
                        {result.kind === 'trait' ? 'trait' : 'rsID'} /{' '}
                        {result.subtitle}
                      </p>
                      <p className="mt-section-offset-sm truncate text-sm font-semibold text-content">
                        {result.title}
                      </p>
                      <p className="mt-section-offset-sm line-clamp-2 text-xs leading-body text-content-subtle">
                        {result.description}
                      </p>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export default GlobalSearch;
