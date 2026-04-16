import { WithChildren } from '../types/react';

function AppShell({ children }: WithChildren) {
  return (
    <main className="min-h-screen bg-app text-content">
      <div className="mx-auto flex min-h-screen w-full max-w-(--width-app) flex-col px-(--spacing-page-x) py-(--spacing-page-y) sm:px-(--spacing-page-x-sm) lg:px-(--spacing-page-x-lg)">
        <header className="mb-(--spacing-section-gap)">
          <p className="text-sm">Genomic Trait Visualizer</p>
        </header>
        {children}
      </div>
    </main>
  );
}

export default AppShell;
