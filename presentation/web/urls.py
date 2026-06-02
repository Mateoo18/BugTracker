from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("accounts/login/", views.UserLoginView.as_view(), name="accounts_login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("dashboard/user/", views.user_dashboard, name="user_dashboard"),
    path("dashboard/staff/", views.staff_dashboard, name="staff_dashboard"),
    path("dashboard/developers/new/", views.developer_create, name="developer_create"),
    path("dashboard/teams/new/", views.team_create, name="team_create"),
    path("password/change-required/", views.force_password_change, name="force_password_change"),
    path("bugs/", views.bug_list, name="bug_list"),
    path("bugs/kanban/", views.kanban_board, name="kanban_board"),
    path("bugs/new/", views.bug_create, name="bug_create"),
    path("bugs/public-resolved/", views.public_resolved_bugs, name="public_resolved_bugs"),
    path("bugs/<int:pk>/", views.bug_detail, name="bug_detail"),
    path("bugs/<int:pk>/assign/", views.assign_bug, name="assign_bug"),
    path("bugs/<int:pk>/status/", views.change_status, name="change_status"),
    path("bugs/<int:pk>/priority/", views.override_priority, name="override_priority"),
    path("bugs/<int:pk>/priority/recalculate/", views.recalculate_priority, name="recalculate_priority"),
]
