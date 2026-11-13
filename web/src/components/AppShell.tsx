import { NavLink, Outlet } from "react-router-dom";
import { TokenBar } from "./TokenBar";

const LINKS = [
  { to: "/", label: "Studio" },
  { to: "/comparateur", label: "Comparateur" },
  { to: "/garde-fous", label: "Garde-fous" },
] as const;

export function AppShell() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Aller au contenu
      </a>
      <header className="app-header">
        <div className="brand">
          <p className="brand-name">MarketPlace Vision</p>
          <p className="brand-tag">Photo d’objet → catégorie d’annonce, en un appel API.</p>
        </div>
        <nav className="nav" aria-label="Navigation principale">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <TokenBar />
      <main id="main">
        <Outlet />
      </main>
    </div>
  );
}
