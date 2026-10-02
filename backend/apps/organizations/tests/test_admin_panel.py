"""Administración del sistema: empresas, sucursales, catálogos y roles por
empresa desde el formulario de usuario. Usa permisos del catálogo, igual que
usuarios y roles del template base."""

import pytest
from django.contrib.auth.models import Permission

from apps.core.models import AuditLog
from apps.obligations.tests.fixtures import client_for, make_user
from apps.organizations.default_roles import RoleName, default_role
from apps.organizations.models import Area, Membership

pytestmark = pytest.mark.django_db


def staff_with(*codenames):
    user = make_user(f"staff.{'-'.join(c.replace('.', '_') for c in codenames) or 'none'}")
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return client_for(user)


def test_companies_require_catalog_permission(company):
    assert staff_with().get("/api/v1/admin/companies/").status_code == 403
    assert staff_with("empresas.ver").get("/api/v1/admin/companies/").status_code == 200
    assert AuditLog.objects.filter(action="access_denied").exists()


def test_create_and_edit_company_with_branches(catalog):
    client = staff_with("empresas.ver", "empresas.editar")
    response = client.post(
        "/api/v1/admin/companies/",
        {
            "code": "nx",
            "legal_name": "Nueva Empresa S.A.",
            "short_name": "Nueva",
            "timezone": "America/Bogota",
            "branches": ["Matriz Bogotá"],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    company_id = response.data["id"]
    assert response.data["code"] == "NX"
    assert [b["name"] for b in response.data["branches"]] == ["Matriz Bogotá"]

    branch = client.post(
        f"/api/v1/admin/companies/{company_id}/branches/", {"name": "Sucursal Cali"}, format="json"
    )
    assert branch.status_code == 201
    duplicate = client.post(
        f"/api/v1/admin/companies/{company_id}/branches/", {"name": "sucursal cali"}, format="json"
    )
    assert duplicate.status_code == 400

    patched = client.patch(
        f"/api/v1/admin/companies/{company_id}/", {"is_active": False}, format="json"
    )
    assert patched.data["is_active"] is False


def test_view_only_cannot_create_company(catalog):
    response = staff_with("empresas.ver").post(
        "/api/v1/admin/companies/",
        {"code": "X", "legal_name": "X", "short_name": "X"},
        format="json",
    )
    assert response.status_code == 403


def test_catalog_crud_and_protected_delete(obligation):
    client = staff_with("catalogos.ver", "catalogos.editar")
    created = client.post(
        "/api/v1/admin/catalogs/areas/", {"code": "cal", "name": "Calidad"}, format="json"
    )
    assert created.status_code == 201
    assert created.data["code"] == "CAL"
    assert client.delete(f"/api/v1/admin/catalogs/areas/{created.data['id']}/").status_code == 204

    used = obligation.area
    response = client.delete(f"/api/v1/admin/catalogs/areas/{used.id}/")
    assert response.status_code == 400
    assert Area.objects.filter(pk=used.pk).exists()

    entities = client.get("/api/v1/admin/catalogs/control-entities/")
    assert entities.status_code == 200
    assert client.get("/api/v1/admin/catalogs/otra/").status_code == 404


def test_user_memberships_replace(company, other_company, people):
    client = staff_with("usuarios.ver", "usuarios.editar")
    user = make_user("multi.empresa")
    responsible = default_role(RoleName.RESPONSIBLE)
    auditor = default_role(RoleName.AUDITOR)
    url = f"/api/v1/admin/users/{user.id}/memberships/"

    response = client.put(
        url,
        {
            "memberships": [
                {"company_id": company.id, "role_id": responsible.id, "area_ids": []},
                {"company_id": other_company.id, "role_id": auditor.id},
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    assert {m["company"]["code"]: m["role"]["name"] for m in response.data} == {
        "LC": "Responsable",
        "VC": "Auditor",
    }

    response = client.put(
        url,
        {"memberships": [{"company_id": other_company.id, "role_id": responsible.id}]},
        format="json",
    )
    assert [m["company"]["code"] for m in response.data] == ["VC"]
    assert not Membership.objects.get(user=user, company=company).is_active
    assert client.get(url).data[0]["role"]["name"] == "Responsable"


def test_user_memberships_require_user_edit_permission(company):
    user = make_user("otro.usuario")
    url = f"/api/v1/admin/users/{user.id}/memberships/"
    assert (
        staff_with("usuarios.ver").put(url, {"memberships": []}, format="json").status_code == 403
    )


def test_matrix_roles_listing(company):
    data = staff_with("usuarios.ver").get("/api/v1/admin/matrix-roles/").data
    assert "Administrador" in {role["name"] for role in data}


def test_permission_catalog_exposes_new_modules():
    data = staff_with("permisos.ver").get("/api/v1/admin/permissions/").data
    assert {"matriz", "empresas", "catalogos"} <= set(data)
    assert "matriz.ver_todas" in data["matriz"]["permissions"]


def test_company_admin_role_can_be_created_from_roles_admin():
    """Un rol nuevo creado desde Administración → Roles ya sirve en la matriz."""
    client = staff_with("roles.ver", "roles.editar")
    response = client.post(
        "/api/v1/admin/roles/",
        {
            "name": "Contador externo",
            "permission_codenames": ["matriz.ver_todas", "matriz.exportar"],
        },
        format="json",
    )
    assert response.status_code == 201
    listed = staff_with("usuarios.ver").get("/api/v1/admin/matrix-roles/").data
    assert "Contador externo" in {role["name"] for role in listed}
