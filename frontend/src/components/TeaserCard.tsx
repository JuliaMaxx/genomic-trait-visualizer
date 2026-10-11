import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

type Props = {
  to: string;
  eyebrow: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  titleAs?: 'h2' | 'h3';
  titleClassName?: string;
  descriptionClassName?: string;
  className?: string;
};

function TeaserCard({
  to,
  eyebrow,
  title,
  description,
  footer,
  titleAs: TitleTag = 'h2',
  titleClassName = '',
  descriptionClassName = '',
  className = '',
}: Props) {
  return (
    <div className={className}>
      <Link to={to} className="group ui-card-link">
        <div>
          <p className="ui-eyebrow">{eyebrow}</p>
          <TitleTag
            className={`ui-card-link-heading mt-section-offset-sm text-xl text-content ${titleClassName}`.trim()}
          >
            {title}
          </TitleTag>
          {description ? (
            <p
              className={`mt-section-offset-sm text-sm leading-body text-content-subtle ${descriptionClassName}`.trim()}
            >
              {description}
            </p>
          ) : null}
        </div>
      </Link>
      {footer ? (
        <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
          {footer}
        </div>
      ) : null}
    </div>
  );
}

export default TeaserCard;
