"""数据范围控制 - 三级角色可见的数据边界.

超级管理员：全公司数据
部门管理员：本部门及其下级部门数据
普通员工：仅本人数据
"""
from . import models

ROLE_SUPER = "super_admin"
ROLE_DEPT = "dept_admin"
ROLE_EMP = "employee"


def role_code(user):
    """返回当前用户的角色编码，未登录返回空串."""
    if not user or not user.is_authenticated:
        return ""
    if user.is_superuser:
        return ROLE_SUPER
    return user.role.code if user.role_id else ""


def is_super(user):
    return role_code(user) == ROLE_SUPER


def is_dept_admin(user):
    return role_code(user) == ROLE_DEPT


def is_employee(user):
    return role_code(user) == ROLE_EMP


def my_employee(user):
    """当前登录账号关联的员工档案."""
    if not user or not user.is_authenticated:
        return None
    return models.Employee.objects.filter(user=user).select_related("depart").first()


def my_dept(user):
    """当前登录账号所属部门（部门管理员与普通员工使用）."""
    emp = my_employee(user)
    return emp.depart if emp else None


def dept_family_ids(dept):
    """返回本部门及其所有下级部门的 ID 列表."""
    if not dept:
        return []
    rows = list(models.Department.objects.values_list("id", "parent_id"))
    result = {dept.id}
    changed = True
    while changed:
        changed = False
        for did, pid in rows:
            if pid in result and did not in result:
                result.add(did)
                changed = True
    return list(result)


def scope_employees(qs, user):
    """按角色过滤员工查询集."""
    if is_super(user):
        return qs
    if is_dept_admin(user):
        ids = dept_family_ids(my_dept(user))
        return qs.filter(depart_id__in=ids) if ids else qs.none()
    emp = my_employee(user)
    return qs.filter(pk=emp.pk) if emp else qs.none()


def scope_by_employee(qs, user, field="employee"):
    """按员工范围过滤考勤/薪资/任务等记录."""
    if is_super(user):
        return qs
    if is_dept_admin(user):
        ids = dept_family_ids(my_dept(user))
        return qs.filter(**{f"{field}__depart_id__in": ids}) if ids else qs.none()
    emp = my_employee(user)
    return qs.filter(**{field: emp}) if emp else qs.none()


def scope_departments(qs, user):
    """按角色过滤部门查询集."""
    if is_super(user):
        return qs
    if is_dept_admin(user):
        ids = dept_family_ids(my_dept(user))
        return qs.filter(id__in=ids) if ids else qs.none()
    return qs.none()


def can_access_employee(user, emp):
    """判断当前用户是否可以访问指定员工档案."""
    if is_super(user):
        return True
    if is_dept_admin(user):
        return emp.depart_id in dept_family_ids(my_dept(user))
    me = my_employee(user)
    return bool(me and me.pk == emp.pk)
