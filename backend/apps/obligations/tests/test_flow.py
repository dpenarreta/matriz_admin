"""Flujo de cierre, evidencias y cambio de fecha (secciones 6.2, 6.3 y 5.8)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.obligations.models import Document, Period, PeriodEvent
from apps.obligations.tests.fixtures import client_for, make_pdf
from apps.organizations.models import Company

pytestmark = pytest.mark.django_db


def upload(client, period, file=None):
    return client.post(
        f"/api/v1/periods/{period.id}/documents/", {"file": file or make_pdf()}, format="multipart"
    )


def test_upload_valid_pdf_moves_to_preparation(people, make_period):
    period = make_period(days=5)
    response = upload(client_for(people["responsible"]), period)

    assert response.status_code == 201, response.data
    period.refresh_from_db()
    assert period.stage == Period.Stage.IN_PREPARATION
    assert period.documents.get().sha256
    assert PeriodEvent.objects.filter(period=period, action="document.uploaded").exists()


def test_non_pdf_extension_is_rejected(people, make_period):
    period = make_period(days=5)
    response = upload(client_for(people["responsible"]), period, make_pdf("permiso.docx"))
    assert response.status_code == 400
    assert "PDF" in str(response.data)


def test_fake_pdf_with_pdf_extension_is_rejected_by_content(people, make_period):
    period = make_period(days=5)
    response = upload(
        client_for(people["responsible"]), period, make_pdf("falso.pdf", b"MZ\x90 no es pdf")
    )
    assert response.status_code == 400
    assert not period.documents.exists()


def test_oversized_file_is_rejected(settings, people, make_period):
    settings.DOCUMENT_MAX_UPLOAD_MB = 0
    period = make_period(days=5)
    response = upload(client_for(people["responsible"]), period)
    assert response.status_code == 400


def test_responsible_cannot_upload_to_foreign_period(people, make_period):
    foreign = make_period(days=5, responsible=people["other_responsible"], backup=None)
    assert upload(client_for(people["responsible"]), foreign).status_code == 404


def test_same_name_creates_a_new_version(people, make_period):
    period = make_period(days=5)
    client = client_for(people["responsible"])
    upload(client, period)
    upload(client, period)
    assert sorted(period.documents.values_list("version", flat=True)) == [1, 2]


def test_submit_requires_valid_evidence(people, make_period):
    period = make_period(days=5)
    response = client_for(people["responsible"]).post(f"/api/v1/periods/{period.id}/submit/")
    assert response.status_code == 400
    assert "evidencia" in str(response.data).lower()


def test_submit_twice_is_rejected(people, make_period):
    period = make_period(days=5)
    client = client_for(people["responsible"])
    upload(client, period)
    assert client.post(f"/api/v1/periods/{period.id}/submit/").status_code == 200
    assert client.post(f"/api/v1/periods/{period.id}/submit/").status_code == 400


def test_full_flow_supervisor_validates_on_time(people, make_period):
    period = make_period(days=5)
    responsible = client_for(people["responsible"])
    upload(responsible, period)
    responsible.post(f"/api/v1/periods/{period.id}/submit/")

    response = client_for(people["supervisor"]).post(f"/api/v1/periods/{period.id}/validate/")

    assert response.status_code == 200, response.data
    assert response.data["status"]["label"] == "Finalizado"
    period.refresh_from_db()
    assert period.is_closed and period.reminders_suspended and period.progress == 100
    assert period.validated_by == people["supervisor"]


def test_validate_button_is_available_on_the_due_day(people, make_period):
    """Defecto 5 del mockup, ya corregido."""
    period = make_period(days=0)
    responsible = client_for(people["responsible"])
    upload(responsible, period)
    responsible.post(f"/api/v1/periods/{period.id}/submit/")
    actions = client_for(people["supervisor"]).get(f"/api/v1/periods/{period.id}/").data["actions"]
    assert actions["validate"] and not actions["submit"]


def test_separation_of_duties_uploader_cannot_validate(people, make_period):
    period = make_period(days=5)
    admin = client_for(people["admin"])
    upload(admin, period)
    client_for(people["responsible"]).post(f"/api/v1/periods/{period.id}/submit/")

    response = admin.post(f"/api/v1/periods/{period.id}/validate/")

    assert response.status_code == 403
    assert "separación de funciones" in response.data["error"]["message"].lower()


def test_validation_after_due_date_is_late(people, make_period):
    period = make_period(days=5)
    responsible = client_for(people["responsible"])
    upload(responsible, period)
    responsible.post(f"/api/v1/periods/{period.id}/submit/")
    Period.objects.filter(pk=period.pk).update(due_at=timezone.now() - timedelta(days=2))

    response = client_for(people["supervisor"]).post(f"/api/v1/periods/{period.id}/validate/")

    assert response.data["status"]["label"] == "Finalizada fuera de plazo"
    assert response.data["status"]["days_overdue"] >= 2


def test_compliance_basis_submission_uses_submission_date(company, people, make_period):
    company.compliance_date_basis = Company.ComplianceDateBasis.SUBMISSION
    company.save()
    period = make_period(days=5)
    responsible = client_for(people["responsible"])
    upload(responsible, period)
    responsible.post(f"/api/v1/periods/{period.id}/submit/")
    period.refresh_from_db()
    submitted_at = period.submitted_at
    client_for(people["supervisor"]).post(f"/api/v1/periods/{period.id}/validate/")
    period.refresh_from_db()
    assert period.completed_at == submitted_at


def test_supervisor_can_return_with_reason(people, make_period):
    period = make_period(days=5)
    responsible = client_for(people["responsible"])
    upload(responsible, period)
    responsible.post(f"/api/v1/periods/{period.id}/submit/")
    supervisor = client_for(people["supervisor"])

    assert (
        supervisor.post(f"/api/v1/periods/{period.id}/return/", {"reason": "corto"}).status_code
        == 400
    )
    response = supervisor.post(
        f"/api/v1/periods/{period.id}/return/", {"reason": "Falta el comprobante de pago firmado."}
    )
    assert response.status_code == 200
    assert response.data["stage"] == Period.Stage.IN_PREPARATION


def test_reject_and_delete_document(people, make_period):
    period = make_period(days=5)
    document_id = upload(client_for(people["responsible"]), period).data["id"]
    responsible = client_for(people["responsible"])

    assert responsible.delete(f"/api/v1/documents/{document_id}/").status_code == 400
    response = client_for(people["supervisor"]).post(
        f"/api/v1/documents/{document_id}/reject/", {"reason": "Formulario sin firma del contador."}
    )
    assert response.data["status"] == Document.Status.REJECTED
    assert responsible.delete(f"/api/v1/documents/{document_id}/").status_code == 204
    assert Document.objects.get(pk=document_id).status == Document.Status.DELETED


def test_due_date_change_requires_reason_and_keeps_history(people, make_period):
    period = make_period(days=5)
    supervisor = client_for(people["supervisor"])
    new_due = (timezone.localdate() + timedelta(days=12)).isoformat()

    no_reason = supervisor.post(
        f"/api/v1/periods/{period.id}/due-date/", {"due_date": new_due, "reason": ""}
    )
    assert no_reason.status_code == 400

    response = supervisor.post(
        f"/api/v1/periods/{period.id}/due-date/",
        {"due_date": new_due, "reason": "Prórroga concedida por la entidad."},
    )
    assert response.status_code == 200
    event = PeriodEvent.objects.get(period=period, action="period.due_date_changed")
    assert event.previous_value and event.new_value and event.reason


def test_responsible_cannot_change_due_date(people, make_period):
    period = make_period(days=5)
    response = client_for(people["responsible"]).post(
        f"/api/v1/periods/{period.id}/due-date/",
        {"due_date": timezone.localdate().isoformat(), "reason": "Quiero más tiempo para cumplir."},
    )
    assert response.status_code == 403


def test_create_obligation_creates_first_period(company, people, catalog):
    payload = {
        "name": "Patente Municipal",
        "area_id": catalog["area"].id,
        "control_entity_id": catalog["entity"].id,
        "type": "regulatoria",
        "periodicity": "anual",
        "expected_evidence": "Comprobante de pago de patente",
        "due_date": (timezone.localdate() + timedelta(days=40)).isoformat(),
        "responsible_id": people["responsible"].id,
    }
    response = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/obligations/", payload, format="json"
    )
    assert response.status_code == 201, response.data
    assert response.data["code"].startswith("OBL-")
    assert response.data["approver"]["id"] == people["admin"].id

    duplicate = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/obligations/", payload, format="json"
    )
    assert duplicate.status_code == 400


def test_cannot_assign_responsible_from_another_company(company, other_company, people, catalog):
    from apps.obligations.tests.fixtures import make_user

    outsider = make_user("fuera.empresa")
    response = client_for(people["admin"]).post(
        f"/api/v1/companies/{company.id}/obligations/",
        {
            "name": "X",
            "area_id": catalog["area"].id,
            "control_entity_id": catalog["entity"].id,
            "type": "interna",
            "periodicity": "unica",
            "expected_evidence": "Acta",
            "due_date": timezone.localdate().isoformat(),
            "responsible_id": outsider.id,
        },
        format="json",
    )
    assert response.status_code == 400


def test_codes_are_unique_and_sequential(make_period):
    first, second = make_period(days=1, label="A"), make_period(days=2, label="B")
    assert int(second.code.split("-")[1]) == int(first.code.split("-")[1]) + 1
