import { apiClient } from "./client";

const data = (res) => res.data;

/** Administración del sistema para los módulos de la matriz. */
export const adminMatrizService = {
  companies: () => apiClient.get("/admin/companies/").then(data),
  company: (id) => apiClient.get(`/admin/companies/${id}/`).then(data),
  createCompany: (payload) => apiClient.post("/admin/companies/", payload).then(data),
  updateCompany: (id, payload) => apiClient.patch(`/admin/companies/${id}/`, payload).then(data),
  addBranch: (companyId, payload) =>
    apiClient.post(`/admin/companies/${companyId}/branches/`, payload).then(data),
  updateBranch: (companyId, branchId, payload) =>
    apiClient.patch(`/admin/companies/${companyId}/branches/${branchId}/`, payload).then(data),

  catalog: (kind) => apiClient.get(`/admin/catalogs/${kind}/`).then(data),
  createCatalogItem: (kind, payload) => apiClient.post(`/admin/catalogs/${kind}/`, payload).then(data),
  updateCatalogItem: (kind, id, payload) =>
    apiClient.patch(`/admin/catalogs/${kind}/${id}/`, payload).then(data),
  deleteCatalogItem: (kind, id) => apiClient.delete(`/admin/catalogs/${kind}/${id}/`).then(data),

  matrixRoles: () => apiClient.get("/admin/matrix-roles/").then(data),
  userMemberships: (userId) => apiClient.get(`/admin/users/${userId}/memberships/`).then(data),
  replaceUserMemberships: (userId, memberships) =>
    apiClient.put(`/admin/users/${userId}/memberships/`, { memberships }).then(data),
};
