import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/search", label: "Search" },
];

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-hcp-900 text-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <Link to="/" className="font-semibold text-lg tracking-tight">
            HCP
          </Link>
          <nav className="flex gap-4 text-sm" aria-label="Main">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  isActive ? "text-white underline" : "text-slate-300 hover:text-white"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-300 hidden sm:inline">
              {user?.name} · {user?.role}
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded px-2 py-1 bg-hcp-700 hover:bg-hcp-600 focus:outline-none focus:ring-2 focus:ring-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
