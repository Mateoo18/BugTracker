from django.test import TestCase

from application.services import BugService, BugWorkflowService, PriorityService
from infrastructure.models import Bug, BugAssignment, BugStatusHistory, Company, Team, User


class BugWorkflowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="TestCo", slug="testco", product_name="Tracker")
        self.team = Team.objects.create(company=self.company, name="Core", module="Auth")
        self.reporter = User.objects.create_user(
            username="reporter",
            password="pass",
            role=User.Role.REPORTER,
            company=self.company,
        )
        self.po = User.objects.create_user(username="po", password="pass", role=User.Role.PRODUCT_OWNER, company=self.company)
        self.dev = User.objects.create_user(username="dev", password="pass", role=User.Role.DEVELOPER, company=self.company)
        self.dev.teams.add(self.team)

    def test_create_bug_calculates_priority_and_history(self):
        bug = BugService.create_bug(
            reporter=self.reporter,
            data={
                "company": self.company,
                "product": "Tracker",
                "module": "Auth",
                "title": "Login fails",
                "description": "Cannot log in",
                "reproduction_steps": "Open login and submit valid credentials.",
                "expected_result": "User is logged in.",
                "actual_result": "User sees error.",
                "severity": "critical",
                "impact": 5,
                "similar_count": 10,
                "module_importance": 5,
            },
        )

        self.assertGreater(bug.priority_score, 0)
        self.assertIn(bug.priority, {"P0", "P1"})
        self.assertTrue(BugStatusHistory.objects.filter(bug=bug, new_status="triage").exists())

    def test_assign_bug_creates_active_assignment(self):
        bug = self._bug()
        assignment = BugWorkflowService.assign_bug(
            bug=bug,
            team=self.team,
            assignee=self.dev,
            assigned_by=self.po,
            note="Take it",
        )

        bug.refresh_from_db()
        self.assertEqual(bug.status, "assigned")
        self.assertTrue(assignment.is_active)
        self.assertEqual(BugAssignment.objects.filter(bug=bug, is_active=True).count(), 1)

    def test_manual_priority_override_is_preserved_on_recalculate(self):
        bug = self._bug()
        BugWorkflowService.override_priority(bug=bug, priority="P0", changed_by=self.po, reason="VIP customer")
        PriorityService.recalculate(bug, changed_by=self.po)
        bug.refresh_from_db()
        self.assertEqual(bug.priority, "P0")
        self.assertTrue(bug.priority_override)

    def _bug(self):
        return BugService.create_bug(
            reporter=self.reporter,
            data={
                "company": self.company,
                "product": "Tracker",
                "module": "Auth",
                "title": "Small bug",
                "description": "Description",
                "reproduction_steps": "Steps",
                "expected_result": "Expected",
                "actual_result": "Actual",
                "severity": "medium",
                "impact": 3,
                "similar_count": 0,
                "module_importance": 3,
            },
        )
