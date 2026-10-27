import { Link } from 'react-router-dom';
import { useAnalysisSession } from '../context/useAnalysisSession';
import { WithChildren } from '../types/react';
import GlobalSearch from './GlobalSearch';
import NavButton from './NavButton';

function AppShell({ children }: WithChildren) {
  const { selectedFile } = useAnalysisSession();

  return (
    <main className="relative min-h-screen text-content">
      <div aria-hidden="true" className="bg-app-grid" />
      <div className="relative mx-auto flex flex-col min-h-screen w-full max-w-app px-lg py-3xl sm:px-2xl lg:px-4xl">
        <header className="mb-xl flex flex-wrap items-center justify-between gap-md border-b border-border pb-lg">
          <div>
            <p className="ui-eyebrow">Genomic trait visualizer</p>
            <Link to="/" className="ui-logo-text">
              WHOAMI
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-sm">
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
