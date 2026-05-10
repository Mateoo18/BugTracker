from django.db import transaction
from django.utils import timezone

from domain.priority import PriorityInputs, calculate_priority_score, map_score_to_priority
from infrastructure.models import (
    Bug,
    BugAssignment,
    BugAttachment,
    BugPriorityHistory,
    BugStatusHistory,
)


class PriorityService:
    @staticmethod
    def calculate_for_bug(bug: Bug) -> tuple[int, str]:
        age_days = max((timezone.now() - bug.created_at).days, 0)
        inputs = PriorityInputs(
            severity=bug.severity,
            impact=bug.impact,
            similar_reports=bug.similar_count,
            age_days=age_days,
            module_importance=bug.module_importance,
        )
        score = calculate_priority_score(inputs)
        return score, map_score_to_priority(score)

    @classmethod
    def recalculate(cls, bug: Bug, changed_by=None, reason: str = "Automatic recalculation") -> Bug:
        score, priority = cls.calculate_for_bug(bug)
        old_priority = bug.priority
        old_score = bug.priority_score
        bug.priority_score = score
        if not bug.priority_override:
            bug.priority = priority
        bug.save(update_fields=["priority_score", "priority", "updated_at"])
        BugPriorityHistory.objects.create(
            bug=bug,
            old_priority=old_priority,
            new_priority=bug.priority,
            old_score=old_score,
            new_score=score,
            changed_by=changed_by,
            reason=reason,
            is_manual_override=False,
        )
        return bug


class BugService:
    @staticmethod
    @transaction.atomic
    def create_bug(*, reporter, data, attachment=None) -> Bug:
        bug = Bug.objects.create(reporter=reporter, **data)
        if attachment:
            BugAttachment.objects.create(
                bug=bug,
                uploaded_by=reporter,
                image=attachment,
                caption="Initial screenshot",
            )
        BugStatusHistory.objects.create(
            bug=bug,
            old_status="",
            new_status=bug.status,
            changed_by=reporter,
            note="Bug submitted",
        )
        PriorityService.recalculate(bug, changed_by=reporter, reason="Initial priority calculation")
        return bug


class BugWorkflowService:
    @staticmethod
    @transaction.atomic
    def assign_bug(*, bug: Bug, team, assignee=None, assigned_by=None, note: str = "") -> BugAssignment:
        old_status = bug.status
        BugAssignment.objects.filter(bug=bug, is_active=True).update(is_active=False)
        assignment = BugAssignment.objects.create(
            bug=bug,
            team=team,
            assignee=assignee,
            assigned_by=assigned_by,
            note=note,
            is_active=True,
        )
        bug.status = "assigned"
        bug.save(update_fields=["status", "updated_at"])
        BugStatusHistory.objects.create(
            bug=bug,
            old_status=old_status,
            new_status="assigned",
            changed_by=assigned_by,
            note=note or "Bug assigned",
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def change_status(*, bug: Bug, new_status: str, changed_by=None, note: str = "") -> Bug:
        old_status = bug.status
        bug.status = new_status
        if new_status == "duplicate":
            bug.is_duplicate = True
        if new_status == "reopened":
            bug.is_reopened = True
        if new_status == "verified":
            bug.is_verified = True
        bug.save(update_fields=["status", "is_duplicate", "is_reopened", "is_verified", "updated_at"])
        BugStatusHistory.objects.create(
            bug=bug,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            note=note,
        )
        return bug

    @staticmethod
    @transaction.atomic
    def override_priority(*, bug: Bug, priority: str, changed_by, reason: str) -> Bug:
        old_priority = bug.priority
        old_score = bug.priority_score
        bug.priority = priority
        bug.priority_override = True
        bug.priority_override_reason = reason
        bug.save(update_fields=["priority", "priority_override", "priority_override_reason", "updated_at"])
        BugPriorityHistory.objects.create(
            bug=bug,
            old_priority=old_priority,
            new_priority=priority,
            old_score=old_score,
            new_score=bug.priority_score,
            changed_by=changed_by,
            reason=reason,
            is_manual_override=True,
        )
        return bug
