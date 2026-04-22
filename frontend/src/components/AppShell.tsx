import { Link } from 'react-router-dom';
import { WithChildren } from '../types/react';

function AppShell({ children }: WithChildren) {
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
