import { useCallback, useEffect, useState } from "react";

import { adminMatrizService } from "../../../api/adminMatrizService";
import { errorMessage } from "../../../api/matrizService";
import { Breadcrumbs } from "../../../components/common/Breadcrumbs/Breadcrumbs";
import { usePermission } from "../../../hooks/usePermission";

const KINDS = [
  ["areas", "Áreas"],
  ["control-entities", "Entidades de control"],
];

/**
 * Catálogos compartidos por todas las empresas. Exige `catalogos.ver`;
 * editar, `catalogos.editar`. Un registro usado por alguna obligación no se
 * puede eliminar (el backend lo impide).
 */
export function CatalogsPage() {
  const canEdit = usePermission("catalogos.editar");
  const [kind, setKind] = useState("areas");
  const [items, setItems] = useState([]);
  const [draft, setDraft] = useState({ code: "", name: "" });
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({ code: "", name: "" });
  const [error, setError] = useState(null);

  const load = useCallback(
    () =>
      adminMatrizService
        .catalog(kind)
        .then(setItems)
        .catch(() => setError("No se pudo cargar el catálogo.")),
    [kind]
  );

  useEffect(() => {
    setError(null);
    setEditingId(null);
    load();
  }, [load]);

  async function run(action) {
    setError(null);
    try {
      await action();
      await load();
      return true;
    } catch (err) {
      setError(errorMessage(err));
      return false;
    }
  }

  const label = KINDS.find(([key]) => key === kind)[1];

  return (
    <div className="catalogs-page">
      <Breadcrumbs items={[{ label: "Administración" }, { label: "Catálogos" }, { label }]} />
      <h2>Catálogos</h2>
      <ul className="nav nav-tabs mb-3">
        {KINDS.map(([key, text]) => (
          <li key={key} className="nav-item">
            <button type="button" className={`nav-link ${kind === key ? "active" : ""}`} onClick={() => setKind(key)}>
              {text}
            </button>
          </li>
        ))}
      </ul>
      {error && <div className="alert alert-danger">{error}</div>}

      {canEdit && (
        <form
          className="d-flex gap-2 mb-3 col-12 col-md-8"
          onSubmit={async (event) => {
            event.preventDefault();
            if (await run(() => adminMatrizService.createCatalogItem(kind, draft))) setDraft({ code: "", name: "" });
          }}
        >
          <input
            className="form-control form-control-sm"
            style={{ maxWidth: 120 }}
            placeholder="Código"
            aria-label="Código"
            value={draft.code}
            onChange={(event) => setDraft({ ...draft, code: event.target.value })}
            required
            maxLength={10}
          />
          <input
            className="form-control form-control-sm"
            placeholder="Nombre"
            aria-label="Nombre"
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            required
          />
          <button type="submit" className="btn btn-primary btn-sm text-nowrap">
            Agregar
          </button>
        </form>
      )}

      <div className="table-responsive">
        <table className="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th style={{ width: 140 }}>Código</th>
              <th>Nombre</th>
              {canEdit && <th style={{ width: 200 }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) =>
              editingId === item.id ? (
                <tr key={item.id}>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      aria-label="Código"
                      value={editDraft.code}
                      onChange={(event) => setEditDraft({ ...editDraft, code: event.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      aria-label="Nombre"
                      value={editDraft.name}
                      onChange={(event) => setEditDraft({ ...editDraft, name: event.target.value })}
                    />
                  </td>
                  <td className="d-flex gap-2">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={async () => {
                        if (await run(() => adminMatrizService.updateCatalogItem(kind, item.id, editDraft)))
                          setEditingId(null);
                      }}
                    >
                      Guardar
                    </button>
                    <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setEditingId(null)}>
                      Cancelar
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={item.id}>
                  <td>{item.code}</td>
                  <td>{item.name}</td>
                  {canEdit && (
                    <td className="d-flex gap-2">
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => {
                          setEditingId(item.id);
                          setEditDraft({ code: item.code, name: item.name });
                        }}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => {
                          if (window.confirm(`¿Eliminar "${item.name}"?`)) {
                            run(() => adminMatrizService.deleteCatalogItem(kind, item.id));
                          }
                        }}
                      >
                        Eliminar
                      </button>
                    </td>
                  )}
                </tr>
              )
            )}
            {items.length === 0 && (
              <tr>
                <td colSpan={3} className="text-center text-muted">
                  Sin registros
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
