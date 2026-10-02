"""Datos de demostración: usuarios ficticios por empresa, las 14 obligaciones
del mockup y períodos en todos los estados (incumplido, vence hoy, sin
iniciar, en preparación, pendiente de validación, finalizado a tiempo y
fuera de plazo).

La contraseña de los usuarios demo se lee de la variable de entorno
`DEMO_USERS_PASSWORD`; nunca está escrita en el código. Por seguridad el
comando se niega a correr con DEBUG=False salvo `--allow-production`.

    DEMO_USERS_PASSWORD='...' python manage.py seed_demo

Las reglas de vencimiento de las plantillas son ilustrativas: deben
confirmarse con cada área (documento funcional, fase F1).
"""

import hashlib
import os
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reportlab.pdfgen import canvas

from apps.obligations.models import Document, Obligation, Period, Priority
from apps.obligations.scheduling import period_label
from apps.obligations.services import PeriodService, record_event
from apps.organizations.models import Area, Company, ControlEntity, Membership
from apps.reminders.services import get_config
from apps.users.models import User

R = Membership.Role

# (usuario, nombre, apellido, rol, áreas que atiende como responsable)
PEOPLE = {
    "LC": [
        ("rodrigo.salcedo", "Rodrigo", "Salcedo Peña", R.ADMIN, []),
        ("priscila.maldonado", "Priscila", "Maldonado", R.RESPONSIBLE, ["TH", "SST", "RSE"]),
        ("gabriela.vega", "Gabriela", "Vega", R.RESPONSIBLE, ["CONT", "LEG", "SEG", "INF", "AMB"]),
        ("daniela.freire", "Daniela", "Freire", R.SUPERVISOR, []),
    ],
    "LS": [
        ("veronica.idrovo", "Verónica", "Idrovo Maldonado", R.ADMIN, []),
        ("andrea.andrade", "Andrea", "Andrade", R.RESPONSIBLE, ["TH", "SST", "RSE"]),
        (
            "byron.cevallos",
            "Byron",
            "Cevallos",
            R.RESPONSIBLE,
            ["CONT", "LEG", "SEG", "INF", "AMB"],
        ),
        ("paola.salcedo", "Paola", "Salcedo", R.SUPERVISOR, []),
    ],
    "VC": [
        ("andres.buestan", "Andrés", "Buestán Moreno", R.ADMIN, []),
        ("camila.vega", "Camila", "Vega", R.RESPONSIBLE, ["TH", "SST", "RSE"]),
        (
            "andrea.cevallos",
            "Andrea",
            "Cevallos",
            R.RESPONSIBLE,
            ["CONT", "LEG", "SEG", "INF", "AMB"],
        ),
        ("fernando.moreno", "Fernando", "Moreno", R.SUPERVISOR, []),
    ],
}
AUDITOR = ("auditoria.externa", "Auditoría", "Externa Asociada")
DOMAINS = {
    "LC": "demo-laarcourier.ec",
    "LS": "demo-laarseguridad.ec",
    "VC": "demo-virtualcreate.ec",
}

# (nombre, área, entidad, tipo, periodicidad, evidencia, fundamento, due_day, due_month, empresas)
TEMPLATES = [
    (
        "Declaración de IVA",
        "CONT",
        "SRI",
        "regulatoria",
        "mensual",
        "Formulario 104 y comprobante de pago",
        "Ley de Régimen Tributario Interno — Reglamento de comprobantes de venta, retención y declaración de IVA.",
        28,
        None,
        "LC LS VC",
    ),
    (
        "Retenciones en la Fuente del Impuesto a la Renta",
        "CONT",
        "SRI",
        "regulatoria",
        "mensual",
        "Formulario 103 y comprobante de pago",
        "Ley de Régimen Tributario Interno, Art. 50.",
        28,
        None,
        "LC LS VC",
    ),
    (
        "Aportes al IESS (personal y patronal)",
        "TH",
        "IESS",
        "regulatoria",
        "mensual",
        "Planilla de aportes IESS pagada",
        "Ley de Seguridad Social.",
        15,
        None,
        "LC LS VC",
    ),
    (
        "Mantenimiento de extintores",
        "SST",
        "BOMB",
        "interna",
        "mensual",
        "Reporte de inspección firmado",
        "Política interna de seguridad ocupacional.",
        30,
        None,
        "LC LS VC",
    ),
    (
        "Décimo Tercer Sueldo",
        "TH",
        "MDT",
        "regulatoria",
        "anual",
        "Rol de pagos y comprobante de transferencia",
        "Código del Trabajo.",
        24,
        12,
        "LC LS VC",
    ),
    (
        "Décimo Cuarto Sueldo",
        "TH",
        "MDT",
        "regulatoria",
        "anual",
        "Rol de pagos y comprobante de transferencia",
        "Código del Trabajo.",
        15,
        8,
        "LC LS VC",
    ),
    (
        "Participación de Utilidades a Trabajadores",
        "TH",
        "MDT",
        "regulatoria",
        "anual",
        "Acta de reparto y comprobantes de pago",
        "Código del Trabajo.",
        15,
        4,
        "LC LS VC",
    ),
    (
        "Permiso de Funcionamiento — Cuerpo de Bomberos",
        "LEG",
        "BOMB",
        "regulatoria",
        "anual",
        "Permiso emitido en PDF",
        "Normativa municipal de prevención de incendios.",
        31,
        3,
        "LC LS VC",
    ),
    (
        "Patente Municipal",
        "LEG",
        "GAD",
        "regulatoria",
        "anual",
        "Comprobante de pago de patente",
        "Código Orgánico de Organización Territorial (COOTAD).",
        31,
        5,
        "LC LS VC",
    ),
    (
        "Renovación de Póliza Multiriesgo",
        "SEG",
        "ASEG",
        "contractual",
        "anual",
        "Póliza renovada y comprobante de pago de prima",
        "Contrato de póliza vigente con la aseguradora.",
        30,
        6,
        "LC LS",
    ),
    (
        "Revisión de Contrato de Arriendo",
        "INF",
        "ARR",
        "contractual",
        "anual",
        "Contrato o adenda firmada",
        "Contrato de arrendamiento vigente.",
        1,
        7,
        "LC LS VC",
    ),
    (
        "Matriz de Identificación de Peligros y Evaluación de Riesgos",
        "SST",
        "MDT",
        "regulatoria",
        "anual",
        "Matriz de riesgos actualizada y firmada",
        "Decisión 584 (2004) Art. 11; Decreto Ejecutivo 255 (2024) Art. 27 y 28.",
        30,
        9,
        "LC LS VC",
    ),
    (
        "Licencia Ambiental",
        "AMB",
        "MINAM",
        "regulatoria",
        "anual",
        "Licencia ambiental emitida",
        "Ley de Gestión Ambiental Art. 31; Reglamento de Licencia Ambiental.",
        30,
        11,
        "LC LS",
    ),
    (
        "Programa de Responsabilidad Social Empresarial (RSE)",
        "RSE",
        "MDT",
        "interna",
        "anual",
        "Informe anual de RSE",
        "Acuerdo Ministerial 097 (2017).",
        15,
        12,
        "LC LS VC",
    ),
]

# Etapa del período actual: (días hasta el vencimiento, etapa, avance, con evidencia)
CURRENT_RECIPES = [
    (-6, Period.Stage.IN_PREPARATION, 40, False),  # incumplido
    (0, Period.Stage.PENDING_VALIDATION, 95, True),  # vence hoy, pendiente de validación
    (18, Period.Stage.NOT_STARTED, 0, False),
    (9, Period.Stage.IN_PREPARATION, 35, True),
    (4, Period.Stage.PENDING_VALIDATION, 95, True),
]
PRIORITIES = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def _stable_index(text: str, size: int) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) % size


def sample_pdf(title: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setTitle(title)
    pdf.drawString(72, 760, "Documento de demostración — datos ficticios")
    pdf.drawString(72, 740, title[:90])
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Crea usuarios, obligaciones y períodos de demostración (datos ficticios)."

    def add_arguments(self, parser):
        parser.add_argument("--allow-production", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError("seed_demo solo se ejecuta con DEBUG=True (o --allow-production).")
        password = os.environ.get("DEMO_USERS_PASSWORD")
        if not password:
            raise CommandError("Defina DEMO_USERS_PASSWORD con la contraseña de los usuarios demo.")
        call_command("seed_catalogs", stdout=self.stdout)
        with transaction.atomic():
            created = self._seed(password)
        self.stdout.write(self.style.SUCCESS(f"Demo lista: {created} períodos creados."))

    def _user(self, username, first, last, email, password) -> User:
        user, created = User.objects.get_or_create(
            username=username, defaults={"first_name": first, "last_name": last, "email": email}
        )
        if created:
            user.set_password(password)
            user.save()
        return user

    def _seed(self, password: str) -> int:
        areas = {area.code: area for area in Area.objects.all()}
        entities = {entity.code: entity for entity in ControlEntity.objects.all()}
        auditor = self._user(*AUDITOR, "auditor@demo-auditorias.ec", password)
        created = 0
        for company in Company.objects.filter(code__in=PEOPLE):
            get_config(company)
            responsible_by_area, admin, supervisor = {}, None, None
            for username, first, last, role, area_codes in PEOPLE[company.code]:
                email = f"{username}@{DOMAINS[company.code]}"
                user = self._user(username, first, last, email, password)
                membership, _ = Membership.objects.get_or_create(
                    user=user, company=company, defaults={"role": role}
                )
                membership.areas.set([areas[code] for code in area_codes])
                for code in area_codes:
                    responsible_by_area[code] = user
                admin = user if role == R.ADMIN else admin
                supervisor = user if role == R.SUPERVISOR else supervisor
            Membership.objects.get_or_create(
                user=auditor, company=company, defaults={"role": R.AUDITOR}
            )
            if company.general_manager_id is None:
                company.general_manager = admin
                company.save(update_fields=["general_manager", "updated_at"])
            for template in TEMPLATES:
                created += self._seed_obligation(
                    company, template, areas, entities, responsible_by_area, supervisor
                )
        return created

    def _seed_obligation(
        self, company, template, areas, entities, responsible_by_area, supervisor
    ) -> int:
        name, area, entity, type_, periodicity, evidence, basis, day, month, companies = template
        if company.code not in companies.split():
            return 0
        obligation, created = Obligation.objects.get_or_create(
            company=company,
            name=name,
            defaults={
                "description": f"{name} — {company.short_name}.",
                "area": areas[area],
                "control_entity": entities[entity],
                "type": type_,
                "periodicity": periodicity,
                "expected_evidence": evidence,
                "legal_basis": basis,
                "due_day": day,
                "due_month": month,
                "default_priority": PRIORITIES[_stable_index(name + company.code, 3)],
            },
        )
        if not created and obligation.periods.exists():
            return 0
        responsible = responsible_by_area[area]
        today = timezone.localdate()
        monthly = periodicity == Obligation.Periodicity.MONTHLY
        recipe = CURRENT_RECIPES[_stable_index(company.code + name, len(CURRENT_RECIPES))]
        common = {"obligation": obligation, "responsible": responsible, "supervisor": supervisor}

        previous_due = today - timedelta(days=35 if monthly else 300)
        previous = PeriodService.create_period(
            due=previous_due, label=period_label(periodicity, previous_due), **common
        )
        late = _stable_index(name, 4) == 0
        self._close(previous, supervisor, completed_delta=8 if late else -3)

        current_due = today + timedelta(days=recipe[0])
        current = PeriodService.create_period(
            due=current_due, label=period_label(periodicity, current_due), **common
        )
        offset, stage, progress, with_evidence = recipe
        if with_evidence:
            self._attach(current, responsible, draft=True)
        current.stage, current.progress = stage, progress
        if stage == Period.Stage.PENDING_VALIDATION:
            current.submitted_at = timezone.now() - timedelta(days=1)
            current.submitted_by = responsible
            record_event(
                current,
                actor=responsible,
                action="period.submitted",
                description="Enviado a validación",
            )
        current.save()
        return 2

    def _attach(self, period, user, draft=False) -> Document:
        title = f"{period.obligation.expected_evidence}{' (borrador)' if draft else ''} — {period.label}"
        content = sample_pdf(title)
        document = Document(
            period=period,
            original_name=f"{title}.pdf"[:255],
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by=user,
        )
        document.file.save(document.original_name, ContentFile(content), save=False)
        document.save()
        record_event(
            period,
            actor=user,
            action="document.uploaded",
            description=f"Evidencia cargada: {document.original_name}",
        )
        return document

    def _close(self, period, validator, completed_delta: int) -> None:
        self._attach(period, period.responsible)
        completed = period.due_at + timedelta(days=completed_delta)
        period.stage = Period.Stage.PENDING_VALIDATION
        period.submitted_at = completed
        period.submitted_by = period.responsible
        period.completed_at = completed
        period.validated_at = completed + timedelta(days=1)
        period.validated_by = validator
        period.is_closed = True
        period.progress = 100
        period.reminders_suspended = True
        period.save()
        late = completed_delta > 0
        record_event(
            period,
            actor=validator,
            action="period.validated",
            description="Cierre validado" + (" — Finalizada fuera de plazo" if late else ""),
            reason=(
                "Se conserva el atraso para efectos de reportes."
                if late
                else "Cumplimiento dentro del plazo."
            ),
        )
