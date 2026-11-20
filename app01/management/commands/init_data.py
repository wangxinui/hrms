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
            "ai_view",
        ],
        "employee": [
            "employee_view", "attendance_view", "salary_view",
            "announcement_view", "task_view", "task_edit",
            "ai_view",
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
            ("使用 AI 助手", "ai_view", "AI"),
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

        # === 10. 制度知识库（供 AI 制度问答检索）===
        knowledge_data = [
            ("考勤与迟到制度", "attendance", "考勤 打卡 迟到 早退 旷工 缺勤",
             "公司标准工作时间为 9:00-18:00，午休 12:00-13:00。"
             "每月迟到 30 分钟以内每次扣款 50 元；迟到超过 30 分钟按半天事假处理。"
             "月累计迟到 3 次以上，取消当月全勤奖。"
             "未打卡且未补卡视为缺勤，无故缺勤 1 天按 3 倍日工资扣款。"),
            ("请假制度", "leave", "请假 年假 事假 病假 调休 流程",
             "年假：入职满 1 年 5 天，满 10 年 10 天，满 20 年 15 天，年假需提前 3 个工作日在系统提交申请。"
             "病假需提供二级以上医院证明，病假期间发放基本工资的 70%。"
             "事假按日工资全额扣除，单次事假不超过 5 天。"),
            ("加班与调休制度", "attendance", "加班 调休 加班费 节假日",
             "加班需提前在系统中提交申请并经部门负责人审批。"
             "工作日加班按 1.5 倍时薪计算，休息日加班按 2 倍计算，法定节假日加班按 3 倍计算。"
             "加班时长可申请调休，调休需在加班之日起 3 个月内使用，逾期作废。"),
            ("差旅报销制度", "salary", "报销 差旅 发票 住宿 交通 贴票",
             "差旅报销需提交发票原件、行程单和出差审批单，缺一不可。"
             "住宿标准：一线城市每晚不超过 500 元，其他城市不超过 350 元；市内交通据实报销。"
             "报销单每月 25 日前提交财务部，财务部在 5 个工作日内完成审核并打款。"),
            ("薪资发放制度", "salary", "薪资 工资 发放 奖金 扣款 实发",
             "公司每月 10 日发放上月工资，遇节假日提前至最近工作日。"
             "薪资构成 = 基本工资 + 绩效奖金 - 各项扣款，实发金额以银行到账为准。"
             "薪资信息属于保密内容，禁止同事之间相互打探或传播。"),
            ("社保与公积金制度", "other", "社保 公积金 五险一金 缴纳 基数",
             "公司为正式员工缴纳五险一金，入职当月开始缴纳。"
             "缴纳基数按员工上年度月平均工资核定，新员工按首月工资核定。"
             "住房公积金企业与个人缴纳比例均为 12%。"),
            ("入职与离职制度", "onboard", "入职 离职 试用期 交接 材料",
             "新员工入职需提交身份证、学历证书、体检报告和银行卡信息，试用期为 3 个月。"
             "试用期考核合格后转为正式员工。"
             "员工离职需提前 30 天提交书面申请，完成工作交接和资产归还后方可办理离职手续。"),
            ("培训与晋升制度", "other", "培训 晋升 考核 调薪 评估",
             "公司每年 4 月和 10 月组织两次晋升评估，由部门负责人提名并述职答辩。"
             "入职满 1 年且绩效连续两次为 A 的员工可申请调薪。"
             "公司为员工提供每年不超过 3000 元的培训补贴，需提前申请并提交培训总结。"),
        ]
        for title, category, keywords, content in knowledge_data:
            models.Knowledge.objects.update_or_create(
                title=title, defaults={
                    "category": category, "keywords": keywords,
                    "content": content, "is_active": True,
                }
            )
        self.stdout.write(f"  创建 {len(knowledge_data)} 条制度知识")

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
