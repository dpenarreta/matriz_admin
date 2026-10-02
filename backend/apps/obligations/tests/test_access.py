"""Control de acceso por empresa y por rol (sección 4 y criterios 9.2)."""

import pytest

from apps.core.models import AuditLog
from apps.obligations.tests.fixtures import client_for, make_pdf

pytestmark = pytest.mark.django_db


def test_responsible_only_sees_own_periods(company, people, make_period):
    own = make_period(days=5, label="Propio")
    make_period(days=6, label="Ajeno", responsible=people["other_responsible"], backup=None)

    response = client_for(people["responsible"]).get(f"/api/v1/companies/{company.id}/periods/")

    assert response.status_code == 200
    assert [row["code"] for row in response.data["results"]] == [own.code]


def test_backup_also_sees_the_period(company, people, make_period):
    period = make_period(days=5)
    response = client_for(people["backup"]).get(f"/api/v1/periods/{period.id}/")
    assert response.status_code == 200


def test_responsible_gets_404_on_someone_elses_period_via_api(people, make_period):
    foreign = make_period(days=5, responsible=people["other_responsible"], backup=None)
    response = client_for(people["responsible"]).get(f"/api/v1/periods/{foreign.id}/")
    assert response.status_code == 404


def test_supervisor_and_auditor_see_everything(company, people, make_period):
    make_period(days=5, label="Uno")
    make_period(days=6, label="Dos", responsible=people["other_responsible"], backup=None)
    for key in ("supervisor", "auditor", "admin"):
        response = client_for(people[key]).get(f"/api/v1/companies/{company.id}/periods/")
        assert response.data["count"] == 2, key


def test_user_without_role_cannot_enter_another_company(other_company, people):
    response = client_for(people["admin"]).get(f"/api/v1/companies/{other_company.id}/periods/")
    assert response.status_code == 404


def test_my_companies_lists_only_companies_with_role(company, other_company, people):
    response = client_for(people["responsible"]).get("/api/v1/companies/mine/")
    assert [item["code"] for item in response.data] == ["LC"]
    assert response.data[0]["role"] == "responsable"
    assert "validar" not in response.data[0]["capabilities"]


def test_auditor_is_read_only(people, make_period):
    period = make_period(days=5)
    client = client_for(people["auditor"])

    assert client.get(f"/api/v1/periods/{period.id}/").status_code == 200
    assert (
        client.post(f"/api/v1/periods/{period.id}/documents/", {"file": make_pdf()}).status_code
        == 403
    )
    assert client.post(f"/api/v1/periods/{period.id}/submit/").status_code == 403
    assert client.post(f"/api/v1/periods/{period.id}/reminders/send/").status_code == 403
    assert AuditLog.objects.filter(action="access_denied", module="matriz").exists()


def test_supervisor_cannot_create_obligations(company, people, catalog):
    response = client_for(people["supervisor"]).post(
        f"/api/v1/companies/{company.id}/obligations/", {}, format="json"
    )
    assert response.status_code == 403


def test_responsible_cannot_validate(people, make_period):
    period = make_period(days=5)
    response = client_for(people["responsible"]).post(f"/api/v1/periods/{period.id}/validate/")
    assert response.status_code == 403


def test_responsible_cannot_export(company, people):
    response = client_for(people["responsible"]).get(
        f"/api/v1/companies/{company.id}/periods/?export=xlsx"
    )
    assert response.status_code == 403


def test_period_actions_reflect_role(people, make_period):
    period = make_period(days=5)
    actions = client_for(people["responsible"]).get(f"/api/v1/periods/{period.id}/").data["actions"]
    assert actions["upload"] and actions["submit"]
    assert not actions["validate"] and not actions["change_due_date"]
