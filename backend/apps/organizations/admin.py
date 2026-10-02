from django.contrib import admin

from .models import Area, Branch, Company, ControlEntity, Membership


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("code", "short_name", "country", "timezone", "is_active")
    search_fields = ("code", "short_name", "legal_name")
    inlines = [BranchInline]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(ControlEntity)
class ControlEntityAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_active")
    list_filter = ("company", "role", "is_active")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("areas",)
