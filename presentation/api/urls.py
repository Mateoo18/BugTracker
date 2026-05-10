from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("companies", views.CompanyViewSet)
router.register("teams", views.TeamViewSet)
router.register("users", views.UserViewSet)
router.register("bugs", views.BugViewSet, basename="bugs")
router.register("comments", views.BugCommentViewSet, basename="comments")
router.register("assignments", views.BugAssignmentViewSet, basename="assignments")
router.register("attachments", views.BugAttachmentViewSet, basename="attachments")
router.register("status-history", views.BugStatusHistoryViewSet, basename="status-history")
router.register("priority-history", views.BugPriorityHistoryViewSet, basename="priority-history")

urlpatterns = [
    path("bugs/create/", views.CreateBugAPIView.as_view(), name="api-create-bug"),
    path("bugs/<int:pk>/assign/", views.AssignBugAPIView.as_view(), name="api-assign-bug"),
    path("bugs/<int:pk>/status/", views.ChangeStatusAPIView.as_view(), name="api-change-status"),
    path("bugs/<int:pk>/priority/recalculate/", views.RecalculatePriorityAPIView.as_view(), name="api-recalculate-priority"),
    path("bugs/my/", views.my_bugs, name="api-my-bugs"),
    path("bugs/assigned/", views.assigned_bugs, name="api-assigned-bugs"),
    path("bugs/company-board/", views.company_board, name="api-company-board"),
    path("bugs/public-resolved/", views.public_resolved_bugs, name="api-public-resolved"),
    path("auth/", include("rest_framework.urls")),
    path("", include(router.urls)),
]
