import { useEffect, useState } from "react";

import { errorMessage, matrizService, saveBlob } from "../../api/matrizService";
import { Icon } from "../common/Icon/Icon";
import { Overlay } from "./Overlay";

/**
 * Visor de evidencias (5.9). Muestra el PDF real con el visor del navegador
 * (páginas, zoom e impresión nativos). El archivo se pide con el token de
 * sesión y se muestra desde un enlace local temporal; nunca hay una URL
 * pública del documento.
 */
export function PdfViewerModal({ documents, initialId, title, onClose }) {
  const [activeId, setActiveId] = useState(initialId || documents[0]?.id);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!activeId) return undefined;
    let url = null;
    setFile(null);
    setError(null);
    matrizService
      .documentFile(activeId)
      .then((result) => {
        url = URL.createObjectURL(new Blob([result.blob], { type: "application/pdf" }));
        setFile({ ...result, url });
      })
      .catch((err) => setError(errorMessage(err, "No se pudo abrir el documento.")));
    return () => url && URL.revokeObjectURL(url);
  }, [activeId]);

  const active = documents.find((doc) => doc.id === activeId);

  return (
    <Overlay title={`Visor de documentos — ${title}`} wide onClose={onClose}>
      {documents.length === 0 ? (
        <p className="mz-faint">Sin documentos: aún no hay evidencia válida para este período.</p>
      ) : (
        <div className="mz-viewer">
          <aside className="mz-viewer-side">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                className={`mz-vdoc ${doc.id === activeId ? "is-active" : ""}`}
                onClick={() => setActiveId(doc.id)}
              >
                <Icon name="file-earmark-pdf" /> {doc.original_name}
              </button>
            ))}
          </aside>
          <div className="mz-viewer-stage">
            <div className="mz-viewer-toolbar">
              <span className="mz-small mz-ellipsis">{active?.original_name}</span>
              <div className="mz-spacer" />
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                disabled={!file}
                onClick={() => window.open(file.url, "_blank", "noopener")}
              >
                <Icon name="printer" /> Abrir para imprimir
              </button>
              <button type="button" className="btn btn-outline-secondary btn-sm" disabled={!file} onClick={() => saveBlob(file)}>
                <Icon name="download" /> Descargar
              </button>
            </div>
            {error && <div className="mz-alert mz-alert--bad m-3">{error}</div>}
            {!error && !file && <p className="mz-faint p-3">Cargando documento…</p>}
            {file && <iframe title={active?.original_name} src={file.url} className="mz-viewer-frame" />}
          </div>
        </div>
      )}
    </Overlay>
  );
}
