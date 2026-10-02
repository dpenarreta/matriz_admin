from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.users.models import User

from .access import PREFIX, CompanyAccess, matrix_roles
from .models import Area, Branch, Company, ControlEntity, Membership


def full_name(user: User | None) -> str:
    if user is None:
        return ""
    return user.get_full_name() or user.username


class PersonSerializer(serializers.ModelSerializer):
    """Datos mínimos de una persona para mostrarla o elegirla en un formulario."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email"]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        return full_name(obj)


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "code", "name"]


class ControlEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlEntity
        fields = ["id", "code", "name"]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name"]


class CompanySerializer(serializers.ModelSerializer):
    general_manager = PersonSerializer(read_only=True)

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
        ]
        read_only_fields = fields


class CompanySettingsWriteSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=200, required=False)
    short_name = serializers.CharField(max_length=80, required=False)
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


class MyCompanySerializer(serializers.Serializer):
    """Empresa accesible + rol y capacidades del usuario en ella."""

    def to_representation(self, access: CompanyAccess):
        company = access.company
        return {
            **CompanySerializer(company).data,
            "role": {"id": access.role_id, "name": access.role_name},
            "role_label": access.role_name,
            "capabilities": sorted(access.capabilities),
            "is_superuser": access.is_superuser,
        }


class MatrixRoleSerializer(serializers.ModelSerializer):
    """Rol del template base visto desde la matriz: solo sus permisos `matriz.*`."""

    permission_codenames = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permission_codenames"]
        read_only_fields = fields

    def get_permission_codenames(self, obj) -> list[str]:
        return sorted(p.codename for p in obj.permissions.all() if p.codename.startswith(PREFIX))


class MembershipSerializer(serializers.ModelSerializer):
    user = PersonSerializer(read_only=True)
    role = serializers.SerializerMethodField()
    role_label = serializers.CharField(source="role.name", read_only=True)
    areas = AreaSerializer(many=True, read_only=True)
    company = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "user", "company", "role", "role_label", "areas", "is_active", "created_at"]
        read_only_fields = fields

    def get_role(self, obj):
        return {"id": obj.role_id, "name": obj.role.name}

    def get_company(self, obj):
        return {
            "id": obj.company_id,
            "code": obj.company.code,
            "short_name": obj.company.short_name,
        }


class MatrixRoleField(serializers.PrimaryKeyRelatedField):
    """Solo roles que otorgan algún permiso de la matriz."""

    def get_queryset(self):
        return matrix_roles()


class MembershipCreateSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Usuario o correo de una cuenta existente.")
    role_id = MatrixRoleField(source="role")
    area_ids = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), many=True, required=False, source="areas"
    )

    def validate_identifier(self, value):
        user = (
            User.objects.filter(username__iexact=value).first()
            or User.objects.filter(email__iexact=value).first()
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError(
                "No existe un usuario activo con ese usuario o correo."
            )
        return user


class MembershipUpdateSerializer(serializers.Serializer):
    role_id = MatrixRoleField(source="role", required=False)
    area_ids = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), many=True, required=False, source="areas"
    )
