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
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger("bugtracker")


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
        # Ensure notification_email has default if not provided
        if 'notification_email' not in data:
            data['notification_email'] = ''
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
        # send notifications for status change
        try:
            from django.shortcuts import resolve_url
            # build a simple plain and HTML body
            subject = f"[BugTracker] Status changed for BUG-{bug.pk}: {bug.title}"
            plain = f"Ticket: {bug.title}\nChanged by: {getattr(changed_by, 'get_full_name', lambda: changed_by)()}\nOld status: {old_status}\nNew status: {new_status}\nNote: {note}"
            html = f"<h3>Ticket: {bug.title}</h3><p>Changed by: {getattr(changed_by, 'get_full_name', lambda: changed_by)()}</p><p>Old status: <strong>{old_status}</strong><br>New status: <strong>{new_status}</strong></p><p>Note: {note}</p>"
            # use request-less sending by constructing a dummy request url in views layer; here we'll queue via signals or views will call notifications
        except Exception:
            pass
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
        # notify recipients
        try:
            addrs = (bug.notification_email or "").strip()
            if addrs:
                recipients = [a.strip() for a in addrs.split(',') if a.strip()]
                if recipients:
                    actor = getattr(changed_by, 'get_full_name', None)
                    actor_name = actor() if callable(actor) else (str(changed_by) if changed_by else 'System')
                    subject = f"[BugTracker] Priority changed for BUG-{bug.pk}: {bug.title}"
                    plain = (
                        f"Ticket: {bug.title}\n"
                        f"Changed by: {actor_name}\n"
                        f"New priority: {priority}\n"
                        f"Reason: {reason}\n\n"
                        f"View ticket: {settings.SITE_URL}{bug.get_absolute_url()}"
                    )
                    html = (
                        f"<h3>Ticket: {bug.title}</h3>"
                        f"<p>Changed by: {actor_name}</p>"
                        f"<p>New priority: <strong>{priority}</strong></p>"
                        f"<p>Reason: {reason}</p>"
                        f"<p><a href=\"{settings.SITE_URL}{bug.get_absolute_url()}\">View ticket</a></p>"
                    )
                    send_mail(subject, plain, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False, html_message=html)
        except Exception:
            logger.exception("Failed to send priority change notifications for bug %s", bug.pk)
        return bug
