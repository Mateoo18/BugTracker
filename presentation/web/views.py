import logging
import secrets
import string

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.conf import settings
from django.views.generic import CreateView

from application.services import BugService, BugWorkflowService, PriorityService
from infrastructure.models import Bug, User
from shared_kernel.roles import is_ba_or_admin, is_staff_role

from .forms import (
    AssignmentForm,
    BugCommentForm,
    BugReportForm,
    DeveloperCreateForm,
    PriorityOverrideForm,
    RegistrationForm,
    StatusChangeForm,
    TeamCreateForm,
)

logger = logging.getLogger("bugtracker")


class UserLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        if self.request.user.must_change_password:
            return reverse_lazy("web:force_password_change")
        return super().get_success_url()


def _generate_temporary_password(length=14):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password):
            return password


class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("web:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Your account has been created.")
        return response


def _visible_bugs_for(user):
    if user.role == "admin":
        return Bug.objects.all()
    if user.role in {"developer", "po", "ba"} and user.company_id:
        return Bug.objects.filter(company=user.company)
    return Bug.objects.filter(Q(reporter=user) | Q(status__in=["resolved", "verified", "closed"]))


def _apply_bug_filters(queryset, request, *, allow_status=True):
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    severity = request.GET.get("severity", "").strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(module__icontains=search)
            | Q(product__icontains=search)
            | Q(company__name__icontains=search)
        )
    if status and allow_status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if severity:
        queryset = queryset.filter(severity=severity)
    return queryset


def _applied_filters(request, *, include_status=True):
    labels = {
        "q": "Search",
        "status": "Status",
        "priority": "Priority",
        "severity": "Severity",
    }
    allowed = ["q", "priority", "severity"]
    if include_status:
        allowed.insert(1, "status")
    return [
        {"label": labels[key], "value": request.GET.get(key)}
        for key in allowed
        if request.GET.get(key)
    ]


@login_required
def dashboard(request):
    if is_staff_role(request.user):
        return redirect("web:staff_dashboard")
    return redirect("web:user_dashboard")


@login_required
def user_dashboard(request):
    my_bugs = Bug.objects.filter(reporter=request.user).order_by("-created_at")
    public_resolved = Bug.objects.filter(status__in=["resolved", "verified", "closed"]).order_by("-updated_at")[:8]
    stats = my_bugs.values("status").annotate(count=Count("id"))
    return render(
        request,
        "dashboard/user_dashboard.html",
        {"my_bugs": my_bugs[:8], "public_resolved": public_resolved, "stats": list(stats)},
    )


@login_required
def staff_dashboard(request):
    if not is_staff_role(request.user):
        return redirect("web:user_dashboard")
    user_team_ids = request.user.teams.values_list("id", flat=True)
    assigned = Bug.objects.filter(assignments__is_active=True, assignments__assignee=request.user).distinct()
    team_bugs = Bug.objects.filter(assignments__is_active=True, assignments__team_id__in=user_team_ids).distinct()
    company_bugs = Bug.objects.filter(company=request.user.company) if request.user.company_id else Bug.objects.none()
    if request.user.role == "admin":
        company_bugs = Bug.objects.all()
    chart_data = list(company_bugs.values("status").annotate(count=Count("id")).order_by("status"))
    return render(
        request,
        "dashboard/staff_dashboard.html",
        {
            "assigned_bugs": assigned[:10],
            "team_bugs": team_bugs[:10],
            "company_bugs": company_bugs[:10],
            "chart_data": chart_data,
            "can_manage": is_ba_or_admin(request.user),
            "can_create_developers": is_ba_or_admin(request.user) and request.user.company_id,
        },
    )


@login_required
def bug_list(request):
    bugs = _apply_bug_filters(_visible_bugs_for(request.user), request)
    paginator = Paginator(bugs.select_related("company", "reporter"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "bugs/bug_list.html",
        {
            "page_obj": page_obj,
            "status_choices": Bug.Status.choices,
            "priority_choices": Bug.Priority.choices,
            "severity_choices": Bug.Severity.choices,
            "applied_filters": _applied_filters(request),
        },
    )


@login_required
def public_resolved_bugs(request):
    bugs = Bug.objects.filter(status__in=["resolved", "verified", "closed"]).select_related("company", "reporter")
    bugs = _apply_bug_filters(bugs, request, allow_status=False)
    paginator = Paginator(bugs, 10)
    return render(
        request,
        "bugs/bug_list.html",
        {
            "page_obj": paginator.get_page(request.GET.get("page")),
            "public_board": True,
            "status_choices": Bug.Status.choices,
            "priority_choices": Bug.Priority.choices,
            "severity_choices": Bug.Severity.choices,
            "applied_filters": _applied_filters(request, include_status=False),
        },
    )


@login_required
def bug_detail(request, pk):
    bug = get_object_or_404(_visible_bugs_for(request.user), pk=pk)
    if request.method == "POST" and request.POST.get("action") == "comment":
        form = BugCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.bug = bug
            comment.author = request.user
            if comment.is_internal and not is_staff_role(request.user):
                comment.is_internal = False
            comment.save()
            messages.success(request, "Comment added.")
            return redirect(bug)
    assignment_form = AssignmentForm(company=bug.company)
    status_form = StatusChangeForm(initial={"status": bug.status})
    priority_form = PriorityOverrideForm(initial={"priority": bug.priority})
    comments = bug.comments.all()
    if not is_staff_role(request.user):
        comments = comments.filter(is_internal=False)
    return render(
        request,
        "bugs/bug_detail.html",
        {
            "bug": bug,
            "active_assignment": bug.assignments.filter(is_active=True).select_related("team", "assignee", "assigned_by").first(),
            "comments": comments,
            "comment_form": BugCommentForm(),
            "assignment_form": assignment_form,
            "status_form": status_form,
            "priority_form": priority_form,
            "can_manage": is_ba_or_admin(request.user),
        },
    )


@login_required
def bug_create(request):
    if request.method == "POST":
        form = BugReportForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data.copy()
            image = data.pop("image", None)
            bug = BugService.create_bug(reporter=request.user, data=data, attachment=image)
            logger.info("Bug %s created by %s", bug.pk, request.user.username)
            messages.success(request, "Bug report saved.")
            return redirect(bug)
    else:
        initial = {}
        if request.user.company_id:
            initial["company"] = request.user.company
            initial["product"] = request.user.company.product_name
        form = BugReportForm(initial=initial)
    return render(request, "bugs/bug_form.html", {"form": form})


@login_required
def assign_bug(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    if not is_ba_or_admin(request.user):
        messages.error(request, "You do not have permission to assign bugs.")
        return redirect(bug)
    form = AssignmentForm(request.POST, company=bug.company)
    if form.is_valid():
        BugWorkflowService.assign_bug(
            bug=bug,
            team=form.cleaned_data["team"],
            assignee=form.cleaned_data["assignee"],
            assigned_by=request.user,
            note=form.cleaned_data["note"],
        )
        messages.success(request, "Bug assigned.")
    else:
        messages.error(request, "Could not assign this bug. Check the form data.")
    return redirect(bug)


@login_required
def change_status(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    if not is_ba_or_admin(request.user):
        messages.error(request, "You do not have permission to change bug status.")
        return redirect(bug)
    form = StatusChangeForm(request.POST)
    if form.is_valid():
        BugWorkflowService.change_status(
            bug=bug,
            new_status=form.cleaned_data["status"],
            changed_by=request.user,
            note=form.cleaned_data["note"],
        )
        messages.success(request, "Status changed.")
    return redirect(bug)


@login_required
def override_priority(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    if not is_ba_or_admin(request.user):
        messages.error(request, "You do not have permission to override priority.")
        return redirect(bug)
    form = PriorityOverrideForm(request.POST)
    if form.is_valid():
        BugWorkflowService.override_priority(
            bug=bug,
            priority=form.cleaned_data["priority"],
            changed_by=request.user,
            reason=form.cleaned_data["reason"],
        )
        messages.success(request, "Priority overridden.")
    return redirect(bug)


@login_required
def recalculate_priority(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    if not is_ba_or_admin(request.user):
        messages.error(request, "You do not have permission to recalculate priority.")
        return redirect(bug)
    PriorityService.recalculate(bug, changed_by=request.user, reason="Manual web recalculation")
    messages.success(request, "Priority recalculated.")
    return redirect(bug)


@login_required
def developer_create(request):
    if not is_ba_or_admin(request.user) or not request.user.company_id:
        messages.error(request, "Only Product Owners and admins assigned to a company can create developer accounts.")
        return redirect("web:staff_dashboard")
    if request.method == "POST":
        form = DeveloperCreateForm(request.POST, company=request.user.company)
        if form.is_valid():
            temporary_password = _generate_temporary_password()
            developer = None
            try:
                developer = form.save(temporary_password=temporary_password)
                login_url = request.build_absolute_uri(reverse_lazy("web:login"))
                send_mail(
                    subject="Your BugTracker developer account",
                    message=(
                        f"Hello {developer.first_name},\n\n"
                        f"A developer account has been created for you in BugTracker.\n\n"
                        f"Username: {developer.username}\n"
                        f"Temporary password: {temporary_password}\n"
                        f"Login page: {login_url}\n\n"
                        "After logging in, you will be asked to set your own password."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[developer.email],
                    fail_silently=False,
                )
            except Exception as exc:
                if developer:
                    developer.delete()
                logger.exception("Could not send developer invite email")
                messages.error(request, f"Developer account was not created because the invite email could not be sent: {exc}")
                return redirect("web:developer_create")
            messages.success(
                request,
                f"Developer account created for {developer.get_full_name()} ({developer.username}). A temporary password email has been sent.",
            )
            return redirect("web:staff_dashboard")
    else:
        form = DeveloperCreateForm(company=request.user.company)
    developers = User.objects.filter(company=request.user.company, role=User.Role.DEVELOPER).prefetch_related("teams")
    return render(request, "dashboard/developer_form.html", {"form": form, "developers": developers})


@login_required
def team_create(request):
    if not is_ba_or_admin(request.user) or not request.user.company_id:
        messages.error(request, "Only Product Owners and admins assigned to a company can create teams.")
        return redirect("web:staff_dashboard")
    if request.method == "POST":
        form = TeamCreateForm(request.POST, company=request.user.company)
        if form.is_valid():
            team = form.save()
            messages.success(request, f"Team '{team.name}' has been created.")
            return redirect("web:staff_dashboard")
    else:
        form = TeamCreateForm(company=request.user.company)
    teams = request.user.company.teams.all()
    return render(request, "dashboard/team_form.html", {"form": form, "teams": teams})


@login_required
def force_password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed.")
            return redirect("web:dashboard")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "registration/force_password_change.html", {"form": form})
