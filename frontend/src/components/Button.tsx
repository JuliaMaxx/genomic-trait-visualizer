import { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: keyof typeof variants;
};

const variants = {
  primary: 'bg-brand text-white disabled:opacity-50',
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
      className={`inline-flex items-center justify-center rounded-(--radius-base) px-(--spacing-control-x) py-(--spacing-control-y) text-sm transition disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
