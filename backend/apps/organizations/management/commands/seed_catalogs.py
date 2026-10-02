"""Siembra los catálogos base: 8 áreas, 8 entidades de control y las 3
empresas del grupo con su sucursal principal. Idempotente (se puede
ejecutar varias veces). No crea usuarios ni contraseñas.

    python manage.py seed_catalogs
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.organizations.models import Area, Branch, Company, ControlEntity

AREAS = [
    ("CONT", "Contabilidad y Tributario"),
    ("TH", "Talento Humano y Nómina"),
    ("SST", "Seguridad y Salud en el Trabajo"),
    ("AMB", "Ambiental"),
    ("LEG", "Legal y Permisos"),
    ("SEG", "Seguros y Pólizas"),
    ("INF", "Arriendos e Infraestructura"),
    ("RSE", "Responsabilidad Social"),
]

CONTROL_ENTITIES = [
    ("SRI", "Servicio de Rentas Internas (SRI)"),
    ("IESS", "Instituto Ecuatoriano de Seguridad Social (IESS)"),
    ("MDT", "Ministerio del Trabajo"),
    ("BOMB", "Cuerpo de Bomberos"),
    ("GAD", "GAD Municipal"),
    ("ASEG", "Aseguradora (contrato de póliza)"),
    ("ARR", "Arrendador (contrato de arriendo)"),
    ("MINAM", "Ministerio del Ambiente, Agua y Transición Ecológica"),
]

COMPANIES = [
    {
        "code": "LC",
        "legal_name": "Laarcourier Express S.A.",
        "short_name": "Laarcourier",
        "activity": "Mensajería, courier y logística de última milla",
        "color": "#164b86",
        "branch": "Matriz Quito",
    },
    {
        "code": "LS",
        "legal_name": "Laar Seguridad Cía. Ltda.",
        "short_name": "Laar Seguridad",
        "activity": "Servicios de seguridad privada y vigilancia",
        "color": "#0e7c86",
        "branch": "Oficina Central Guayaquil",
    },
    {
        "code": "VC",
        "legal_name": "Virtual Create S.A.",
        "short_name": "Virtual Create",
        "activity": "Desarrollo de software y soluciones digitales",
        "color": "#5b3fa0",
        "branch": "Oficina Cuenca",
    },
]


class Command(BaseCommand):
    help = "Siembra áreas, entidades de control y empresas (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, name in AREAS:
            Area.objects.update_or_create(code=code, defaults={"name": name})
        for code, name in CONTROL_ENTITIES:
            ControlEntity.objects.update_or_create(code=code, defaults={"name": name})
        for data in COMPANIES:
            data = dict(data)
            branch = data.pop("branch")
            company, _ = Company.objects.get_or_create(code=data["code"], defaults=data)
            Branch.objects.get_or_create(company=company, name=branch)
        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogos listos: {Area.objects.count()} áreas, "
                f"{ControlEntity.objects.count()} entidades, {Company.objects.count()} empresas."
            )
        )
