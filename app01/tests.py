"""HRMS 单元测试 - 8 个用例覆盖认证/CRUD/业务逻辑."""
from decimal import Decimal
from datetime import date, time

from django.test import TestCase, Client
from django.urls import reverse

from app01.models import (
    User, Role, Department, Employee,
    Attendance, Salary, Announcement,
)


# ─── 1. 未登录拦截 ────────────────────────────────────────────────────────────
class AuthRedirectTest(TestCase):
    """未登录访问受保护页面 → 302 到 /login/."""

    def test_dashboard_redirect(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_dept_list_redirect(self):
        r = self.client.get(reverse("dept_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)


# ─── 2. 登录页白名单 ──────────────────────────────────────────────────────────
class LoginPageTest(TestCase):
    """/login/ 在白名单，匿名可访问."""

    def test_login_page_200(self):
        r = self.client.get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "form")


# ─── 3. 超级用户 force_login 后正常访问 ───────────────────────────────────────
class SuperUserAccessTest(TestCase):
    """is_superuser 直接过所有 @perm_required."""

    @classmethod
    def setUpTestData(cls):
        cls.su = User.objects.create_superuser("admin", "a@x.com", "pw123456")

    def test_dashboard_200(self):
        self.client.force_login(self.su)
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)

    def test_dept_list_200(self):
        self.client.force_login(self.su)
        r = self.client.get(reverse("dept_list"))
        self.assertEqual(r.status_code, 200)

    def test_stats_page_200(self):
        self.client.force_login(self.su)
        r = self.client.get(reverse("stats_page"))
        self.assertEqual(r.status_code, 200)


# ─── 4. 部门 CRUD ────────────────────────────────────────────────────────────
class DepartmentCrudTest(TestCase):
    """部门创建 + 列表 + 删除确认页."""

    @classmethod
    def setUpTestData(cls):
        cls.su = User.objects.create_superuser("admin", "a@x.com", "pw123456")
        cls.dept = Department.objects.create(
            name="研发部", code="DEV", description="后端团队"
        )

    def setUp(self):
        self.client.force_login(self.su)

    def test_dept_list_shows_dept(self):
        r = self.client.get(reverse("dept_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "研发部")

    def test_dept_create(self):
        r = self.client.post(reverse("dept_add"), {
            "name": "市场部", "code": "MKT", "description": "推广",
        })
        self.assertRedirects(r, reverse("dept_list"))
        self.assertTrue(Department.objects.filter(code="MKT").exists())

    def test_dept_delete_get_confirm(self):
        r = self.client.get(reverse("dept_delete", args=[self.dept.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "确认删除")


# ─── 5. 薪资实发自动计算 ──────────────────────────────────────────────────────
class SalaryAutoTotalTest(TestCase):
    """Salary.save() 时 total = base_salary + bonus - deduction."""

    @classmethod
    def setUpTestData(cls):
        cls.su = User.objects.create_superuser("admin", "a@x.com", "pw123456")
        cls.dept = Department.objects.create(name="人力", code="HR")
        cls.emp = Employee.objects.create(
            name="张三", age=28, gender=1, phone="13900000001",
            hire_date=date(2023, 1, 1), depart=cls.dept,
        )

    def test_total_calculation(self):
        sal = Salary.objects.create(
            employee=self.emp, month=date(2026, 1, 1),
            base_salary=Decimal("8000"),
            bonus=Decimal("2000"),
            deduction=Decimal("500"),
        )
        sal.refresh_from_db()
        self.assertEqual(sal.total, Decimal("9500"))

    def test_total_negative_allowed(self):
        """扣款大于工资时 total 可以为负（模型没做约束）."""
        sal = Salary.objects.create(
            employee=self.emp, month=date(2026, 2, 1),
            base_salary=Decimal("5000"),
            bonus=Decimal("0"),
            deduction=Decimal("6000"),
        )
        sal.refresh_from_db()
        self.assertEqual(sal.total, Decimal("-1000"))


# ─── 6. Employee.ensure_account 自动建登录账号 ─────────────────────────────────
class EmployeeEnsureAccountTest(TestCase):
    """ensure_account() 为员工创建 User，username=phone, password=123456."""

    @classmethod
    def setUpTestData(cls):
        cls.emp_role = Role.objects.create(name="员工", code="employee")
        cls.dept = Department.objects.create(name="研发部", code="DEV")
        cls.emp = Employee.objects.create(
            name="李四", age=25, gender=1, phone="13900000002",
            hire_date=date(2023, 6, 1), depart=cls.dept,
        )

    def test_creates_user(self):
        self.assertIsNone(self.emp.user)
        user = self.emp.ensure_account(role=self.emp_role)
        self.emp.refresh_from_db()
        self.assertIsNotNone(self.emp.user)
        self.assertEqual(user.username, "13900000002")
        self.assertTrue(user.check_password("123456"))

    def test_idempotent_call(self):
        """多次调用不重复建 User."""
        u1 = self.emp.ensure_account(role=self.emp_role)
        u2 = self.emp.ensure_account(role=self.emp_role)
        self.assertEqual(u1.pk, u2.pk)
        self.assertEqual(User.objects.count(), 1)


# ─── 7. 考勤 unique_together（一人一天一条） ────────────────────────────────────
class AttendanceUniqueTest(TestCase):
    """(employee, date) 联合唯一，重复创建抛 IntegrityError."""

    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="技术部", code="TECH")
        cls.emp = Employee.objects.create(
            name="王五", age=30, gender=1, phone="13900000003",
            hire_date=date(2022, 3, 15), depart=cls.dept,
        )
        cls.day = date(2026, 11, 1)

    def test_unique_constraint(self):
        Attendance.objects.create(
            employee=self.emp, date=self.day,
            clock_in=time(9, 0), clock_out=time(18, 0),
            status="normal",
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                employee=self.emp, date=self.day, status="normal",
            )


# ─── 8. 公告创建 + 置顶 ───────────────────────────────────────────────────────
class AnnouncementTest(TestCase):
    """公告可以置顶，列表按 is_top 倒序."""

    @classmethod
    def setUpTestData(cls):
        cls.publisher = User.objects.create_superuser("boss", "b@x.com", "pw123456")

    def test_toggle_top(self):
        a1 = Announcement.objects.create(
            title="普通公告", content="内容一", publisher=self.publisher,
            is_top=False,
        )
        a2 = Announcement.objects.create(
            title="重要公告", content="内容二", publisher=self.publisher,
            is_top=True,
        )
        # 置顶的排前面
        ids = list(Announcement.objects.values_list("pk", flat=True))
        self.assertEqual(ids[0], a2.pk)

    def test_create_via_view(self):
        self.client.force_login(self.publisher)
        r = self.client.post(reverse("ann_add"), {
            "title": "测试公告",
            "content": "这是测试内容",
        })
        self.assertRedirects(r, reverse("ann_list"))
        self.assertTrue(Announcement.objects.filter(title="测试公告").exists())
