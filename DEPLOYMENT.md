# Money Journey Docker 部署指南

本文档提供使用Docker部署Money Journey应用的详细说明。

## 组件化前端部署（2026-11-21）

Dockerfile 首阶段构建 React 前端，运行阶段只保留 Python 与静态产物，不运行 Node 服务。前端位于 `/opt/money_journey_frontend`，避免开发环境的 `.:/app` 源码挂载遮挡。`/app/` 由 Django 提供入口，`/static/app/` 由 WhiteNoise 发布，`/api/v1/` 为接口，`/admin/` 保持系统维护用途。

默认构建使用官方 `node:22-alpine`。本次验收因该基础层下载缓慢，使用相同项目兼容的官方 Node 20.20.2 构建完成；可复现命令为：

```powershell
docker build --build-arg NODE_BUILD_IMAGE=node:20.20.2-alpine -t money_journey:frontend .
```

常规部署仍可使用 `docker compose -f docker-compose.prod.yml up -d --build`。用户已确认退役旧页面：旧 GET/HEAD 地址跳转到对应 `/app/` 页面并保留筛选参数；旧表单提交返回 410，不执行写入。`FRONTEND_ENABLED` 回退开关已退出，CSV 模板与游客演示由新 API 独立提供。若需部署旧版本，应使用历史提交构建，不能再通过环境开关恢复旧模板。

旧提交仍受 Django CSRF 校验：安全凭证缺失或过期时先返回 403；通过校验后返回 410，均不执行旧业务写入。

生产使用 HTTPS 可信反向代理，转发 Host，并由代理覆盖 `X-Forwarded-Proto: https`；Django 生产配置据此识别安全请求。应用端口应仅对可信代理开放，不能直接信任客户端提供的代理头。`CSRF_TRUSTED_ORIGINS` 填写实际 HTTPS 入口；Secure/HttpOnly Cookie 保持开启，新前端从身份上下文响应读取 CSRF token，不读取 HttpOnly Cookie。

本地独立测试入口保持 `http://127.0.0.1:38000/app/`。实际验证覆盖生产设置与本机自签证书 TLS 代理，但不代替真实域名证书和外部代理环境验收。

本地开发在 `frontend/` 运行 `npm ci` 与 `npm run dev`。默认代理 `http://127.0.0.1:8000`，保留浏览器 Host；若连接 38000 测试容器，可在同一终端设 `$env:MJ_BACKEND_URL='http://127.0.0.1:38000'`。构建使用 `npm run build`，不需要全局安装 Node 包。

测试代码、设置与验收文档统一位于顶层 `tests/`，运行方式见 [测试说明](tests/README.md)。后端回归使用 `--settings=tests.settings` 独立内存数据库或独立 MySQL 测试库，浏览器验收使用隔离账号；测试凭据、TLS 私钥、截图和报告不进入 Git。用户确认后的文件清理记录见 `docs/superpowers/plans/2026-11-21-frontend-deletion-candidates.md`。业务数据和数据库卷保持原样。

## 项目结构更改

本次Docker化部署添加了以下文件：

```
money_journey/
├── Dockerfile                              # Django应用镜像构建
├── docker-compose.yml                      # 开发环境编排
├── docker-compose.prod.yml                 # 生产环境编排
├── .env.example                           # 环境变量模板
├── requirements/
│   └── production.txt                     # 生产环境依赖
├── docker/
│   └── django/
│       └── entrypoint.sh                  # 应用启动脚本
└── money_journey/
    └── settings/
        ├── __init__.py                    # 配置加载器
        ├── base.py                        # 基础配置
        └── production.py                  # 生产环境配置
```

## 配置分离

原有的`settings.py`已被重构为：

1. **base.py** - 基础配置，包含开发默认值，使用环境变量
2. **production.py** - 生产配置，继承base.py，覆盖安全设置
3. **__init__.py** - 根据`DJANGO_SETTINGS_MODULE`环境变量加载相应配置

## 环境变量管理

所有敏感配置已移至环境变量：
- 数据库连接信息
- Django密钥
- 安全设置
- 邮件配置等

使用`.env.example`作为模板，复制为`.env`或`.env.production`并填写实际值。

## 开发环境部署

### 1. 环境准备
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，配置数据库连接等
# 注意：开发环境使用docker-compose.yml中的MySQL容器
```

### 2. 启动开发环境
```bash
# 构建并启动服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 运行数据库迁移
docker-compose exec web python manage.py migrate

# 创建超级用户
docker-compose exec web python manage.py createsuperuser
```

### 3. 访问应用
- 应用地址：http://localhost:8000
- 管理员后台：http://localhost:8000/admin
- 数据库端口：3307（映射到容器内部的3306）

## 生产环境部署

### 1. 服务器要求
- Docker和Docker Compose
- 外部MySQL数据库（版本8.0+）
- 外部反向代理服务（如Nginx，用户提到的"lucky"服务）

### 2. 部署步骤
```bash
# 1. 克隆代码
git clone git@github.com:longfengpili/money_journey.git
cd money_journey

# 2. 配置生产环境变量
cp .env.example .env.production
# 编辑.env.production，设置生产环境变量：
# - DJANGO_SECRET_KEY（生成强密钥）
# - DJANGO_DEBUG=False
# - DJANGO_ALLOWED_HOSTS（你的域名）
# - 外部MySQL数据库连接信息
# - 安全设置（CSRF_COOKIE_SECURE=True等）

# 3. 构建并启动生产环境
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 4. 检查服务状态
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. 配置外部反向代理
应用容器暴露8000端口。配置你的反向代理（如Nginx或"lucky"服务）：
- 代理请求到`http://localhost:38000`
- 配置SSL/TLS证书
- 设置正确的HTTP头（X-Forwarded-For, X-Forwarded-Proto等）

### 4. 健康检查
应用提供健康检查端点：`/health/`
可用于容器健康检查或监控。

### 5. 定时任务配置
应用使用`django-crontab`管理定时任务，配置在`money_journey/settings/base.py`中：
- **到期存款检测**：每天19-21点执行，检测未来7天内到期的存款记录，通过PushPlus发送通知
- **历史记录检查**：`clean_old_records` 仅报告长期未更新的结束状态候选记录，目前未加入定时配置

定时任务在容器启动时自动添加（通过entrypoint.sh）：
```bash
# 添加定时任务
python manage.py crontab add

# 查看当前定时任务
python manage.py crontab show
```

如需手动管理定时任务：
```bash
# 开发环境
docker-compose exec web python manage.py crontab add
docker-compose exec web python manage.py crontab show
docker-compose exec web python manage.py crontab remove

# 生产环境
docker-compose -f docker-compose.prod.yml exec web python manage.py crontab add
```

### 6. 储蓄计算器

`savings_calculator`应用是一个无数据库模型的计算器应用，无需额外的数据库迁移或部署配置。它通过表单输入、计算引擎和Session存储实现完整的储蓄规划功能。

**功能入口**：
- 游客模式：`/savings-calculator/`（无需登录）
- 登录模式：`/savings-calculator/loggedin/`（需登录）

**注意事项**：
- 计算结果存储在Django Session中，Session过期后结果将丢失
- 生产环境建议配置合理的Session过期时间（默认2周）
- 该应用无数据库表，无需执行额外的数据库迁移

## 静态文件处理

生产环境使用Whitenoise中间件服务静态文件：
- 静态文件自动收集到`/app/staticfiles`
- 支持压缩和缓存
- 1年缓存时间

## 数据库迁移

应用启动时自动运行数据库迁移（通过entrypoint.sh）。
如需手动操作：
```bash
# 开发环境
docker-compose exec web python manage.py migrate

# 生产环境
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

## 备份和恢复

### 数据库备份
```bash
# 开发环境
docker-compose exec db mysqldump -u root -p$MYSQL_ROOT_PASSWORD money_journey > backup.sql

# 生产环境（需连接到外部MySQL）
# 使用外部MySQL的备份工具
```

### 恢复数据库
```bash
# 开发环境
docker-compose exec -T db mysql -u root -p$MYSQL_ROOT_PASSWORD money_journey < backup.sql
```

## 监控和维护

### 查看日志
```bash
# 开发环境
docker-compose logs -f --tail=100

# 生产环境
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### 进入容器
```bash
docker-compose exec web bash
```

### 更新应用
```bash
# 拉取最新代码
git pull

# 重建并重启
docker-compose up -d --build
```

## 故障排除

### 1. 构建失败
- 检查Dockerfile语法
- 确保网络可访问Docker Hub
- 验证requirements文件格式

### 2. 数据库连接失败
- 检查环境变量配置
- 验证网络连通性
- 确认MySQL用户权限

### 3. 静态文件404
- 检查collectstatic是否运行
- 验证Whitenoise配置
- 确认文件权限

### 4. 应用无法启动
- 检查日志：`docker-compose logs web`
- 验证环境变量
- 检查端口冲突：
  - MySQL端口冲突：如果本地已有MySQL运行在3306端口，Docker容器会启动失败
  - 解决方案1：停止本地MySQL服务
  - 解决方案2：修改`docker-compose.yml`中的端口映射（如改为`3307:3306`）
  - 应用端口冲突：如果8000端口被占用，修改web服务的端口映射

## 安全建议

1. **生产环境务必**：
   - 设置`DJANGO_DEBUG=False`
   - 使用强`DJANGO_SECRET_KEY`
   - 配置正确的`ALLOWED_HOSTS`
   - 启用HTTPS

2. **定期更新**：
   - 更新Docker基础镜像
   - 更新Python依赖
   - 应用安全补丁

3. **监控**：
   - 设置日志监控
   - 监控容器资源使用
   - 设置告警

## 扩展和定制

### 添加Nginx容器
如需在Docker内部处理SSL和静态文件，可添加Nginx容器：
1. 创建`docker/nginx/Dockerfile`和`nginx.conf`
2. 更新`docker-compose.prod.yml`

### 使用云数据库
如需使用云数据库（如RDS）：
1. 更新环境变量中的数据库连接信息
2. 配置VPC网络和安全组

### 多实例部署
如需水平扩展：
1. 增加Gunicorn workers数量
2. 使用负载均衡器
3. 配置共享会话存储

## 联系和支持

如有问题，请参考：
1. Docker文档：https://docs.docker.com/
2. Django部署指南：https://docs.djangoproject.com/en/stable/howto/deployment/
3. 项目README.md

---

**最后更新**：2026-04-04（添加储蓄计算器部署说明）
**版本**：1.0.0
