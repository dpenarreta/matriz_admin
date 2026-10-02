import { apiClient } from "./client";

const data = (res) => res.data;

/** Descarga un archivo protegido (con el token) y lo entrega como Blob. */
function getBlob(url, params) {
  return apiClient.get(url, { params, responseType: "blob" }).then((res) => {
    const disposition = res.headers["content-disposition"] || "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    return { blob: res.data, filename: match ? match[1] : "archivo" };
  });
}

export const matrizService = {
  // --- Empresas y personas ---
  myCompanies: () => apiClient.get("/companies/mine/").then(data),
  company: (companyId) => apiClient.get(`/companies/${companyId}/`).then(data),
  updateCompany: (companyId, payload) =>
    apiClient.patch(`/companies/${companyId}/`, payload).then(data),
  catalogs: (companyId) => apiClient.get(`/companies/${companyId}/catalogs/`).then(data),
  people: (companyId) => apiClient.get(`/companies/${companyId}/people/`).then(data),
  members: (companyId) => apiClient.get(`/companies/${companyId}/members/`).then(data),
  roles: (companyId) => apiClient.get(`/companies/${companyId}/roles/`).then(data),
  addMember: (companyId, payload) =>
    apiClient.post(`/companies/${companyId}/members/`, payload).then(data),
  updateMember: (companyId, memberId, payload) =>
    apiClient.patch(`/companies/${companyId}/members/${memberId}/`, payload).then(data),
  removeMember: (companyId, memberId) =>
    apiClient.delete(`/companies/${companyId}/members/${memberId}/`).then(data),

  // --- Vistas de la empresa ---
  dashboard: (companyId) => apiClient.get(`/companies/${companyId}/dashboard/`).then(data),
  periods: (companyId, params) =>
    apiClient.get(`/companies/${companyId}/periods/`, { params }).then(data),
  exportPeriods: (companyId, params, format) =>
    getBlob(`/companies/${companyId}/periods/`, { ...params, export: format }),
  calendar: (companyId, year, month) =>
    apiClient.get(`/companies/${companyId}/calendar/`, { params: { year, month } }).then(data),
  documentsOverview: (companyId, params) =>
    apiClient.get(`/companies/${companyId}/documents-overview/`, { params }).then(data),
  report: (companyId, params) =>
    apiClient.get(`/companies/${companyId}/reports/`, { params }).then(data),
  exportReport: (companyId, params, format) =>
    getBlob(`/companies/${companyId}/reports/`, { ...params, export: format }),
  audit: (companyId, params) =>
    apiClient.get(`/companies/${companyId}/audit/`, { params }).then(data),
  notifications: (companyId, params) =>
    apiClient.get(`/companies/${companyId}/notifications/`, { params }).then(data),
  reminderConfig: (companyId) =>
    apiClient.get(`/companies/${companyId}/reminder-config/`).then(data),
  updateReminderConfig: (companyId, payload) =>
    apiClient.put(`/companies/${companyId}/reminder-config/`, payload).then(data),

  // --- Obligaciones y períodos ---
  createObligation: (companyId, payload) =>
    apiClient.post(`/companies/${companyId}/obligations/`, payload).then(data),
  updateObligation: (obligationId, payload) =>
    apiClient.patch(`/obligations/${obligationId}/`, payload).then(data),
  period: (periodId) => apiClient.get(`/periods/${periodId}/`).then(data),
  updatePeriod: (periodId, payload) => apiClient.patch(`/periods/${periodId}/`, payload).then(data),
  changeDueDate: (periodId, payload) =>
    apiClient.post(`/periods/${periodId}/due-date/`, payload).then(data),
  submit: (periodId) => apiClient.post(`/periods/${periodId}/submit/`).then(data),
  validate: (periodId) => apiClient.post(`/periods/${periodId}/validate/`).then(data),
  returnToPreparation: (periodId, reason) =>
    apiClient.post(`/periods/${periodId}/return/`, { reason }).then(data),
  history: (periodId) => apiClient.get(`/periods/${periodId}/history/`).then(data),

  // --- Evidencias ---
  documents: (periodId) => apiClient.get(`/periods/${periodId}/documents/`).then(data),
  upload: (periodId, file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post(`/periods/${periodId}/documents/`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          if (onProgress && event.total) onProgress(Math.round((event.loaded * 100) / event.total));
        },
      })
      .then(data);
  },
  documentFile: (documentId, download = false) =>
    getBlob(`/documents/${documentId}/file/`, download ? { download: 1 } : undefined),
  rejectDocument: (documentId, reason) =>
    apiClient.post(`/documents/${documentId}/reject/`, { reason }).then(data),
  deleteDocument: (documentId) => apiClient.delete(`/documents/${documentId}/`).then(data),

  // --- Recordatorios ---
  reminders: (periodId) => apiClient.get(`/periods/${periodId}/reminders/`).then(data),
  sendReminder: (periodId) => apiClient.post(`/periods/${periodId}/reminders/send/`).then(data),
  previewReminder: (periodId, kind) =>
    apiClient.get(`/periods/${periodId}/reminders/preview/`, { params: { kind } }).then(data),
  retryNotification: (notificationId) =>
    apiClient.post(`/notifications/${notificationId}/retry/`).then(data),
};

/** Mensaje legible del contrato de error del backend. */
export function errorMessage(error, fallback = "No se pudo completar la acción.") {
  const payload = error?.response?.data?.error;
  if (!payload) return fallback;
  const details = payload.details;
  if (details && typeof details === "object") {
    const first = Object.values(details).flat()[0];
    if (typeof first === "string") return first;
  }
  return payload.message || fallback;
}

/** Dispara la descarga de un Blob en el navegador. */
export function saveBlob({ blob, filename }) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
