"""Administración del sistema (panel `/admin` del template base) para los
módulos de la matriz: empresas y sucursales, catálogos (áreas y entidades)
y roles por empresa de cada usuario.

Usan el mismo mecanismo que usuarios y roles del template base: un permiso
del catálogo (`HasModulePermission`), no la membresía por empresa.
"""

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.request_meta import get_request_context
from apps.permissions.permissions import HasModulePermission
from apps.users.models import User

from .access import matrix_roles
from .models import Area, Branch, Company
from .serializers import (
    AreaSerializer,
    BranchSerializer,
    MatrixRoleField,
    MatrixRoleSerializer,
    MembershipSerializer,
    PersonSerializer,
)
from .services import (
    CATALOG_MODELS,
    BranchService,
    CatalogService,
    CompanyService,
    MembershipService,
)


class EmpresasPermission(HasModulePermission):
    view_permission = "empresas.ver"
    write_permission = "empresas.editar"


class CatalogosPermission(HasModulePermission):
    view_permission = "catalogos.ver"
    write_permission = "catalogos.editar"


class UsuariosEditPermission(HasModulePermission):
    view_permission = "usuarios.ver"
    write_permission = "usuarios.editar"


# --- Serializadores -----------------------------------------------------------


class AdminCompanySerializer(serializers.ModelSerializer):
    general_manager = PersonSerializer(read_only=True)
    branches = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "code",
            "legal_name",
            "short_name",
            "country",
            "activity",
            "timezone",
            "color",
            "compliance_date_basis",
            "general_manager",
            "is_active",
            "branches",
            "member_count",
        ]
        read_only_fields = fields

    def get_branches(self, obj):
        return [{**BranchSerializer(b).data, "is_active": b.is_active} for b in obj.branches.all()]

    def get_member_count(self, obj) -> int:
        return obj.memberships.filter(is_active=True).count()


class AdminCompanyWriteSerializer(serializers.Serializer):
    code = serializers.RegexField(r"^[A-Za-z0-9_-]{1,10}$")
    legal_name = serializers.CharField(max_length=200)
    short_name = serializers.CharField(max_length=80)
    country = serializers.CharField(max_length=80, required=False)
    activity = serializers.CharField(max_length=255, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False)
    color = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", required=False)
    compliance_date_basis = serializers.ChoiceField(
        choices=Company.ComplianceDateBasis.choices, required=False
    )
    general_manager_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="general_manager",
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(required=False)

    def validate_code(self, value):
        return value.upper()


class BranchWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    is_active = serializers.BooleanField(required=False)


class CatalogWriteSerializer(serializers.Serializer):
    code = serializers.RegexField(r"^[A-Za-z0-9_-]{1,10}$")
    name = serializers.CharField(max_length=160)


class MembershipEntrySerializer(serializers.Serializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source="company"
    )
    role_id = MatrixRoleField(source="role")
    area_ids = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), many=True, required=False, source="areas"
    )


class MembershipReplaceSerializer(serializers.Serializer):
    memberships = MembershipEntrySerializer(many=True)

    def validate_memberships(self, value):
        companies = [entry["company"].pk for entry in value]
        if len(companies) != len(set(companies)):
            raise serializers.ValidationError("Una empresa aparece más de una vez.")
        return value


# --- Vistas ---------------------------------------------------------------------


class AdminCompanyListView(APIView):
    permission_classes = [IsAuthenticated, EmpresasPermission]

    def get(self, request):
        companies = Company.objects.prefetch_related("branches").select_related("general_manager")
        return Response(AdminCompanySerializer(companies.order_by("short_name"), many=True).data)

    def post(self, request):
        serializer = AdminCompanyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branches = request.data.get("branches") or []
        company = CompanyService.create(
            actor=request.user,
            context=get_request_context(request),
            branches=[name for name in branches if isinstance(name, str) and name.strip()],
            **serializer.validated_data,
        )
        return Response(AdminCompanySerializer(company).data, status=status.HTTP_201_CREATED)


class AdminCompanyDetailView(APIView):
    permission_classes = [IsAuthenticated, EmpresasPermission]

    def get(self, request, company_id):
        return Response(AdminCompanySerializer(get_object_or_404(Company, pk=company_id)).data)

    def patch(self, request, company_id):
        company = get_object_or_404(Company, pk=company_id)
        serializer = AdminCompanyWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        company = CompanyService.update_settings(
            actor=request.user,
            company=company,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(AdminCompanySerializer(company).data)


class AdminBranchListView(APIView):
    permission_classes = [IsAuthenticated, EmpresasPermission]

    def post(self, request, company_id):
        company = get_object_or_404(Company, pk=company_id)
        serializer = BranchWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = BranchService.save(
            actor=request.user,
            company=company,
            branch=None,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(BranchSerializer(branch).data, status=status.HTTP_201_CREATED)


class AdminBranchDetailView(APIView):
    permission_classes = [IsAuthenticated, EmpresasPermission]

    def patch(self, request, company_id, branch_id):
        company = get_object_or_404(Company, pk=company_id)
        branch = get_object_or_404(Branch, pk=branch_id, company=company)
        serializer = BranchWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        branch = BranchService.save(
            actor=request.user,
            company=company,
            branch=branch,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response({**BranchSerializer(branch).data, "is_active": branch.is_active})


def _catalog_model(kind):
    model = CATALOG_MODELS.get(kind)
    if model is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("Catálogo desconocido.")
    return model


class AdminCatalogListView(APIView):
    permission_classes = [IsAuthenticated, CatalogosPermission]

    def get(self, request, kind):
        model = _catalog_model(kind)
        return Response(AreaSerializer(model.objects.order_by("name"), many=True).data)

    def post(self, request, kind):
        model = _catalog_model(kind)
        serializer = CatalogWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = CatalogService.save(
            actor=request.user,
            model=model,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(AreaSerializer(instance).data, status=status.HTTP_201_CREATED)


class AdminCatalogDetailView(APIView):
    permission_classes = [IsAuthenticated, CatalogosPermission]

    def patch(self, request, kind, item_id):
        model = _catalog_model(kind)
        instance = get_object_or_404(model, pk=item_id)
        serializer = CatalogWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = CatalogService.save(
            actor=request.user,
            model=model,
            instance=instance,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(AreaSerializer(instance).data)

    def delete(self, request, kind, item_id):
        model = _catalog_model(kind)
        CatalogService.delete(
            actor=request.user,
            instance=get_object_or_404(model, pk=item_id),
            context=get_request_context(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMatrixRolesView(APIView):
    """Roles que otorgan permisos de la matriz (para asignarlos por empresa)."""

    permission_classes = [IsAuthenticated, UsuariosEditPermission]

    def get(self, request):
        return Response(MatrixRoleSerializer(matrix_roles(), many=True).data)


class AdminUserMembershipsView(APIView):
    """Roles por empresa de un usuario, desde el formulario de usuario."""

    permission_classes = [IsAuthenticated, UsuariosEditPermission]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        memberships = (
            user.memberships.filter(is_active=True)
            .select_related("company", "role")
            .prefetch_related("areas")
        )
        return Response(MembershipSerializer(memberships, many=True).data)

    def put(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = MembershipReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        memberships = MembershipService.replace_for_user(
            actor=request.user,
            user=user,
            entries=serializer.validated_data["memberships"],
            context=get_request_context(request),
        )
        return Response(MembershipSerializer(memberships, many=True).data)
