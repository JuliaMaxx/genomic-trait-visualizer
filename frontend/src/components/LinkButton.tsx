import { Link, type LinkProps } from 'react-router-dom';

type Props = LinkProps & {
  className?: string;
  variant?: keyof typeof variants;
};

const variants = {
  primary: 'ui-button-primary',
  secondary: 'ui-button-secondary',
};

function LinkButton({
  children,
  className = '',
  variant = 'primary',
  ...props
}: Props) {
  return (
    <Link
      {...props}
      className={`ui-button-base ${variants[variant]} ${className}`.trim()}
    >
      {children}
    </Link>
  );
}

export default LinkButton;
