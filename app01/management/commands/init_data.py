"""数据初始化管理命令."""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from datetime import date, time, timedelta
import random
from decimal import Decimal


class Command(BaseCommand):
    help = "初始化演示数据 - 一键写入角色、权限、管理员、部门、员工账号等"

    # 三级角色的权限分配
    ROLE_PERMS = {
        "super_admin": None,  # None 表示全部权限
        "dept_admin": [
            "department_view",
            "employee_view", "employee_add", "employee_edit",
            "attendance_view", "attendance_add", "attendance_edit",
            "salary_view", "salary_add", "salary_edit",
            "announcement_view",
            "task_view", "task_add", "task_edit", "task_delete",
            "stats_view",
        ],
        "employee": [
            "employee_view", "attendance_view", "salary_view",
            "announcement_view", "task_view", "task_edit",
        ],
    }

    ROLE_NAMES = {
        "super_admin": "超级管理员",
        "dept_admin": "部门管理员",
        "employee": "普通员工",
    }

    def handle(self, *args, **options):
        from app01 import models

        self.stdout.write("开始初始化数据...")

        # === 1. 创建权限 ===
        PERMS = [
            ("查看部门", "department_view", "部门"),
            ("新增部门", "department_add", "部门"),
            ("编辑部门", "department_edit", "部门"),
            ("删除部门", "department_delete", "部门"),
            ("查看员工", "employee_view", "员工"),
            ("新增员工", "employee_add", "员工"),
            ("编辑员工", "employee_edit", "员工"),
            ("删除员工", "employee_delete", "员工"),
            ("查看考勤", "attendance_view", "考勤"),
            ("新增考勤", "attendance_add", "考勤"),
            ("编辑考勤", "attendance_edit", "考勤"),
            ("删除考勤", "attendance_delete", "考勤"),
            ("查看薪资", "salary_view", "薪资"),
            ("新增薪资", "salary_add", "薪资"),
            ("编辑薪资", "salary_edit", "薪资"),
            ("删除薪资", "salary_delete", "薪资"),
            ("查看公告", "announcement_view", "公告"),
            ("发布公告", "announcement_add", "公告"),
            ("编辑公告", "announcement_edit", "公告"),
            ("删除公告", "announcement_delete", "公告"),
            ("查看任务", "task_view", "任务"),
            ("新增任务", "task_add", "任务"),
            ("编辑任务", "task_edit", "任务"),
            ("删除任务", "task_delete", "任务"),
            ("查看统计", "stats_view", "统计"),
        ]
        perm_objs = {}
        for name, code, group in PERMS:
            p, _ = models.Permission.objects.get_or_create(code=code, defaults={
                "name": name, "group": group,
            })
            perm_objs[code] = p
        self.stdout.write(f"  创建 {len(perm_objs)} 个权限")

        # === 2. 创建三级角色并分配权限 ===
        role_objs = {}
        for code, perms in self.ROLE_PERMS.items():
            role, _ = models.Role.objects.get_or_create(
                code=code, defaults={"name": self.ROLE_NAMES[code]}
            )
            role.name = self.ROLE_NAMES[code]
            role.save(update_fields=["name"])
            role.permissions.set(
                list(perm_objs.values()) if perms is None else [perm_objs[c] for c in perms]
            )
            role_objs[code] = role
            self.stdout.write(f"  角色 {role.name}: {role.permissions.count()} 项权限")

        # === 3. 创建部门 ===
        depts_data = [
            ("技术部", "TECH", None),
            ("市场部", "MKT", None),
            ("财务部", "FIN", None),
            ("人力资源部", "HR", None),
            ("研发一组", "DEV1", "TECH"),
            ("研发二组", "DEV2", "TECH"),
        ]
        dept_objs = {}
        for name, code, parent_code in depts_data:
            parent = dept_objs.get(parent_code) if parent_code else None
            d, _ = models.Department.objects.get_or_create(code=code, defaults={
                "name": name, "parent": parent,
            })
            dept_objs[code] = d
        self.stdout.write(f"  创建 {len(dept_objs)} 个部门")

        # === 4. 创建超级管理员账号 ===
        admin_user, created = models.User.objects.get_or_create(
            username="admin",
            defaults={
                "is_superuser": True, "is_staff": True,
                "password": make_password("admin123"),
                "role": role_objs["super_admin"],
            },
        )
        if not created and admin_user.role_id != role_objs["super_admin"].id:
            admin_user.role = role_objs["super_admin"]
            admin_user.save(update_fields=["role"])
        self.stdout.write("  创建超级管理员 admin / admin123")

        # === 5. 创建员工（每个员工都分配部门与角色）===
        # (姓名, 部门编码, 角色编码)
        staff_data = [
            ("张三", "DEV1", "employee"),
            ("李四", "DEV2", "employee"),
            ("王五", "TECH", "dept_admin"),      # 技术部管理员（含研发一二组）
            ("赵六", "MKT", "dept_admin"),        # 市场部管理员
            ("钱七", "MKT", "employee"),
            ("孙八", "FIN", "employee"),
            ("周九", "FIN", "employee"),
            ("吴十", "HR", "employee"),
            ("郑十一", "DEV1", "employee"),
            ("冯十二", "HR", "employee"),
            ("陈十三", "MKT", "employee"),
            ("褚十四", "TECH", "employee"),
        ]
        for i, (name, dept_code, role_code) in enumerate(staff_data):
            phone = "138%08d" % (10000000 + i)
            emp, _ = models.Employee.objects.get_or_create(
                phone=phone,
                defaults={
                    "name": name,
                    "age": random.randint(22, 45),
                    "gender": 1 if i % 2 == 0 else 2,
                    "account_balance": Decimal(str(random.randint(1000, 20000))),
                    "hire_date": date(2020, 1, 1) + timedelta(days=i * 120),
                    "depart": dept_objs[dept_code],
                    "status": 1,
                },
            )
            # 固定部门与姓名，保证部门管理员的可见范围稳定
            emp.name = name
            emp.depart = dept_objs[dept_code]
            emp.save()
            # 每个员工都开通登录账号：用户名=手机号，初始密码 123456
            emp.ensure_account(role=role_objs[role_code])
        self.stdout.write(f"  创建 {len(staff_data)} 个员工并开通登录账号")

        # === 6. 创建考勤 ===
        employees = list(models.Employee.objects.filter(status=1))
        today = date.today()
        for _ in range(30):
            emp = random.choice(employees)
            d = today - timedelta(days=random.randint(0, 30))
            in_hour = random.choice([8, 9, 9, 9, 10])
            out_hour = random.choice([17, 17, 18, 18, 19])
            in_min = random.choice([0, 5, 10, 15, 30])
            out_min = random.choice([0, 10, 20, 30, 45])
            models.Attendance.objects.get_or_create(
                employee=emp, date=d,
                defaults={
                    "clock_in": time(in_hour, in_min),
                    "clock_out": time(out_hour, out_min),
                },
            )
        self.stdout.write("  创建考勤记录")

        # === 7. 创建薪资 ===
        for emp in employees[:8]:
            for month_offset in range(6):
                m = today.replace(day=1) - timedelta(days=30 * month_offset)
                m = m.replace(day=1)
                base = Decimal(str(random.choice([6000, 8000, 10000, 12000, 15000])))
                bonus = Decimal(str(random.randint(0, 3000)))
                deduction = Decimal(str(random.randint(0, 500)))
                models.Salary.objects.get_or_create(
                    employee=emp, month=m,
                    defaults={
                        "base_salary": base,
                        "bonus": bonus,
                        "deduction": deduction,
                    },
                )
        self.stdout.write("  创建薪资记录")

        # === 8. 创建公告 ===
        anns = [
            ("系统上线公告", "HRMS 系统正式上线，请各位员工及时登录更新信息。", True),
            ("2025年春节放假通知", "2025年春节放假时间为 1月28日 - 2月3日。", True),
            ("培训通知", "本周五下午 14:00 组织新员工入职培训。", False),
            ("考勤制度更新", "新考勤制度自下月起执行，详细请见附件。", False),
        ]
        for title, content, top in anns:
            models.Announcement.objects.get_or_create(
                title=title, defaults={
                    "content": content, "publisher": admin_user, "is_top": top,
                }
            )
        self.stdout.write(f"  创建 {len(anns)} 条公告")

        # === 9. 创建任务（按部门分散，便于验证数据范围）===
        tasks_data = [
            ("完成 Q4 项目总结", "整理 Q4 各项目数据并输出总结报告", 1, "todo", "DEV1"),
            ("新员工入职培训", "组织 3 名新员工的入职培训工作", 2, "doing", "HR"),
            ("服务器安全巡检", "完成服务器安全补丁更新与漏洞扫描", 2, "todo", "TECH"),
            ("年度财务报表", "完成 2024 年度财务报表编制与审核", 1, "doing", "FIN"),
            ("客户回访", "回访重点客户，收集反馈意见", 3, "todo", "MKT"),
            ("市场推广方案", "制定下季度市场推广方案", 2, "doing", "MKT"),
        ]
        for title, detail, level, status, dept_code in tasks_data:
            owner = models.Employee.objects.filter(depart__code=dept_code).first()
            if owner is None:
                owner = employees[0]
            models.Task.objects.update_or_create(
                title=title, defaults={
                    "detail": detail, "level": level,
                    "owner": owner, "status": status,
                }
            )
        self.stdout.write(f"  创建 {len(tasks_data)} 条任务")

        self.stdout.write(self.style.SUCCESS("演示数据初始化完成！"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=== 登录账号一览（初始密码均为 123456）==="))
        self.stdout.write("  超级管理员: admin / admin123")
        for emp in models.Employee.objects.select_related("user", "depart").order_by("id"):
            if emp.user_id is None:
                continue
            role_name = emp.user.role.name if emp.user.role_id else "无角色"
            self.stdout.write(
                f"  {role_name}: {emp.user.username} / {models.DEFAULT_PASSWORD}"
                f"  （{emp.name} · {emp.depart.name}）"
            )
