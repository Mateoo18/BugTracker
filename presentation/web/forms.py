from django import forms
from django.contrib.auth.forms import UserCreationForm

from infrastructure.models import Bug, BugComment, Company, Team, User, BugAttachment


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.REPORTER
        if commit:
            user.save()
        return user


class BugReportForm(forms.ModelForm):
    image = forms.ImageField(required=False, help_text="Optional PNG or JPG screenshot, up to 4 MB.")

    class Meta:
        model = Bug
        fields = (
            "company",
            "product",
            "module",
            "title",
            "description",
            "reproduction_steps",
            "expected_result",
            "actual_result",
            "severity",
            "impact",
            "similar_count",
            "module_importance",
        )
        labels = {
            "company": "Company affected by the bug",
            "product": "Product",
            "module": "Module or feature area",
            "title": "Bug title",
            "description": "Description",
            "reproduction_steps": "Steps to reproduce",
            "expected_result": "Expected result",
            "actual_result": "Actual result",
            "severity": "Severity",
            "impact": "User impact",
            "similar_count": "Similar reports",
            "module_importance": "Module importance",
        }


class BugNotificationForm(forms.ModelForm):
    class Meta:
        model = Bug
        fields = ("notification_email", "notification_emails")

    def clean_notification_email(self):
        email = self.cleaned_data.get("notification_email", "").strip()
        return email

    def clean_notification_emails(self):
        txt = self.cleaned_data.get("notification_emails", "")
        # basic split and strip
        emails = [e.strip() for e in txt.split(",") if e.strip()]
        return ",".join(emails)
        help_texts = {
            "module": "Examples: Payments, Login, Reports, Notifications.",
            "severity": "Low = cosmetic or minor, Medium = degraded workflow, High = major feature broken, Critical = outage, data loss, or security risk.",
            "impact": "Scale 1-5: 1 affects one user or a rare edge case, 3 affects a common workflow, 5 blocks many users or revenue-critical work.",
            "similar_count": "How many users or tickets describe the same issue. 0-2 is low, 3-9 is noticeable, 10+ means broad signal.",
            "module_importance": "Scale 1-5: 1 is optional/back-office, 3 is a standard product flow, 5 is core business-critical functionality.",
        }
        widgets = {
            "impact": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "similar_count": forms.NumberInput(attrs={"min": 0}),
            "module_importance": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "reproduction_steps": forms.Textarea(attrs={"rows": 4}),
            "expected_result": forms.Textarea(attrs={"rows": 3}),
            "actual_result": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 4 * 1024 * 1024:
            raise forms.ValidationError("Attachment size must be 4 MB or less.")
        return image


class AssignmentForm(forms.Form):
    team = forms.ModelChoiceField(queryset=Team.objects.none())
    assignee = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        teams = Team.objects.all()
        users = User.objects.filter(role__in=[User.Role.DEVELOPER, User.Role.PRODUCT_OWNER, User.Role.ADMIN])
        if company:
            teams = teams.filter(company=company)
            users = users.filter(company=company)
        self.fields["team"].queryset = teams
        self.fields["assignee"].queryset = users


class StatusChangeForm(forms.Form):
    status = forms.ChoiceField(choices=Bug.Status.choices)
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)


class PriorityOverrideForm(forms.Form):
    priority = forms.ChoiceField(choices=Bug.Priority.choices)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class BugCommentForm(forms.ModelForm):
    class Meta:
        model = BugComment
        fields = ("body", "is_internal")
        labels = {
            "body": "Comment",
            "is_internal": "Internal note",
        }
        help_texts = {
            "is_internal": "Visible only to company staff. Leave unchecked for a public comment visible to the reporter.",
        }
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Add an update, question, workaround, or investigation note...",
                }
            )
        }


class DeveloperCreateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        required=True,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select one or more teams this developer should work with.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "teams")

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["teams"].queryset = Team.objects.filter(company=company) if company else Team.objects.none()

    def save(self, temporary_password, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = User.Role.DEVELOPER
        user.company = self.company
        user.must_change_password = True
        user.set_password(temporary_password)
        if commit:
            user.save()
            user.teams.set(self.cleaned_data["teams"])
        return user


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name", "module")
        labels = {
            "name": "Team name",
            "module": "Primary module",
        }
        help_texts = {
            "module": "Example: Payments, Reports, Mobile App, Auth.",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

    def clean_name(self):
        name = self.cleaned_data["name"]
        if self.company and Team.objects.filter(company=self.company, name__iexact=name).exists():
            raise forms.ValidationError("A team with this name already exists in your company.")
        return name

    def save(self, commit=True):
        team = super().save(commit=False)
        team.company = self.company
        if commit:
            team.save()
        return team


class BugAttachmentForm(forms.ModelForm):
    class Meta:
        model = BugAttachment
        fields = ("image",)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 4 * 1024 * 1024:
            raise forms.ValidationError("Attachment size must be 4 MB or less.")
        return image
