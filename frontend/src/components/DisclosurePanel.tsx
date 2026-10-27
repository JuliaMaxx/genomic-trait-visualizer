import { ReactNode } from 'react';

type DisclosurePanelProps = {
  title: string;
  eyebrow: string;
  children: ReactNode;
};

function DisclosurePanel({ title, eyebrow, children }: DisclosurePanelProps) {
  return (
    <section className="ui-panel">
      <details className="ui-disclosure">
        <summary className="ui-disclosure-summary">
          <div>
            <p className="ui-eyebrow">{eyebrow}</p>
            <h2 className="ui-section-title">{title}</h2>
          </div>
          <span className="ui-disclosure-toggle">+</span>
        </summary>
        <div className="mt-lg">{children}</div>
      </details>
    </section>
  );
}

export default DisclosurePanel;
