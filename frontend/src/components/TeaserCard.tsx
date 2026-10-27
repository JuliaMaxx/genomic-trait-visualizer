import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

type Props = {
  to: string;
  eyebrow: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  size?: 'sm' | 'lg';
  footer?: ReactNode;
  titleAs?: 'h2' | 'h3';
  titleClassName?: string;
  descriptionClassName?: string;
  className?: string;
};

const sizeClasses = {
  sm: 'ui-card-link-sm',
  lg: 'ui-card-link-lg',
} as const;

function TeaserCard({
  to,
  eyebrow,
  title,
  description,
  size = 'sm',
  footer,
  titleClassName = '',
  descriptionClassName = '',
  className = '',
}: Props) {
  return (
    <div className={className}>
      <Link to={to} className={`group ui-card-link ${sizeClasses[size]}`}>
        <div>
          <p className="ui-eyebrow">{eyebrow}</p>
          <h2 className={`ui-card-link-heading ${titleClassName}`.trim()}>
            {title}
          </h2>
          {description ? (
            <p
              className={`leading-regular ui-paragraph-subtle ${descriptionClassName}`.trim()}
            >
              {description}
            </p>
          ) : null}
        </div>
      </Link>
      {footer ? (
        <div className="mt-2xs flex flex-wrap gap-sm">{footer}</div>
      ) : null}
    </div>
  );
}

export default TeaserCard;
