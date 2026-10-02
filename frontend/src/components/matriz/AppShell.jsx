import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { matrizService } from "../../api/matrizService";
import { useCompany } from "../../context/CompanyContext";
import { useAuth } from "../../hooks/useAuth";
import { initials } from "../../utils/matrizFormat";
import { Icon } from "../common/Icon/Icon";
import { ObligationFormModal } from "./ObligationFormModal";
import { PeriodDrawer } from "./PeriodDrawer";

const NAV = [
  { path: "/resumen", label: "Resumen", icon: "grid-1x2" },
  { path: "/matriz", label: "Matriz de obligaciones", icon: "building", badge: true },
  { path: "/calendario", label: "Calendario", icon: "calendar3" },
  { path: "/documentos", label: "Documentos", icon: "folder2-open" },
  { path: "/reportes", label: "Reportes", icon: "bar-chart" },
  { path: "/configuracion", label: "Configuración", icon: "gear" },
];

const TITLES = Object.fromEntries(NAV.map((item) => [item.path, item.label]));

const ShellContext = createContext(null);

/** Abre el detalle de un período o el alta de obligación desde cualquier vista. */
export function useShell() {
  const context = useContext(ShellContext);
  if (!context) throw new Error("useShell debe usarse dentro de <AppShell>.");
  return context;
}

export function AppShell() {
  const { user, logout } = useAuth();
  const { companies, company, setActiveId, dataVersion, isLoading } = useCompany();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [menuOpen, setMenuOpen] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [attention, setAttention] = useState(0);
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const switcherRef = useRef(null);
  const searchTimer = useRef(null);

  const openPeriodId = Number(searchParams.get("periodo")) || null;

  const openPeriod = useCallback(
    (periodId) => {
      const next = new URLSearchParams(searchParams);
      next.set("periodo", String(periodId));
      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  const closePeriod = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.delete("periodo");
    setSearchParams(next);
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (!company) return;
    matrizService
      .dashboard(company.id)
      .then((data) => setAttention(data.counts.attention))
      .catch(() => setAttention(0));
  }, [company, dataVersion]);

  useEffect(() => {
    function handleClick(event) {
      if (switcherRef.current && !switcherRef.current.contains(event.target)) setSwitcherOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  const shell = useMemo(
    () => ({ openPeriod, openNewObligation: () => setCreating(true) }),
    [openPeriod]
  );

  if (isLoading) {
    return <div className="mz-loading">Cargando…</div>;
  }

  if (!company) {
    return (
      <div className="mz-empty-company">
        <h2>Sin empresas asignadas</h2>
        <p>Su usuario no tiene un rol en ninguna empresa. Solicite acceso a un Administrador.</p>
        <button type="button" className="btn btn-outline-secondary" onClick={logout}>
          Cerrar sesión
        </button>
      </div>
    );
  }

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username;
  const hasAdminPanel = Boolean(user?.permissions?.length);

  function handleSearch(event) {
    const value = event.target.value;
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      navigate(`/matriz?q=${encodeURIComponent(value)}`);
    }, 250);
  }

  return (
    <ShellContext.Provider value={shell}>
      <div className="mz-shell" style={{ "--company-color": company.color }}>
        <nav className={`mz-sidebar ${menuOpen ? "mz-sidebar--open" : ""}`} aria-label="Menú principal">
          <div className="mz-brand">
            <span className="mz-glyph">MA</span>
            <span>
              Matriz Administrativa
              <br />
              de Obligaciones
            </span>
          </div>
          <div className="mz-active-company">
            <small>Tablero activo</small>
            <strong>{company.short_name}</strong>
          </div>
          <ul className="mz-nav">
            {NAV.map((item) => (
              <li key={item.path}>
                <NavLink to={item.path} className={({ isActive }) => `mz-nav-item ${isActive ? "is-active" : ""}`}>
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  {item.badge && attention > 0 && (
                    <span className="mz-badge" title="Incumplidas o que vencen hoy">
                      {attention}
                    </span>
                  )}
                </NavLink>
              </li>
            ))}
            {hasAdminPanel && (
              <li>
                <Link to="/admin" className="mz-nav-item">
                  <Icon name="shield-lock" />
                  <span>Administración del sistema</span>
                </Link>
              </li>
            )}
          </ul>
          <div className="mz-sidebar-foot">
            <span className="mz-role-pill">
              <Icon name="lock-fill" /> {company.role_label}
            </span>
            <div className="mz-user">
              <div className="mz-avatar">{initials(fullName)}</div>
              <div>
                <strong>{fullName}</strong>
                <span>{user?.email}</span>
              </div>
              <button type="button" className="mz-logout" onClick={logout} title="Cerrar sesión" aria-label="Cerrar sesión">
                <Icon name="box-arrow-right" />
              </button>
            </div>
          </div>
        </nav>
        {menuOpen && <div className="mz-sidebar-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />}

        <div className="mz-main">
          <header className="mz-topbar">
            <button type="button" className="mz-icon-btn mz-menu-btn" onClick={() => setMenuOpen(true)} aria-label="Abrir menú">
              <Icon name="list" />
            </button>
            <h1>{TITLES[location.pathname] || "Matriz"}</h1>
            <div className="mz-spacer" />
            <label className="mz-search">
              <Icon name="search" />
              <span className="visually-hidden">Buscar</span>
              <input
                type="search"
                value={search}
                onChange={handleSearch}
                placeholder="Buscar obligación, responsable, código…"
              />
            </label>
            <button
              type="button"
              className="mz-icon-btn"
              title="Recordatorios y notificaciones"
              aria-label="Recordatorios y notificaciones"
              onClick={() => navigate("/configuracion?tab=recordatorios")}
            >
              <Icon name="bell" />
              {attention > 0 && <span className="mz-dot" />}
            </button>
            <div className="mz-switcher" ref={switcherRef}>
              <button type="button" onClick={() => setSwitcherOpen((open) => !open)} aria-expanded={switcherOpen}>
                <span className="mz-color-dot" style={{ background: company.color }} />
                {company.short_name}
                <Icon name="chevron-down" />
              </button>
              {switcherOpen && (
                <div className="mz-dropdown" role="menu">
                  {companies.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      role="menuitem"
                      className="mz-dropdown-item"
                      onClick={() => {
                        setActiveId(item.id);
                        setSwitcherOpen(false);
                        closePeriod();
                      }}
                    >
                      <span className="mz-color-dot" style={{ background: item.color }} />
                      <span>
                        {item.short_name}
                        <small>{item.role_label}</small>
                      </span>
                      {item.id === company.id && <Icon name="check2" className="ms-auto" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </header>
          <main className="mz-view">
            <Outlet />
          </main>
        </div>
      </div>
      {openPeriodId && <PeriodDrawer periodId={openPeriodId} onClose={closePeriod} />}
      {creating && (
        <ObligationFormModal
          onClose={() => setCreating(false)}
          onCreated={(period) => {
            setCreating(false);
            navigate(`/matriz?periodo=${period.id}`);
          }}
        />
      )}
    </ShellContext.Provider>
  );
}
