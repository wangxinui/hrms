"""HRMS 数据模型 - 自定义 User + RBAC + 业务模型."""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

# 员工账号初始密码
DEFAULT_PASSWORD = "123456"


class User(AbstractUser):
    """自定义用户模型，继承 AbstractUser."""
    phone = models.CharField(max_length=11, blank=True, verbose_name="手机号")
    avatar = models.ImageField(upload_to="avatars/", blank=True, verbose_name="头像")
    role = models.ForeignKey(
        "Role", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="角色"
    )

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name


class Role(models.Model):
    """角色模型."""
    name = models.CharField(max_length=64, unique=True, verbose_name="角色名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="角色编码")
    description = models.CharField(max_length=255, blank=True, verbose_name="描述")
    permissions = models.ManyToManyField("Permission", blank=True, verbose_name="权限")

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Permission(models.Model):
    """权限模型."""
    name = models.CharField(max_length=64, verbose_name="权限名称")
    code = models.CharField(max_length=128, unique=True, verbose_name="权限编码")
    description = models.CharField(max_length=255, blank=True, verbose_name="描述")
    group = models.CharField(max_length=32, blank=True, verbose_name="权限分组")

    class Meta:
        verbose_name = "权限"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.group}-{self.name}"


class Department(models.Model):
    """部门模型."""
    name = models.CharField(max_length=64, verbose_name="部门名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="部门编码")
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="上级部门"
    )
    description = models.CharField(max_length=255, blank=True, verbose_name="描述")
    manager = models.ForeignKey(
        "Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_dept", verbose_name="部门负责人"
    )

    class Meta:
        verbose_name = "部门"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Employee(models.Model):
    """员工档案模型."""
    GENDER_CHOICES = ((1, "男"), (2, "女"))
    STATUS_CHOICES = (
        (1, "在职"), (2, "离职"), (3, "试用期"),
    )

    name = models.CharField(max_length=32, verbose_name="姓名")
    age = models.IntegerField(verbose_name="年龄")
    gender = models.IntegerField(choices=GENDER_CHOICES, default=1, verbose_name="性别")
    phone = models.CharField(max_length=11, unique=True, verbose_name="手机号")
    email = models.EmailField(blank=True, verbose_name="邮箱")
    account_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="账户余额"
    )
    hire_date = models.DateField(verbose_name="入职时间")
    depart = models.ForeignKey(
        Department, on_delete=models.PROTECT, verbose_name="所属部门"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, verbose_name="头像")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="关联用户"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "员工"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def ensure_account(self, role=None):
        """为员工创建/同步登录账号.

        用户名 = 手机号，初始密码 123456；role 为空时默认分配普通员工角色。
        已存在账号时只同步手机号与角色，不重置密码。
        """
        user = self.user
        if user is None:
            if role is None:
                role = Role.objects.filter(code="employee").first()
            username = self.phone
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{self.phone}_{suffix}"
            user = User(username=username, phone=self.phone, role=role)
            user.set_password(DEFAULT_PASSWORD)
            user.save()
            self.user = user
            Employee.objects.filter(pk=self.pk).update(user=user)
            return user

        fields = []
        if user.phone != self.phone:
            user.phone = self.phone
            fields.append("phone")
        if role is not None and user.role_id != role.id:
            user.role = role
            fields.append("role")
        if fields:
            user.save(update_fields=fields)
        return user


class Attendance(models.Model):
    """考勤模型 - 自动计算状态."""
    STATUS_CHOICES = (
        ("normal", "按时"),
        ("late", "迟到"),
        ("early", "早退"),
        ("absent", "缺勤"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="员工")
    date = models.DateField(verbose_name="日期")
    clock_in = models.TimeField(null=True, blank=True, verbose_name="上班时间")
    clock_out = models.TimeField(null=True, blank=True, verbose_name="下班时间")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="normal", verbose_name="状态")
    remark = models.CharField(max_length=255, blank=True, verbose_name="备注")

    class Meta:
        verbose_name = "考勤"
        verbose_name_plural = verbose_name
        unique_together = ("employee", "date")
        #一人一天一条
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name} - {self.date}"


class Salary(models.Model):
    """薪资模型 - 实发自动计算."""
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name="员工"
    )
    month = models.DateField(verbose_name="月份")  # 用月初日期代表该月
    base_salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="基本工资"
    )
    bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="奖金"
    )
    deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="扣款"
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="实发"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "薪资"
        verbose_name_plural = verbose_name
        unique_together = ("employee", "month")
        ordering = ["-month"]

    def save(self, *args, **kwargs):
        """实发 = 基本工资 + 奖金 - 扣款."""
        self.total = self.base_salary + self.bonus - self.deduction
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.month.strftime('%Y-%m')}"


class Announcement(models.Model):
    """公告模型."""
    title = models.CharField(max_length=128, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name="发布人"
    )
    #账号删除公告保留
    is_top = models.BooleanField(default=False, verbose_name="是否置顶")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = verbose_name
        ordering = ["-is_top", "-created_at"]
        #置顶优先，再按发布时间倒序
    def __str__(self):
        return self.title


class Task(models.Model):
    """任务模型 - AJAX 异步提交练习."""
    LEVEL_CHOICES = (
        (1, "紧急"), (2, "高"), (3, "中"), (4, "低"),
    )
    STATUS_CHOICES = (
        ("todo", "待处理"), ("doing", "进行中"), ("done", "已完成"),
    )

    level = models.IntegerField(choices=LEVEL_CHOICES, default=3, verbose_name="级别")
    title = models.CharField(max_length=128, verbose_name="标题")
    detail = models.TextField(verbose_name="详情")
    owner = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name="负责人"
    )
    #连带任务一起删除
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="todo", verbose_name="状态"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "任务"
        verbose_name_plural = verbose_name
        ordering = ["-level", "-created_at"]

    def __str__(self):
        return self.title
