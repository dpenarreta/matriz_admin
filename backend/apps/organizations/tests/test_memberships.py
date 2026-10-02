"""Membresías por empresa y configuración de la empresa."""

import pytest

from apps.obligations.tests.fixtures import client_for, make_user
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db


def test_admin_adds_member_by_username(company, people):
    newcomer = make_user("nuevo.miembro")
    response = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/members/",
        {"identifier": "nuevo.miembro", "role": "auditor"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert Membership.objects.get(user=newcomer, company=company).role == "auditor"


def test_non_admin_cannot_manage_members(company, people):
    response = client_for(people["supervisor"]).get(f"/api/v1/companies/{company.id}/members/")
    assert response.status_code == 403


def test_last_admin_cannot_be_removed_or_downgraded(company, people):
    membership = Membership.objects.get(user=people["admin"], company=company)
    client = client_for(people["admin"])
    url = f"/api/v1/companies/{company.id}/members/{membership.id}/"
    assert client.patch(url, {"role": "auditor"}, format="json").status_code == 400
    assert client.delete(url).status_code == 400


def test_company_settings_only_admin_and_timezone_validated(company, people):
    url = f"/api/v1/companies/{company.id}/"
    assert (
        client_for(people["supervisor"]).patch(url, {"activity": "x"}, format="json").status_code
        == 403
    )
    admin = client_for(people["admin"])
    assert admin.patch(url, {"timezone": "Marte/Base"}, format="json").status_code == 400
    response = admin.patch(url, {"short_name": "Laar Courier", "color": "#123456"}, format="json")
    assert response.status_code == 200
    assert response.data["short_name"] == "Laar Courier"


def test_people_endpoint_lists_company_members(company, people):
    data = client_for(people["responsible"]).get(f"/api/v1/companies/{company.id}/people/").data
    assert {person["username"] for person in data} >= {"ana.admin", "rita.responsable"}


def test_superuser_acts_as_admin_everywhere(company, other_company):
    root = make_user("root.admin", is_superuser=True, is_staff=True)
    data = client_for(root).get("/api/v1/companies/mine/").data
    assert {item["code"] for item in data} == {"LC", "VC"}
    assert all(item["role"] == "administrador" for item in data)
