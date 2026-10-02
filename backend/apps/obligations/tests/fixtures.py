"""Fixtures compartidas de la matriz: una empresa con un usuario por rol, una
obligación y helpers para crear períodos y PDFs válidos."""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.obligations.models import Obligation
from apps.obligations.services import PeriodService
from apps.organizations.models import Area, Company, ControlEntity, Membership
from apps.users.models import User

R = Membership.Role
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def make_pdf(name="evidencia.pdf", content=PDF_BYTES):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def make_user(username, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Sup3r-Secr3t-Pass!",
        first_name=username.split(".")[0].title(),
        last_name="Prueba",
        **extra,
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def _isolated_media(settings, tmp_path):
    """Los PDF de las pruebas se escriben en un directorio temporal."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def catalog(db):
    area = Area.objects.create(code="CONT", name="Contabilidad y Tributario")
    other_area = Area.objects.create(code="TH", name="Talento Humano y Nómina")
    entity = ControlEntity.objects.create(code="SRI", name="Servicio de Rentas Internas (SRI)")
    return {"area": area, "other_area": other_area, "entity": entity}


@pytest.fixture
def company(catalog):
    return Company.objects.create(
        code="LC", legal_name="Laarcourier Express S.A.", short_name="Laarcourier"
    )


@pytest.fixture
def other_company(catalog):
    return Company.objects.create(
        code="VC", legal_name="Virtual Create S.A.", short_name="Virtual Create"
    )


@pytest.fixture
def people(company):
    users = {
        "admin": make_user("ana.admin"),
        "responsible": make_user("rita.responsable"),
        "backup": make_user("sara.suplente"),
        "other_responsible": make_user("otro.responsable"),
        "supervisor": make_user("sofia.supervisora"),
        "auditor": make_user("aldo.auditor"),
    }
    roles = {
        "admin": R.ADMIN,
        "responsible": R.RESPONSIBLE,
        "backup": R.RESPONSIBLE,
        "other_responsible": R.RESPONSIBLE,
        "supervisor": R.SUPERVISOR,
        "auditor": R.AUDITOR,
    }
    for key, user in users.items():
        Membership.objects.create(user=user, company=company, role=roles[key])
    company.general_manager = users["admin"]
    company.save()
    return users


@pytest.fixture
def obligation(company, catalog, people):
    return Obligation.objects.create(
        company=company,
        name="Declaración de IVA",
        area=catalog["area"],
        control_entity=catalog["entity"],
        type=Obligation.Type.REGULATORY,
        periodicity=Obligation.Periodicity.MONTHLY,
        expected_evidence="Formulario 104 y comprobante de pago",
        due_day=28,
    )


@pytest.fixture
def make_period(obligation, people):
    def _make(days=10, responsible=None, label=None, **extra):
        due = timezone.localdate() + timedelta(days=days)
        return PeriodService.create_period(
            obligation=obligation,
            due=due,
            responsible=responsible or people["responsible"],
            backup=extra.pop("backup", people["backup"]),
            supervisor=extra.pop("supervisor", people["supervisor"]),
            label=label or f"Período {due.isoformat()}",
            **extra,
        )

    return _make
