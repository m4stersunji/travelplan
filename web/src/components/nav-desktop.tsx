import { Link } from "@tanstack/react-router";

const ITEMS = [
  { to: "/", label: "Home" },
  { to: "/add", label: "Add trip" },
  { to: "/settings", label: "Settings" },
] as const;

export function NavDesktop() {
  return (
    <header className="hidden md:block border-b">
      <div className="mx-auto max-w-2xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold">
          Travelplan
        </Link>
        <nav className="flex gap-4 text-sm">
          {ITEMS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="text-muted-foreground hover:text-foreground"
              activeProps={{ className: "text-foreground font-medium" }}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
