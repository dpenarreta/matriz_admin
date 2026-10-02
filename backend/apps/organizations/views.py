from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.request_meta import get_request_context

from .access import (
    Cap,
    accessible_companies,
    get_access,
    matrix_roles,
    require_access,
    require_capability,
)
from .models import Company, Membership
from .serializers import (
    CompanySerializer,
    CompanySettingsWriteSerializer,
    MatrixRoleSerializer,
    MembershipCreateSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
    MyCompanySerializer,
    PersonSerializer,
)
from .services import CompanyService, MembershipService


def get_company(company_id) -> Company:
    return get_object_or_404(Company, pk=company_id, is_active=True)


class MyCompaniesView(APIView):
    """Empresas donde el usuario tiene rol, con sus capacidades. Es lo que el
    frontend usa para el selector de empresa y para mostrar u ocultar botones
    (la autorización real se vuelve a comprobar en cada endpoint)."""

    def get(self, request):
        accesses = [
            get_access(request.user, company) for company in accessible_companies(request.user)
        ]
        return Response([MyCompanySerializer(access).data for access in accesses if access])


class CompanyDetailView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        access = require_access(request, company)
        return Response(MyCompanySerializer(access).data)

    def patch(self, request, company_id):
        company = get_company(company_id)
        require_capability(
            request, company, Cap.CONFIGURE, "Solo un Administrador puede modificar la empresa."
        )
        serializer = CompanySettingsWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        company = CompanyService.update_settings(
            actor=request.user,
            company=company,
            context=get_request_context(request),
            **serializer.validated_data,
        )
        return Response(CompanySerializer(company).data)


class CompanyPeopleView(APIView):
    """Personas con rol activo en la empresa (para elegir responsable,
    suplente, supervisor y aprobador)."""

    def get(self, request, company_id):
        company = get_company(company_id)
        require_access(request, company)
        memberships = (
            Membership.objects.filter(company=company, is_active=True, user__is_active=True)
            .select_related("user", "role")
            .order_by("user__first_name", "user__last_name", "user__username")
        )
        return Response(
            [
                {
                    **PersonSerializer(m.user).data,
                    "role": m.role_id,
                    "role_label": m.role.name,
                }
                for m in memberships
            ]
        )


class MembershipListView(APIView):
    def get(self, request, company_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.MANAGE_MEMBERS)
        memberships = (
            Membership.objects.filter(company=company, is_active=True)
            .select_related("user", "role")
            .prefetch_related("areas")
        )
        return Response(MembershipSerializer(memberships, many=True).data)

    def post(self, request, company_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.MANAGE_MEMBERS)
        serializer = MembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = MembershipService.add(
            actor=request.user,
            company=company,
            user=serializer.validated_data["identifier"],
            role=serializer.validated_data["role"],
            areas=serializer.validated_data.get("areas", []),
            context=get_request_context(request),
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class MembershipDetailView(APIView):
    def _get(self, request, company_id, membership_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.MANAGE_MEMBERS)
        return get_object_or_404(Membership, pk=membership_id, company=company, is_active=True)

    def patch(self, request, company_id, membership_id):
        membership = self._get(request, company_id, membership_id)
        serializer = MembershipUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        membership = MembershipService.update(
            actor=request.user,
            membership=membership,
            role=serializer.validated_data.get("role"),
            areas=serializer.validated_data.get("areas"),
            context=get_request_context(request),
        )
        return Response(MembershipSerializer(membership).data)

    def delete(self, request, company_id, membership_id):
        membership = self._get(request, company_id, membership_id)
        MembershipService.deactivate(
            actor=request.user, membership=membership, context=get_request_context(request)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyRolesView(APIView):
    """Roles asignables en la empresa (los que otorgan permisos matriz.*),
    con sus permisos, para el selector y la tabla de la pestaña "Usuarios y
    roles". Se editan en Administración del sistema → Roles."""

    def get(self, request, company_id):
        company = get_company(company_id)
        require_capability(request, company, Cap.MANAGE_MEMBERS)
        return Response(MatrixRoleSerializer(matrix_roles(), many=True).data)
