from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True)
    product_name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return self.name


class Team(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=160)
    module = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["company__name", "name"]
        unique_together = ("company", "name")

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"


class User(AbstractUser):
    class Role(models.TextChoices):
        REPORTER = "reporter", "Reporter"
        DEVELOPER = "developer", "Developer"
        PRODUCT_OWNER = "po", "Product Owner"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REPORTER)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    teams = models.ManyToManyField(Team, blank=True, related_name="members")
    must_change_password = models.BooleanField(default=False)

    def is_business_admin(self) -> bool:
        return self.role in {self.Role.PRODUCT_OWNER, self.Role.ADMIN}

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class Bug(TimeStampedModel):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        TRIAGE = "triage", "Triage"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        VERIFIED = "verified", "Verified"
        DUPLICATE = "duplicate", "Duplicate"
        REOPENED = "reopened", "Reopened"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        P0 = "P0", "P0"
        P1 = "P1", "P1"
        P2 = "P2", "P2"
        P3 = "P3", "P3"

    title = models.CharField(max_length=220)
    description = models.TextField()
    reproduction_steps = models.TextField()
    expected_result = models.TextField()
    actual_result = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.TRIAGE)
    priority = models.CharField(max_length=2, choices=Priority.choices, default=Priority.P3)
    priority_score = models.PositiveIntegerField(default=0)
    priority_override = models.BooleanField(default=False)
    priority_override_reason = models.TextField(blank=True)
    impact = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    similar_count = models.PositiveIntegerField(default=0)
    module = models.CharField(max_length=120)
    module_importance = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    product = models.CharField(max_length=160)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="bugs")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reported_bugs")
    duplicate_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicates")
    is_duplicate = models.BooleanField(default=False)
    is_reopened = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["priority", "-priority_score", "-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["company", "module"]),
            models.Index(fields=["reporter", "status"]),
        ]

    def __str__(self) -> str:
        return f"BUG-{self.pk}: {self.title}"

    def get_absolute_url(self):
        return reverse("web:bug_detail", kwargs={"pk": self.pk})


class BugComment(TimeStampedModel):
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="bug_comments")
    body = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment on {self.bug_id}"


class BugAssignment(TimeStampedModel):
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="assignments")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="bug_assignments")
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_bugs")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="made_assignments")
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "team", "assignee"])]

    def __str__(self) -> str:
        target = self.assignee or self.team
        return f"{self.bug_id} -> {target}"


class BugStatusHistory(models.Model):
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="status_changes")
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.bug_id}: {self.old_status} -> {self.new_status}"


class BugAttachment(TimeStampedModel):
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="bug_attachments")
    image = models.ImageField(
        upload_to="bug_attachments/%Y/%m/%d/",
        validators=[FileExtensionValidator(["png", "jpg", "jpeg"])],
    )
    caption = models.CharField(max_length=180, blank=True)

    def __str__(self) -> str:
        return self.caption or self.image.name


class BugPriorityHistory(models.Model):
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="priority_history")
    old_priority = models.CharField(max_length=2, blank=True)
    new_priority = models.CharField(max_length=2)
    old_score = models.PositiveIntegerField(default=0)
    new_score = models.PositiveIntegerField(default=0)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="priority_changes")
    reason = models.TextField(blank=True)
    is_manual_override = models.BooleanField(default=False)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.bug_id}: {self.old_priority} -> {self.new_priority}"
