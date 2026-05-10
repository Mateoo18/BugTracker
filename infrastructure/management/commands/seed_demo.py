from django.core.management.base import BaseCommand

from application.services import BugService, BugWorkflowService
from infrastructure.models import Bug, Company, Team, User


class Command(BaseCommand):
    help = "Create demo companies, teams, users and bugs."

    def handle(self, *args, **options):
        User.objects.filter(role="ba").update(role=User.Role.PRODUCT_OWNER)

        companies = {
            "acme": ("ACME Software", "ACME Portal", [("Billing", "Payments"), ("Core Platform", "Auth")]),
            "northwind": ("Northwind Retail", "Northwind Commerce", [("Checkout", "Cart"), ("Fulfillment", "Orders")]),
            "globex": ("Globex Finance", "Globex Banking", [("Mobile Banking", "Mobile App"), ("Risk", "Fraud Detection")]),
            "initech": ("Initech Cloud", "Initech Desk", [("Support", "Tickets"), ("Analytics", "Reports")]),
        }

        company_objects = {}
        team_objects = {}
        for slug, (name, product, teams) in companies.items():
            company, _ = Company.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "product_name": product, "is_active": True},
            )
            company_objects[slug] = company
            team_objects[slug] = []
            for team_name, module in teams:
                team, _ = Team.objects.update_or_create(
                    company=company,
                    name=team_name,
                    defaults={"module": module},
                )
                team_objects[slug].append(team)

        demo_users = [
            ("reporter", "Olivia", "Reporter", User.Role.REPORTER, "acme", []),
            ("admin", "Ava", "Admin", User.Role.ADMIN, "acme", ["Billing", "Core Platform"]),
            ("po.acme", "Emma", "Carter", User.Role.PRODUCT_OWNER, "acme", ["Billing", "Core Platform"]),
            ("dev.acme.james", "James", "Wilson", User.Role.DEVELOPER, "acme", ["Billing"]),
            ("dev.acme.sophia", "Sophia", "Martin", User.Role.DEVELOPER, "acme", ["Core Platform"]),
            ("po.northwind", "Liam", "Anderson", User.Role.PRODUCT_OWNER, "northwind", ["Checkout", "Fulfillment"]),
            ("dev.northwind.noah", "Noah", "Brown", User.Role.DEVELOPER, "northwind", ["Checkout"]),
            ("dev.northwind.mia", "Mia", "Davis", User.Role.DEVELOPER, "northwind", ["Fulfillment"]),
            ("po.globex", "Charlotte", "Miller", User.Role.PRODUCT_OWNER, "globex", ["Mobile Banking", "Risk"]),
            ("dev.globex.ethan", "Ethan", "Moore", User.Role.DEVELOPER, "globex", ["Mobile Banking"]),
            ("dev.globex.amelia", "Amelia", "Taylor", User.Role.DEVELOPER, "globex", ["Risk"]),
            ("po.initech", "Benjamin", "Thomas", User.Role.PRODUCT_OWNER, "initech", ["Support", "Analytics"]),
            ("dev.initech.harper", "Harper", "Jackson", User.Role.DEVELOPER, "initech", ["Support"]),
            ("dev.initech.lucas", "Lucas", "White", User.Role.DEVELOPER, "initech", ["Analytics"]),
        ]

        users = {}
        for username, first_name, last_name, role, company_slug, team_names in demo_users:
            company = company_objects[company_slug]
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    "company": company,
                    "must_change_password": False,
                    "is_staff": role == User.Role.ADMIN,
                    "is_superuser": role == User.Role.ADMIN,
                },
            )
            user.set_password("demo1234")
            user.save()
            user.teams.set([team for team in team_objects[company_slug] if team.name in team_names])
            users[username] = user

        if not Bug.objects.exists():
            payment_bug = BugService.create_bug(
                reporter=users["reporter"],
                data={
                    "company": company_objects["acme"],
                    "product": company_objects["acme"].product_name,
                    "module": "Payments",
                    "title": "Payment confirmation is not displayed",
                    "description": "After a successful card payment the confirmation screen stays blank.",
                    "reproduction_steps": "1. Add product to cart\n2. Pay by card\n3. Wait for confirmation",
                    "expected_result": "User sees order number and payment confirmation.",
                    "actual_result": "The page stays blank after redirect from payment provider.",
                    "severity": "high",
                    "impact": 4,
                    "similar_count": 6,
                    "module_importance": 5,
                },
            )
            BugWorkflowService.assign_bug(
                bug=payment_bug,
                team=team_objects["acme"][0],
                assignee=users["dev.acme.james"],
                assigned_by=users["po.acme"],
                note="High customer impact, assign to Billing.",
            )

            resolved_bug = BugService.create_bug(
                reporter=users["reporter"],
                data={
                    "company": company_objects["northwind"],
                    "product": company_objects["northwind"].product_name,
                    "module": "Cart",
                    "title": "Cart badge count did not update after removing an item",
                    "description": "The item is removed but the header badge still shows the old count.",
                    "reproduction_steps": "1. Add two items\n2. Remove one item\n3. Check the header badge",
                    "expected_result": "The badge shows the current cart count.",
                    "actual_result": "The badge shows the previous count until refresh.",
                    "severity": "medium",
                    "impact": 2,
                    "similar_count": 3,
                    "module_importance": 4,
                },
            )
            BugWorkflowService.change_status(
                bug=resolved_bug,
                new_status="resolved",
                changed_by=users["po.northwind"],
                note="Fixed by recalculating cart state after item removal.",
            )

            mobile_bug = BugService.create_bug(
                reporter=users["reporter"],
                data={
                    "company": company_objects["globex"],
                    "product": company_objects["globex"].product_name,
                    "module": "Mobile App",
                    "title": "Mobile app freezes on biometric login",
                    "description": "Some Android users are stuck after successful fingerprint confirmation.",
                    "reproduction_steps": "1. Enable biometric login\n2. Open the app\n3. Confirm fingerprint",
                    "expected_result": "User lands on the account overview.",
                    "actual_result": "The loading spinner never finishes.",
                    "severity": "critical",
                    "impact": 5,
                    "similar_count": 14,
                    "module_importance": 5,
                },
            )
            BugWorkflowService.assign_bug(
                bug=mobile_bug,
                team=team_objects["globex"][0],
                assignee=users["dev.globex.ethan"],
                assigned_by=users["po.globex"],
                note="Critical login path issue.",
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready. Password for all demo users: demo1234"))
