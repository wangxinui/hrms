# HRMS · 企业员工管理系统

基于 Django 5.2 的企业人事管理系统，覆盖「组织架构 → 员工档案 → 考勤 → 薪资 → 公告 → 任务」全流程，并内置基于大模型（Qwen2.5-7B）的智能助手：**制度问答（RAG）**、**JD 生成**、**数据智能点评**、**多轮对话**。

- 权限体系：自建 RBAC（`User` + `Role` + `Permission` 三层），26 条权限码 / 3 类角色
- 数据范围：超管全量、部门管理员本部门树、普通员工仅本人（`scoping.py` 统一实现）
- 界面：AdminLTE 3 + Bootstrap 4 + DataTables，列表页统一搜索 / 筛选 / 分页
- 交互：表单增删改复用 `CrudMixin`，任务模块与全部 AI 接口走 AJAX / SSE
- 测试：34 个单元测试，跑测试自动切 SQLite 内存库，不依赖 MySQL

---

## 1. 技术栈与运行环境

| 项 | 版本 / 说明 |
|---|---|
| Python | 3.12.7（项目内 `venv`） |
| Django | 5.2 |
| 数据库 | MySQL 8（库名 `hrms`，`utf8mb4`）；测试时自动用 SQLite 内存库 |
| 依赖 | `Django==5.2`、`mysqlclient>=2.2`、`Pillow>=10.0`（见 `requirements.txt`） |
| 前端 | AdminLTE 3、Bootstrap 4、jQuery、DataTables、ECharts 5 |
| 大模型 | 硅基流动 OpenAI 兼容接口，默认 `Qwen/Qwen2.5-7B-Instruct` |
| 时区 / 语言 | `Asia/Shanghai` / `zh-hans`，`USE_TZ = False` |

---

## 2. 快速开始

```bash
# 1) 建库（MySQL）
mysql -u root -p -e "CREATE DATABASE hrms CHARACTER SET utf8mb4;"

# 2) 准备虚拟环境（仓库已自带 venv，可跳过）
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3) 配置环境变量（项目根新建 .env，已被 .gitignore 忽略）
#    SECRET_KEY=...
#    DEBUG=True
#    LLM_API_KEY=sk-xxx
#    LLM_BASE_URL=https://api.siliconflow.cn/v1
#    LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
#    LLM_TIMEOUT=60

# 4) 建表
python manage.py migrate

# 5) 灌演示数据（部门 / 员工 / 考勤 / 薪资 / 公告 / 任务 / 制度，可重复执行）
python manage.py init_data

# 6) 启动
python manage.py runserver
```

访问 <http://127.0.0.1:8000/>，未登录会跳转 `/login/`。

> 数据库连接写在 `hrms/settings.py` 的 `DATABASES`（默认 `root/root123@localhost:3306/hrms`），换机器请改这里。

### 演示账号

| 账号 | 角色 | 说明 |
|---|---|---|
| `admin` / `admin123` | 超级管理员 | 全部 26 条权限 |
| `13810000002` | 部门管理员（王五 · 技术部） | 17 条权限，只看技术部树 |
| `13810000001` | 普通员工（李四 · 研发二组） | 7 条权限，只看自己 |

其余 `13810000003` ~ `13810000011` 等账号由 `init_data` 自动生成，**默认密码 `123456`**（`models.DEFAULT_PASSWORD`）。

---

## 3. 目录结构

```
hrms/
├─ manage.py                  Django 管理入口
├─ requirements.txt           依赖清单
├─ .env                       环境变量（不入库）
├─ hrms/                      项目配置包
│  ├─ settings.py             配置：数据库 / DEBUG / 安全头 / Cookie / 日志 / LLM
│  ├─ urls.py                 根路由（include app01.urls）
│  ├─ wsgi.py / asgi.py       部署入口
└─ app01/                     唯一业务应用
   ├─ models.py               10 个模型（含 Knowledge）
   ├─ urls.py                 45 条路由
   ├─ forms.py                6 类表单 + ScopedEmployeeMixin
   ├─ decorators.py           @perm_required 权限装饰器
   ├─ scoping.py              数据范围：scope_employees / scope_by_employee / can_access_employee / my_employee
   ├─ context_processors.py   导航菜单注入（按权限动态生成）
   ├─ middleware/auth.py      登录态中间件
   ├─ dashboard.py            首页概览
   ├─ *_views.py              各模块视图（部门 / 员工 / 考勤 / 薪资 / 公告 / 任务 / 统计 / AI）
   ├─ views/mixins.py         CrudMixin：base_add / base_edit / base_delete
   ├─ utils/
   │  ├─ ai.py                LLMClient + 各场景提示词
   │  ├─ rag.py               制度检索 search_knowledge（关键词召回 + 加权排序）
   │  ├─ pagination.py        列表分页
   │  └─ captcha.py           登录验证码（Pillow 生成，存 session）
   ├─ templatetags/perm_tags.py  模板里判权限的 {% has_perm %}
   ├─ management/commands/init_data.py  一次性灌演示数据
   ├─ migrations/             0001_initial / 0002_knowledge
   ├─ templates/app01/        24 个 HTML 模板（含片段）
   └─ static/
      ├─ adminlte/            AdminLTE 第三方模板资源
      └─ app01/css/           hrms-theme.css / hrms-login.css / ai.css（自写样式）
```

---

## 4. 文件清单（逐个作用）

### 4.1 配置与入口

| 文件 | 作用 |
|---|---|
| `manage.py` | Django 命令行入口（`migrate` / `runserver` / `test` / 自定义命令） |
| `hrms/settings.py` | 全局配置。关键项：`AUTH_USER_MODEL = "app01.User"`（自定义用户表）、MySQL 连接、`DEBUG` 走环境变量、安全响应头（HSTS / nosniff / Referrer）、Cookie（HttpOnly + SameSite）、`LLM_*` 五项、分级日志（控制台 + `logs/info.log`、`logs/error.log`、`logs/security.log` 三路轮转） |
| `hrms/urls.py` | 根路由，`include("app01.urls")` |
| `hrms/wsgi.py`、`asgi.py` | 部署入口（同步 / 异步） |
| `requirements.txt` | 三项依赖，装完即可跑 |

### 4.2 数据层

| 文件 | 作用 |
|---|---|
| `app01/models.py` | **全部 10 个模型**：`User`(继承 AbstractUser)、`Role`、`Permission`、`Department`(parent 自关联 SET_NULL，被 Employee 以 PROTECT 引用)、`Employee`(含 `ensure_account()` 自动开通账号)、`Attendance`(一人一天唯一)、`Salary`(`save()` 自动算实发)、`Announcement`(置顶)、`Task`、`Knowledge`(制度库) |
| `app01/migrations/0001_initial.py` | 初始建表（9 张业务表） |
| `app01/migrations/0002_knowledge.py` | 追加制度表 `Knowledge` |

### 4.3 视图层（每个模块一个文件）

| 文件 | 主要函数 | 作用 |
|---|---|---|
| `dashboard.py` | `dashboard` | 首页：人数、部门数、待办、最近公告等概览卡片 |
| `department_views.py` | `dept_list/add/edit/delete` | 部门 CRUD；删除时若挂有员工会 `ProtectedError` 拦下 |
| `employee_views.py` | `emp_list/add/edit/delete/detail/detail_fragment/reset_password` | 员工 CRUD + 详情（AJAX 片段）+ 重置密码；列表带搜索 / 状态筛选 / 分页，用 `select_related` 消除 N+1 |
| `attendance_views.py` | `att_list/add/edit/delete` | 考勤 CRUD；`calc_status()` 按打卡时间自动判定迟到/早退/缺勤 |
| `salary_views.py` | `sal_list/add/edit/delete` | 薪资 CRUD + 按月份筛选 + `Sum` 汇总；实发由模型 `save()` 算 |
| `announcement_views.py` | `ann_list/add/edit/delete/toggle_top` | 公告 CRUD + 置顶开关；`auto_now_add` 记录发布时间 |
| `task_views.py` | `task_list/add_page/edit/delete/ajax` | 任务管理；表单校验走 AJAX（失败不刷新、不丢输入） |
| `stats_views.py` | `stats_page`、`api_dept_distribution`、`api_salary_trend`、`api_attendance_overview` | 统计页 + 3 个 JSON 接口（后端 ORM 聚合，前端 ECharts 画图） |
| `auth_views.py` | `login_view/logout_view/captcha_view/password_change` | 登录（验证码校验）、登出、验证码图片、改密码（`set_password` 哈希） |
| `ai_views.py` | `ai_page`、`api_jd`、`api_ask`、`api_comment`、`api_employee_comment`、`api_chat_stream`、`api_chat_clear` | AI 助手全部入口；含 `_employee_notes()` 分层披露、SSE 流式输出、历史存 session |
| `views/mixins.py` | `CrudMixin.base_add/base_edit/base_delete` | 通用增删改模板方法：取表单 → 校验 → 保存 → 消息 → 跳转，部门/公告/考勤/薪资 4 模块复用 |

### 4.4 支撑组件

| 文件 | 作用 |
|---|---|
| `app01/decorators.py` | `@perm_required("code")`：无权限直接 403；全站 33 处使用 |
| `app01/scoping.py` | 数据范围唯一出口：`role_code`、`scope_employees`、`scope_by_employee`、`can_access_employee`、`my_employee`；全站 19 处调用，跨 6 个模块 |
| `app01/middleware/auth.py` | `AuthMiddleware`：未登录访问业务页 → 302 登录页（白名单放行 login/captcha/static） |
| `app01/context_processors.py` | `nav_processor`：按当前用户权限算菜单，模板里 `nav_items` 直接渲染 |
| `app01/templatetags/perm_tags.py` | `{% has_perm "code" %}`：模板级别判权限（按钮显隐） |
| `app01/forms.py` | `DepartmentForm`、`EmployeeForm`、`AttendanceForm`、`SalaryForm`、`AnnouncementForm`、`TaskForm`；`ScopedEmployeeMixin` 让考勤/薪资/任务的下拉框只出现权限内员工 |
| `app01/utils/ai.py` | `LLMClient`（chat / stream / 超时 / 错误包装）、`check_input`、各场景提示词：`CHAT_SYSTEM`、`KB_SYSTEM`、`JD_SYSTEM`、`COMMENT_SYSTEM`，及 `build_chat_system`、`build_kb_prompt` 等 |
| `app01/utils/rag.py` | `search_knowledge(question, limit=3)`：中文 2–3 字切片 + `icontains` 召回 + 标题×3/正文×1 打分排序；含停用词表 |
| `app01/utils/pagination.py` | `paginate()`：统一分页（6 个列表页各 1 处） |
| `app01/utils/captcha.py` | 生成 4 位验证码图片（Pillow），答案写 session，登录时比对 |
| `app01/management/commands/init_data.py` | `python manage.py init_data`：生成演示数据（部门 / 员工 / 考勤 / 薪资 / 公告 / 任务 / 制度），并按角色为员工开通账号 |
| `app01/admin.py` | **目前是空壳**（未注册任何模型，后台 `/admin/` 无内容） |
| `app01/apps.py` | App 配置（仅 `verbose_name`） |
| `app01/tests.py` | **34 个用例**：模型约束、权限、数据范围、CRUD、AJAX、检索、AI 接口（mock）等 |

### 4.5 模板与静态资源

| 位置 | 作用 |
|---|---|
| `templates/app01/base.html` | 全站骨架：AdminLTE 布局、导航、消息条、DataTables 三件套、`{% block %}` 扩展点 |
| `templates/app01/login.html`、`password_change.html` | 登录页（验证码）、改密页 |
| `templates/app01/dashboard.html` | 首页概览 |
| `templates/app01/department/list.html`、`form.html` | 部门列表 / 新增编辑 |
| `templates/app01/employee/list.html`、`form.html`、`detail.html`、`_detail_body.html`、`_employee_edit_form.html` | 员工列表、表单、详情抽屉（片段复用） |
| `templates/app01/attendance/list.html`、`form.html` | 考勤列表 / 表单 |
| `templates/app01/salary/list.html`、`form.html` | 薪资列表 / 表单 |
| `templates/app01/announcement/list.html`、`form.html` | 公告列表 / 表单 |
| `templates/app01/task/list.html`、`form.html` | 任务列表 / AJAX 表单 |
| `templates/app01/stats/index.html` | 可视化页（ECharts） |
| `templates/app01/ai/index.html`、`ai/_comment_modal.html` | AI 助手页（4 个面板 + 对话流）、点评弹窗 |
| `templates/app01/confirm_delete.html` | 通用删除确认页 |
| `templates/app01/partials/_kpi_cards.html` | KPI 卡片片段（6 个列表页 include） |
| `static/adminlte/` | AdminLTE 3 完整资源（第三方，勿改） |
| `static/app01/css/hrms-theme.css` | 自写主题：配色、卡片、表格、徽章 |
| `static/app01/css/hrms-login.css` | 登录页样式 |
| `static/app01/css/ai.css` | AI 助手页样式（对话气泡、流式光标、面板） |

---

## 5. 数据模型关系

```
Role ──M2M── Permission                （角色↔权限，必须第三张表）
  │
User ──FK(role)── Role                 （登录账号，角色删除时置空）
  │
  └──1:1── Employee (user, SET_NULL)    （账号 ↔ 档案，可为空）
              │
Department ──FK(parent, 自关联, SET_NULL)── Department   （树形组织；被 Employee 以 PROTECT 引用）
              │
              └──FK(depart, PROTECT)── Employee
                                 ├──FK(employee, CASCADE)── Attendance  (unique: employee+date)
                                 ├──FK(employee, CASCADE)── Salary      (save() 算 total)
                                 └──FK(employee, CASCADE)── Task

Announcement ──FK(author, SET_NULL)── User   （发布人，账号删除时只丢署名）
Knowledge                                    （独立表，无外键，供 AI 检索）
```

删除策略一句话：**部门受保护（有员工就不许删）、三本账连坐（员工删了考勤/薪资/任务跟着走）、角色与作者只丢关联（SET_NULL），部门的上级指针也只置空不删子部门**。

---

## 6. 权限体系（26 条权限 / 3 类角色）

| 角色 | 权限数 | 典型权限 |
|---|---|---|
| `super_admin` 超级管理员 | 26 | 全部 |
| `dept_admin` 部门管理员 | 17 | `employee_*`、`attendance_*`、`salary_*`、`task_*`、`ai_view`… |
| `employee` 普通员工 | 7 | `employee_view`、`attendance_view`、`salary_view`、`announcement_view`、`task_view`、`task_edit`、`ai_view` |

三层防护：

1. **中间件** `AuthMiddleware` → 未登录 302；
2. **装饰器** `@perm_required` → 无权限 403（全站 33 处）；
3. **模板** `{% has_perm %}` + `nav_processor` → 没权限的菜单/按钮不生成。

第四层是**数据范围**：有权限 ≠ 能看全部，`scoping.py` 再按「超管 / 本部门树 / 本人」收窄查询集。

---

## 7. AI 智能助手（4 个入口）

| 入口 | 路由 | 实现要点 |
|---|---|---|
| **制度问答（RAG）** | `POST /ai/api/ask/` | `search_knowledge()` 召回 3 条 → 拼进 `build_kb_prompt` → 返回 `answer + sources`；**检索不到就不调模型**，直接回“不知道” |
| **JD 生成** | `POST /ai/api/jd/` | 输入岗位/技能，输出岗位职责与要求 |
| **数据智能点评** | `POST /ai/api/comment/`、`/ai/api/employee/<pk>/comment/` | 后端聚合该员工考勤/薪资/任务 → 交给模型写评语与建议 |
| **多轮对话** | `POST /ai/api/chat/stream/`（SSE） | 每轮先检索制度 + 提取员工档案，再流式输出；历史存 session，保留 5 轮；`temperature=0.3` |

**分层披露（对话里问某位员工时）**

| 字段 | 超管 | 部门管理员 | 普通员工 |
|---|---|---|---|
| 姓名 / 部门 / 状态 / 入职 | ✅ | ✅ 本部门树 | ✅ 仅本人 |
| 薪资（最近一月实发） | ✅ | ✅ 本部门树 | ✅ 仅本人 |
| 考勤（按时/迟到/早退/缺勤计数） | ✅ | ✅ 本部门树 | ✅ 仅本人 |
| 手机号 | ✅ | ❌ | ✅ 仅本人 |
| 全公司名单 | 永不注入模型（一次最多 2 人） | ❌ | ❌ |

判定 = **权限码**（`salary_view` / `attendance_view`）+ **数据范围**（`can_access_employee`）双闸门；提示词只允许复述“档案里已列出”的字段。

---

## 8. 测试

```bash
python manage.py test app01 -v 2
```

- 34 个用例，覆盖：模型约束（手机号唯一、考勤唯一、实发计算）、RBAC、数据范围、CRUD、AJAX、检索命中/未命中、AI 接口（`LLMClient` 被 mock，不产生真实调用与费用）
- `settings.py` 检测到 `test` 参数会自动切换到 **SQLite 内存库**，不污染 MySQL 数据

---

## 9. 常用命令

| 命令 | 用途 |
|---|---|
| `python manage.py runserver` | 本地启动 |
| `python manage.py migrate` | 建表 / 应用迁移 |
| `python manage.py makemigrations app01` | 改模型后生成迁移 |
| `python manage.py init_data` | 灌演示数据（可重复执行，`update_or_create` 按标题/编号覆盖） |
| `python manage.py test app01` | 跑测试 |
| `python manage.py check` | 配置与模型自检 |
| `python manage.py collectstatic` | `DEBUG=False` 前收集静态文件（输出到 `staticfiles/`） |

---

## 10. 已知问题与待办

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | 制度库有 **4 组重复条目**（考勤 2 条、请假 2 条、入离职 3 条、报销 2 条），其中 6 条是旧版 seed 遗留、代码里已不存在 | 同一问题可能检索到两套口径（如“迟到扣 20 元”与“扣 50 元”），答案不稳定 | 合并去重后重新 seed，见 `init_data.py:238` |
| 2 | `LLM_TIMEOUT` 默认 **30 秒** | 注入 3 条制度后生成约 16–20 秒，网络抖动即超时，页面显示“连接超时” | `.env` 里设 `LLM_TIMEOUT=60` |
| 3 | `admin.py` 未注册模型 | `/admin/` 无法维护制度等数据 | 需要后台编辑时注册 `Knowledge` |
| 4 | `DEBUG` 默认 True | 生产环境会暴露报错细节 | 部署时 `.env` 设 `DEBUG=False` + `collectstatic` |
| 5 | `Attendance.status` 依赖视图计算，模型层无 `save()` 兜底 | 绕过视图写数据可能状态不准 | 可把状态计算下移到模型 `save()` |

---

## 11. 安全说明

- 密码：`set_password()` 走 PBKDF2-SHA256 哈希，库中形如 `pbkdf2_sha256$...`
- 登录：图形验证码答案存 session，一次性校验（登录成功后立刻清除）；账号或密码错误统一提示“用户名或密码错误”
- CSRF：全站启用 `CsrfViewMiddleware`，AJAX 请求携带 `X-CSRFToken`
- Cookie：`HttpOnly` + `SameSite=Lax`，Session 24 小时滚动过期
- 响应头：HSTS、`X-Content-Type-Options: nosniff`、`Referrer-Policy: same-origin`、`X-Frame-Options: SAMEORIGIN`
- 密钥：`SECRET_KEY`、数据库密码、`LLM_API_KEY` 一律走 `.env`（已加入 `.gitignore`），代码中不含明文
- 日志：分级 INFO/WARNING/ERROR，分三路文件轮转——`info.log`（5MB × 3）、`error.log`（5MB × 3）、`security.log`（3MB × 2，接 `django.security`）；**不记录完整 prompt 与用户隐私内容**（只记 `prompt_len`）
