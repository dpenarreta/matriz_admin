"""Membresías por empresa, roles editables y configuración de la empresa."""

import pytest
from django.contrib.auth.models import Group, Permission

from apps.obligations.tests.fixtures import client_for, make_pdf, make_user
from apps.organizations.default_roles import RoleName, default_role
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db


def make_role(name, *codenames):
    role = Group.objects.create(name=name)
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    return role


def test_default_roles_are_seeded_with_their_permissions():
    responsible = default_role(RoleName.RESPONSIBLE)
    codenames = set(responsible.permissions.values_list("codename", flat=True))
    assert codenames == {
        "matriz.crear",
        "matriz.editar",
        "matriz.cargar",
        "matriz.enviar",
        "matriz.recordar",
    }
    assert (
        default_role(RoleName.ADMIN).permissions.filter(codename__startswith="matriz.").count()
        == 12
    )


def test_admin_adds_member_with_a_role(company, people):
    newcomer = make_user("nuevo.miembro")
    auditor = default_role(RoleName.AUDITOR)
    response = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/members/",
        {"identifier": "nuevo.miembro", "role_id": auditor.id},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert Membership.objects.get(user=newcomer, company=company).role == auditor


def test_role_without_matrix_permissions_cannot_be_assigned(company, people):
    make_user("nuevo.miembro")
    plain = make_role("Solo usuarios", "usuarios.ver")
    response = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/members/",
        {"identifier": "nuevo.miembro", "role_id": plain.id},
        format="json",
    )
    assert response.status_code == 400


def test_non_admin_cannot_manage_members(company, people):
    response = client_for(people["supervisor"]).get(f"/api/v1/companies/{company.id}/members/")
    assert response.status_code == 403


def test_last_member_manager_cannot_be_removed_or_downgraded(company, people):
    membership = Membership.objects.get(user=people["admin"], company=company)
    client = client_for(people["admin"])
    url = f"/api/v1/companies/{company.id}/members/{membership.id}/"
    auditor = default_role(RoleName.AUDITOR)
    assert client.patch(url, {"role_id": auditor.id}, format="json").status_code == 400
    assert client.delete(url).status_code == 400


def test_company_roles_endpoint_lists_matrix_roles(company, people):
    data = client_for(people["admin"]).get(f"/api/v1/companies/{company.id}/roles/").data
    names = {role["name"] for role in data}
    assert {"Administrador", "Responsable", "Supervisor/Aprobador", "Auditor"} <= names
    responsible = next(role for role in data if role["name"] == "Responsable")
    assert "matriz.cargar" in responsible["permission_codenames"]


def test_editing_a_role_changes_what_members_can_do(company, people, make_period):
    """El rol es configurable: quitarle `matriz.cargar` al Responsable bloquea
    la carga en el acto, sin tocar código."""
    period = make_period(days=5)
    client = client_for(people["responsible"])
    url = f"/api/v1/periods/{period.id}/documents/"
    assert client.post(url, {"file": make_pdf()}, format="multipart").status_code == 201

    responsible = default_role(RoleName.RESPONSIBLE)
    responsible.permissions.remove(Permission.objects.get(codename="matriz.cargar"))

    assert client.post(url, {"file": make_pdf()}, format="multipart").status_code == 403


def test_custom_role_without_view_all_only_sees_own_periods(company, people, make_period):
    reviewer = make_user("revisor.propio")
    role = make_role("Revisor de lo propio", "matriz.validar")
    Membership.objects.create(user=reviewer, company=company, role=role)
    own = make_period(days=5, label="Propio", responsible=reviewer, backup=None)
    make_period(days=6, label="Ajeno")

    response = client_for(reviewer).get(f"/api/v1/companies/{company.id}/periods/")

    assert [row["code"] for row in response.data["results"]] == [own.code]


def test_custom_role_with_view_all_sees_everything(company, people, make_period):
    viewer = make_user("lector.total")
    Membership.objects.create(
        user=viewer, company=company, role=make_role("Lector", "matriz.ver_todas")
    )
    make_period(days=5, label="Uno")
    make_period(days=6, label="Dos")
    client = client_for(viewer)
    assert client.get(f"/api/v1/companies/{company.id}/periods/").data["count"] == 2
    assert client.get(f"/api/v1/companies/{company.id}/periods/?export=xlsx").status_code == 403


def test_company_settings_only_with_configure_permission(company, people):
    url = f"/api/v1/companies/{company.id}/"
    supervisor = client_for(people["supervisor"])
    assert supervisor.patch(url, {"activity": "x"}, format="json").status_code == 403
    admin = client_for(people["admin"])
    assert admin.patch(url, {"timezone": "Marte/Base"}, format="json").status_code == 400
    response = admin.patch(url, {"short_name": "Laar Courier", "color": "#123456"}, format="json")
    assert response.status_code == 200
    assert response.data["short_name"] == "Laar Courier"


def test_my_companies_reports_role_and_capabilities(company, people):
    data = client_for(people["responsible"]).get("/api/v1/companies/mine/").data
    assert data[0]["role_label"] == "Responsable"
    assert data[0]["role"]["id"] == default_role(RoleName.RESPONSIBLE).id
    assert "cargar" in data[0]["capabilities"]
    assert "ver_todas" not in data[0]["capabilities"]


def test_people_endpoint_lists_company_members(company, people):
    data = client_for(people["responsible"]).get(f"/api/v1/companies/{company.id}/people/").data
    assert {person["username"] for person in data} >= {"ana.admin", "rita.responsable"}


def test_superuser_acts_as_admin_everywhere(company, other_company):
    root = make_user("root.admin", is_superuser=True, is_staff=True)
    data = client_for(root).get("/api/v1/companies/mine/").data
    assert {item["code"] for item in data} == {"LC", "VC"}
    assert all("gestionar_miembros" in item["capabilities"] for item in data)
