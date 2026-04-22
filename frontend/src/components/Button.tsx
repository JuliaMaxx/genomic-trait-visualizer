import { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: keyof typeof variants;
};

const variants = {
  primary: 'ui-button-primary',
  secondary: 'ui-button-secondary',
};

function Button({
  children,
  className = '',
  type = 'button',
  variant = 'primary',
  ...props
}: Props) {
  return (
    <button
      type={type}
      className={`ui-button-base ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
