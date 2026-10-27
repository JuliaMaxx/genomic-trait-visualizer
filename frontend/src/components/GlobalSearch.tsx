import searchIcon from '../assets/icons/search.svg';
import searchAccentIcon from '../assets/icons/search-accent.svg';
import closeIcon from '../assets/icons/close.svg';
import closeAccentIcon from '../assets/icons/close-accent.svg';
import { useEffect, useCallback, useRef, useState } from 'react';
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

  const closeSearch = useCallback(() => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
    setErrorMessage('');
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    inputRef.current?.focus();

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeSearch();
      }
    }

    window.addEventListener('keydown', closeOnEscape);

    return () => {
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [isOpen, closeSearch]);

  useEffect(() => {
    if (trimmedQuery.length < 2) {
      setResults([]);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    setResults([]);

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const data = await searchCatalog(trimmedQuery, controller.signal);
        if (!controller.signal.aborted) {
          setResults([...data.traits, ...data.rsids]);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setErrorMessage('Search is unavailable right now.');
          if (error instanceof Error) {
            console.error('Error searching catalog:', error.message);
          }
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

  const statusCopy = (() => {
    if (trimmedQuery.length < 2) {
      return 'Type at least two characters to search traits, rsIDs, and keywords.';
    }

    if (isLoading) {
      return 'Searching catalog...';
    }

    if (errorMessage) {
      return errorMessage;
    }

    if (results.length === 0) {
      return 'No matching traits or rsIDs found.';
    }

    return '';
  })();

  return (
    <>
      <button
        className="group ui-icon-button"
        type="button"
        aria-label="Open global search"
        onClick={() => setIsOpen(true)}
      >
        <img src={searchIcon} alt="" className="ui-icon group-hover:hidden" />
        <img
          src={searchAccentIcon}
          alt=""
          className="hidden ui-icon group-hover:block"
        />
      </button>

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
            <div className="flex items-start justify-between gap-md">
              <div>
                <p className="ui-eyebrow">global search</p>
                <h2 id="global-search-title" className="ui-section-title">
                  Search the genomic explorer
                </h2>
              </div>
              <button
                className="group ui-icon-button"
                type="button"
                aria-label="Close global search"
                onClick={closeSearch}
              >
                <img
                  src={closeIcon}
                  alt=""
                  className="ui-icon group-hover:hidden"
                />
                <img
                  src={closeAccentIcon}
                  alt=""
                  className="hidden ui-icon group-hover:block"
                />
              </button>
            </div>

            <input
              ref={inputRef}
              className="ui-search-input mt-lg"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Search traits, rsIDs, or keywords"
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
                      <p className="mt-2xs truncate ui-item-title">
                        {result.title}
                      </p>
                      <p className="ui-item-body-faint mt-2xs line-clamp-2 text-xs">
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
