import { WithChildren } from '../types/react';

function AppShell({ children }: WithChildren) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-app text-content">
      <div
        aria-hidden="true"
        className="bg-app-chrome pointer-events-none absolute inset-0 opacity-70"
      />
      <div className="relative mx-auto flex min-h-screen w-full max-w-(--width-app) flex-col px-page-x py-page-y sm:px-page-x-sm lg:px-page-x-lg">
        <header className="mb-section-gap flex items-center justify-between gap-inline-gap border-b border-border pb-header-padding-bottom">
          <div>
            <p className="ui-eyebrow">whoami / genomic explorer</p>
            <p className="mt-section-offset-sm text-lg font-semibold text-content">
              Genomic Trait Visualizer
            </p>
          </div>
          <p className="ui-badge hidden sm:inline-flex">
            dual-layer analysis interface
          </p>
        </header>
        {children}
      </div>
    </main>
  );
}

export default AppShell;
