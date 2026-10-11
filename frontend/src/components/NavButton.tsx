import { NavLink, type NavLinkProps } from 'react-router-dom';

type Props = NavLinkProps & {
  className?: string;
  variant?: keyof typeof variants;
};

const variants = {
  primary: 'ui-button-primary',
  secondary: 'ui-button-secondary',
};

function NavButton({
  children,
  className = '',
  variant = 'primary',
  ...props
}: Props) {
  return (
    <NavLink
      {...props}
      className={({ isActive }) =>
        `ui-button-base ${variants[variant]}${isActive ? ' ui-button-active' : ''} ${className}`.trim()
      }
    >
      {children}
    </NavLink>
  );
}

export default NavButton;
