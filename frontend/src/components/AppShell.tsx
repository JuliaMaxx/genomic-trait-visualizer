import { WithChildren } from '../types/react';

function AppShell({ children }: WithChildren) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-app text-content">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            'var(--background-radial), var(--background-grid)',
          backgroundSize: 'auto, 32px 32px',
        }}
      />
      <div className="relative mx-auto flex min-h-screen w-full max-w-(--width-app) flex-col px-(--spacing-page-x) py-(--spacing-page-y) sm:px-(--spacing-page-x-sm) lg:px-(--spacing-page-x-lg)">
        <header className="mb-(--spacing-section-gap) flex items-center justify-between gap-4 border-b border-(--color-border) pb-5">
          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint">
              whoami / genomic explorer
            </p>
            <p className="mt-2 text-lg font-semibold text-content">
              Genomic Trait Visualizer
            </p>
          </div>
          <p className="hidden rounded-full border border-(--color-border) bg-white/3 px-3 py-1.5 font-mono text-[0.7rem] uppercase tracking-(--tracking-eyebrow) text-content-faint sm:block">
            dual-layer analysis interface
          </p>
        </header>
        {children}
      </div>
    </main>
  );
}

export default AppShell;
