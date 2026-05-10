from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Bug,
    BugAssignment,
    BugAttachment,
    BugComment,
    BugPriorityHistory,
    BugStatusHistory,
    Company,
    Team,
    User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Bugtracker", {"fields": ("role", "company", "teams")}),
    )
    list_display = ("username", "email", "role", "company", "is_staff", "is_active")
    list_filter = ("role", "company", "is_staff", "is_active")
    filter_horizontal = ("groups", "user_permissions", "teams")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "product_name", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "product_name")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "module")
    list_filter = ("company",)
    search_fields = ("name", "module")


class BugAttachmentInline(admin.TabularInline):
    model = BugAttachment
    extra = 0


class BugAssignmentInline(admin.TabularInline):
    model = BugAssignment
    extra = 0


@admin.register(Bug)
class BugAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "module", "status", "priority", "severity", "priority_score")
    list_filter = ("status", "priority", "severity", "company", "module")
    search_fields = ("title", "description", "actual_result")
    readonly_fields = ("priority_score", "created_at", "updated_at")
    inlines = [BugAttachmentInline, BugAssignmentInline]


admin.site.register(BugComment)
admin.site.register(BugStatusHistory)
admin.site.register(BugPriorityHistory)
