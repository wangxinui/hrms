"""表单定义 - 使用 ModelForm 进行数据校验."""
import re
from django import forms
from . import models
from .scoping import is_super, scope_departments, scope_employees


class ScopedEmployeeMixin:
    """下拉框员工选项按当前用户的数据范围过滤."""

    employee_field = "employee"

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and self.employee_field in self.fields:
            qs = models.Employee.objects.filter(status=1)
            self.fields[self.employee_field].queryset = scope_employees(qs, user)


class DepartmentForm(forms.ModelForm):
    """部门表单."""
    class Meta:
        model = models.Department
        fields = ["name", "code", "parent", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EmployeeForm(forms.ModelForm):
    """员工表单 - 含校验 + 自动开通登录账号."""
    role = forms.ModelChoiceField(
        queryset=models.Role.objects.all(),
        required=False,
        label="账号角色",
        empty_label=None,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = models.Employee
        fields = ["name", "age", "gender", "phone", "email", "account_balance",
                  "hire_date", "depart", "avatar", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": 16, "max": 70}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "11位手机号"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "account_balance": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "hire_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "depart": forms.Select(attrs={"class": "form-control"}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = user
        self.instance_id = self.instance.pk if self.instance.pk else None

        # 部门范围：部门管理员只能在本科室范围内建档
        if user is not None and not is_super(user):
            self.fields["depart"].queryset = scope_departments(
                models.Department.objects.all(), user
            )
            # 角色范围：只有超级管理员能分配部门管理员
            self.fields["role"].queryset = models.Role.objects.filter(code="employee")

        if self.instance.pk and self.instance.user_id:
            self.fields["role"].initial = self.instance.user.role

    def clean_name(self):
        name = self.cleaned_data["name"]
        if len(name) < 2 or len(name) > 20:
            raise forms.ValidationError("姓名长度应在 2-20 个字符之间")
        return name

    def clean_age(self):
        age = self.cleaned_data["age"]
        if not (16 <= age <= 70):
            raise forms.ValidationError("年龄应在 16-70 岁之间")
        return age

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not re.match(r"^1[3-9]\d{9}$", phone):
            raise forms.ValidationError("请输入有效的 11 位手机号")
        # 唯一性校验（排除自身）
        qs = models.Employee.objects.filter(phone=phone)
        if self.instance_id:
            qs = qs.exclude(id=self.instance_id)
        if qs.exists():
            raise forms.ValidationError("该手机号已被使用")
        return phone

    def save(self, commit=True):
        emp = super().save(commit=False)
        role = self.cleaned_data.get("role")
        # 非超级管理员不允许改动账号角色
        if self.current_user is not None and not is_super(self.current_user):
            role = None
        if commit:
            emp.save()
            emp.ensure_account(role=role)
        return emp


class AttendanceForm(ScopedEmployeeMixin, forms.ModelForm):
    """考勤表单."""
    class Meta:
        model = models.Attendance
        fields = ["employee", "date", "clock_in", "clock_out", "remark"]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "clock_in": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "clock_out": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "remark": forms.TextInput(attrs={"class": "form-control"}),
        }


class SalaryForm(ScopedEmployeeMixin, forms.ModelForm):
    """薪资表单."""
    class Meta:
        model = models.Salary
        fields = ["employee", "month", "base_salary", "bonus", "deduction"]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "month": forms.DateInput(attrs={"class": "form-control", "type": "month"}),
            "base_salary": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "bonus": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "deduction": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class AnnouncementForm(forms.ModelForm):
    """公告表单."""
    class Meta:
        model = models.Announcement
        fields = ["title", "content", "is_top"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "is_top": forms.CheckboxInput(attrs={"class": "flat-red"}),
        }


class TaskForm(ScopedEmployeeMixin, forms.ModelForm):
    """任务表单 - AJAX 提交."""
    employee_field = "owner"

    class Meta:
        model = models.Task
        fields = ["level", "title", "detail", "owner", "status"]
        widgets = {
            "level": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "detail": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "owner": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class LoginForm(forms.Form):
    """登录表单."""
    username = forms.CharField(
        max_length=64,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "用户名", "autofocus": True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": "密码",
        }),
    )
    captcha = forms.CharField(
        max_length=4,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "验证码",
        }),
    )


class ChangePasswordForm(forms.Form):
    """个人中心 - 修改密码表单."""

    old_password = forms.CharField(
        label="原密码",
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": "请输入当前密码",
            "autocomplete": "current-password",
        }),
    )
    new_password = forms.CharField(
        label="新密码",
        min_length=6,
        max_length=20,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": "6-20 位，建议字母与数字组合",
            "autocomplete": "new-password",
        }),
    )
    confirm_password = forms.CharField(
        label="确认新密码",
        min_length=6,
        max_length=20,
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": "请再次输入新密码",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old = self.cleaned_data["old_password"]
        if self.user is None or not self.user.check_password(old):
            raise forms.ValidationError("原密码不正确")
        return old

    def clean_new_password(self):
        new = self.cleaned_data["new_password"]
        if not re.search(r"[A-Za-z]", new) or not re.search(r"\d", new):
            raise forms.ValidationError("新密码需同时包含字母和数字")
        return new

    def clean(self):
        cleaned = super().clean()
        old = cleaned.get("old_password")
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")
        if new and confirm and new != confirm:
            self.add_error("confirm_password", "两次输入的新密码不一致")
        if old and new and old == new:
            self.add_error("new_password", "新密码不能与原密码相同")
        return cleaned

