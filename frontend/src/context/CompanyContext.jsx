import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { matrizService } from "../api/matrizService";
import { useAuth } from "../hooks/useAuth";

const STORAGE_KEY = "matriz.activeCompanyId";

export const CompanyContext = createContext(null);

function readStoredId() {
  try {
    return Number(localStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null;
  }
}

/**
 * Empresas donde el usuario tiene rol y la empresa activa (tablero). Las
 * capacidades vienen del backend (`/companies/mine/`) y solo deciden qué
 * botones se muestran: cada endpoint vuelve a comprobarlas.
 */
export function CompanyProvider({ children }) {
  const { user } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [activeId, setActiveId] = useState(readStoredId);
  const [isLoading, setIsLoading] = useState(true);
  // Contador que sube tras cada acción que cambia datos (cerrar, cargar,
  // crear…): las vistas lo usan como dependencia para recargar.
  const [dataVersion, setDataVersion] = useState(0);
  const refreshData = useCallback(() => setDataVersion((value) => value + 1), []);

  const reload = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await matrizService.myCompanies();
      setCompanies(list);
      setActiveId((current) =>
        list.some((company) => company.id === current) ? current : list[0]?.id ?? null
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      reload();
    } else {
      setCompanies([]);
      setIsLoading(false);
    }
  }, [user, reload]);

  useEffect(() => {
    try {
      if (activeId) localStorage.setItem(STORAGE_KEY, String(activeId));
    } catch {
      // Sin almacenamiento local: la empresa activa vive solo en memoria.
    }
  }, [activeId]);

  const company = companies.find((item) => item.id === activeId) || null;

  const can = useCallback(
    (capability) => Boolean(company?.capabilities?.includes(capability)),
    [company]
  );

  const value = useMemo(
    () => ({ companies, company, setActiveId, can, isLoading, reload, dataVersion, refreshData }),
    [companies, company, can, isLoading, reload, dataVersion, refreshData]
  );

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}

export function useCompany() {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error("useCompany debe usarse dentro de un <CompanyProvider>.");
  }
  return context;
}
