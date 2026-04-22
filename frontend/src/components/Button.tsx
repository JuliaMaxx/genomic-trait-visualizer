import { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: keyof typeof variants;
};

const variants = {
  primary:
    'border border-(--color-brand-line) bg-brand text-zinc-950 shadow-(--shadow-button) hover:brightness-105 disabled:opacity-50',
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
      className={`inline-flex items-center justify-center rounded-(--radius-button) px-(--spacing-control-x) py-(--spacing-control-y) text-sm font-semibold tracking-tight transition duration-200 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
