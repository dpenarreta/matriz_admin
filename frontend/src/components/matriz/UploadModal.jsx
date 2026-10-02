import { useState } from "react";

import { errorMessage, matrizService } from "../../api/matrizService";
import { useToast } from "../../context/ToastContext";
import { Icon } from "../common/Icon/Icon";
import { Overlay } from "./Overlay";

const MAX_MB = 10;

/**
 * Carga de evidencias (5.8). La validación del navegador (extensión y
 * tamaño) es solo para avisar antes; el servidor vuelve a validar el
 * contenido del PDF y el tamaño.
 */
export function UploadModal({ period, onClose, onUploaded }) {
  const notify = useToast();
  const [items, setItems] = useState([]);
  const [dragging, setDragging] = useState(false);

  function update(id, patch) {
    setItems((list) => list.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function uploadOne(item) {
    try {
      await matrizService.upload(period.id, item.file, (progress) => update(item.id, { progress }));
      update(item.id, { progress: 100, state: "ok" });
    } catch (err) {
      update(item.id, { state: "error", message: errorMessage(err, "La carga falló. Vuelva a intentarlo.") });
    }
  }

  function handleFiles(fileList) {
    const added = Array.from(fileList).map((file) => {
      const id = `${file.name}-${file.size}-${Math.random()}`;
      if (!/\.pdf$/i.test(file.name)) {
        return { id, file, state: "error", message: "Formato no permitido. Solo se aceptan archivos PDF." };
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        return { id, file, state: "error", message: `Supera el tamaño máximo permitido (${MAX_MB} MB).` };
      }
      return { id, file, state: "uploading", progress: 0 };
    });
    setItems((list) => [...list, ...added]);
    added.filter((item) => item.state === "uploading").forEach(uploadOne);
  }

  const uploaded = items.filter((item) => item.state === "ok").length;
  const pending = items.some((item) => item.state === "uploading");

  function finish() {
    if (uploaded) notify("Documentos guardados", `${uploaded} archivo(s) añadidos al expediente.`);
    onUploaded();
  }

  return (
    <Overlay
      title="Cargar evidencia"
      onClose={uploaded ? finish : onClose}
      footer={
        <button type="button" className="btn btn-primary" disabled={pending} onClick={uploaded ? finish : onClose}>
          {uploaded ? "Listo" : "Cerrar"}
        </button>
      }
    >
      <p className="mz-faint mz-small">
        {period.obligation.name} · {period.label}. Documento esperado: <b>{period.obligation.expected_evidence}</b>.
        Solo se aceptan archivos PDF de hasta {MAX_MB} MB. Puede cargar varios documentos.
      </p>
      <div
        className={`mz-drop ${dragging ? "is-drag" : ""}`}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <Icon name="cloud-arrow-up" />
        <div>
          <b>Arrastre sus archivos PDF aquí</b>
          <br />o
        </div>
        <label className="btn btn-outline-secondary btn-sm mt-2">
          Elegir archivo
          <input type="file" accept="application/pdf,.pdf" multiple hidden onChange={(e) => handleFiles(e.target.files)} />
        </label>
      </div>
      {items.map((item) => (
        <div key={item.id} className={`mz-upload-item ${item.state === "error" ? "is-error" : ""}`}>
          <Icon name={item.state === "error" ? "exclamation-triangle" : "file-earmark-pdf"} />
          <div className="flex-grow-1 min-w-0">
            <div className="mz-ellipsis mz-small">{item.file.name}</div>
            {item.state === "error" ? (
              <div className="mz-small mz-bad">{item.message}</div>
            ) : (
              <div className="mz-bar">
                <i style={{ width: `${item.progress}%` }} />
              </div>
            )}
          </div>
          <span className="mz-mono mz-small">{item.state === "ok" ? "✓" : item.state === "error" ? "" : `${item.progress}%`}</span>
        </div>
      ))}
    </Overlay>
  );
}
