import { Link } from 'react-router-dom';
import { useAnalysisSession } from '../context/useAnalysisSession';
import { WithChildren } from '../types/react';
import GlobalSearch from './GlobalSearch';
import NavButton from './NavButton';

function AppShell({ children }: WithChildren) {
  const { selectedFile } = useAnalysisSession();

  return (
    <main className="relative min-h-screen overflow-hidden bg-app text-content">
      <div
        aria-hidden="true"
        className="bg-app-chrome pointer-events-none absolute inset-0 opacity-70"
      />
      <div className="relative mx-auto flex min-h-screen w-full max-w-(--width-app) flex-col px-page-x py-page-y sm:px-page-x-sm lg:px-page-x-lg">
        <header className="mb-section-gap flex flex-wrap items-center justify-between gap-inline-gap border-b border-border pb-header-padding-bottom">
          <div>
            <p className="ui-eyebrow">Genomic trait visualizer</p>
            <Link
              to="/"
              className="mt-section-offset-sm block text-lg font-semibold text-content"
            >
              WHOAMI
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-inline-gap-sm">
            <GlobalSearch />
            {selectedFile ? (
              <NavButton to="/analysis" variant="secondary">
                Analysis
              </NavButton>
            ) : null}
            <NavButton to="/traits" variant="secondary">
              Trait catalog
            </NavButton>
            <NavButton to="/rsids" variant="secondary">
              rsID catalog
            </NavButton>
            <span className="ui-badge hidden sm:inline-flex">
              free and open-source
            </span>
          </div>
        </header>
        {children}
      </div>
    </main>
  );
}

export default AppShell;
