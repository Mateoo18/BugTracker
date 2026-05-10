from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from application.services import BugService, BugWorkflowService, PriorityService
from infrastructure.models import (
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
from shared_kernel.roles import is_staff_role

from .permissions import BugObjectPermission, IsAdminRole, IsBAOrAdmin
from .serializers import (
    AssignBugSerializer,
    BugAssignmentSerializer,
    BugAttachmentSerializer,
    BugCommentSerializer,
    BugPriorityHistorySerializer,
    BugSerializer,
    BugStatusHistorySerializer,
    ChangeStatusSerializer,
    CompanySerializer,
    CreateBugSerializer,
    PriorityOverrideSerializer,
    TeamSerializer,
    UserSerializer,
)


def paginated_response(request, queryset, serializer_class):
    paginator = PageNumberPagination()
    paginator.page_size = 10
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


def visible_bugs_for(user):
    if user.role == "admin":
        return Bug.objects.all()
    if user.role in {"developer", "po", "ba"} and user.company_id:
        return Bug.objects.filter(company_id=user.company_id)
    return Bug.objects.filter(Q(reporter=user) | Q(status__in=["resolved", "verified", "closed"]))


class AdminOnlyModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]


class CompanyViewSet(AdminOnlyModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    search_fields = ["name", "product_name"]
    ordering_fields = ["name", "created_at"]


class TeamViewSet(AdminOnlyModelViewSet):
    queryset = Team.objects.select_related("company")
    serializer_class = TeamSerializer
    search_fields = ["name", "module", "company__name"]
    ordering_fields = ["name", "company__name"]


class UserViewSet(AdminOnlyModelViewSet):
    queryset = User.objects.prefetch_related("teams")
    serializer_class = UserSerializer
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "role"]


class BugViewSet(viewsets.ModelViewSet):
    serializer_class = BugSerializer
    permission_classes = [IsAuthenticated, BugObjectPermission]
    search_fields = ["title", "description", "module", "product", "company__name"]
    ordering_fields = ["priority_score", "created_at", "updated_at", "status", "severity"]

    def get_queryset(self):
        queryset = visible_bugs_for(self.request.user).select_related("company", "reporter").prefetch_related("attachments")
        status_value = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        severity = self.request.query_params.get("severity")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if priority:
            queryset = queryset.filter(priority=priority)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset

    def perform_create(self, serializer):
        bug = serializer.save(reporter=self.request.user)
        PriorityService.recalculate(bug, changed_by=self.request.user, reason="API CRUD calculation")


class BugCommentViewSet(viewsets.ModelViewSet):
    serializer_class = BugCommentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["body"]

    def get_queryset(self):
        bugs = visible_bugs_for(self.request.user)
        queryset = BugComment.objects.filter(bug__in=bugs)
        if not is_staff_role(self.request.user):
            queryset = queryset.filter(is_internal=False)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class BugAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = BugAssignmentSerializer
    permission_classes = [IsAuthenticated, IsBAOrAdmin]
    queryset = BugAssignment.objects.select_related("bug", "team", "assignee", "assigned_by")

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class BugAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = BugAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BugAttachment.objects.filter(bug__in=visible_bugs_for(self.request.user))

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class BugStatusHistoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BugStatusHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BugStatusHistory.objects.filter(bug__in=visible_bugs_for(self.request.user))


class BugPriorityHistoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BugPriorityHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BugPriorityHistory.objects.filter(bug__in=visible_bugs_for(self.request.user))


class CreateBugAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateBugSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        image = data.pop("image", None)
        bug = BugService.create_bug(reporter=request.user, data=data, attachment=image)
        return Response(BugSerializer(bug, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AssignBugAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBAOrAdmin]

    def post(self, request, pk):
        bug = get_object_or_404(Bug, pk=pk)
        serializer = AssignBugSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = BugWorkflowService.assign_bug(
            bug=bug,
            team=serializer.validated_data["team"],
            assignee=serializer.validated_data.get("assignee"),
            assigned_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(BugAssignmentSerializer(assignment).data)


class ChangeStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBAOrAdmin]

    def post(self, request, pk):
        bug = get_object_or_404(Bug, pk=pk)
        serializer = ChangeStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bug = BugWorkflowService.change_status(
            bug=bug,
            new_status=serializer.validated_data["status"],
            changed_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(BugSerializer(bug, context={"request": request}).data)


class RecalculatePriorityAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBAOrAdmin]

    def post(self, request, pk):
        bug = get_object_or_404(Bug, pk=pk)
        override = PriorityOverrideSerializer(data=request.data)
        if request.data.get("priority"):
            override.is_valid(raise_exception=True)
            bug = BugWorkflowService.override_priority(
                bug=bug,
                priority=override.validated_data["priority"],
                changed_by=request.user,
                reason=override.validated_data["reason"],
            )
        else:
            bug = PriorityService.recalculate(bug, changed_by=request.user, reason="API manual recalculation")
        return Response(BugSerializer(bug, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_bugs(request):
    queryset = Bug.objects.filter(reporter=request.user)
    return paginated_response(request, queryset, BugSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assigned_bugs(request):
    queryset = Bug.objects.filter(assignments__is_active=True, assignments__assignee=request.user).distinct()
    return paginated_response(request, queryset, BugSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_board(request):
    queryset = Bug.objects.filter(company=request.user.company) if request.user.company_id else Bug.objects.none()
    if request.user.role == "admin":
        queryset = Bug.objects.all()
    return paginated_response(request, queryset, BugSerializer)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def public_resolved_bugs(request):
    queryset = Bug.objects.filter(status__in=["resolved", "verified", "closed"])
    return paginated_response(request, queryset, BugSerializer)
