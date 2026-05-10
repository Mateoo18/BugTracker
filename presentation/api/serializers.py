from rest_framework import serializers

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


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "company", "teams", "password")

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        teams = validated_data.pop("teams", [])
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        user.teams.set(teams)
        return user


class BugAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugAttachment
        fields = "__all__"
        read_only_fields = ("uploaded_by",)


class BugCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = BugComment
        fields = "__all__"
        read_only_fields = ("author",)


class BugStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BugStatusHistory
        fields = "__all__"


class BugPriorityHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BugPriorityHistory
        fields = "__all__"


class BugAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugAssignment
        fields = "__all__"
        read_only_fields = ("assigned_by",)


class BugSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.username", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    attachments = BugAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Bug
        fields = "__all__"
        read_only_fields = (
            "reporter",
            "priority",
            "priority_score",
            "priority_override",
            "priority_override_reason",
            "is_duplicate",
            "is_reopened",
            "is_verified",
        )


class CreateBugSerializer(serializers.Serializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    product = serializers.CharField(max_length=160)
    module = serializers.CharField(max_length=120)
    title = serializers.CharField(max_length=220)
    description = serializers.CharField()
    reproduction_steps = serializers.CharField()
    expected_result = serializers.CharField()
    actual_result = serializers.CharField()
    severity = serializers.ChoiceField(choices=Bug.Severity.choices)
    impact = serializers.IntegerField(min_value=1, max_value=5, default=3)
    similar_count = serializers.IntegerField(min_value=0, default=0)
    module_importance = serializers.IntegerField(min_value=1, max_value=5, default=3)
    image = serializers.ImageField(required=False)


class AssignBugSerializer(serializers.Serializer):
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class ChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Bug.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class PriorityOverrideSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=Bug.Priority.choices)
    reason = serializers.CharField()
