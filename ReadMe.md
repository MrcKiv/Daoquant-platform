# Daoquant Platform

Daoquant Platform 是一个以 Docker 部署为主的量化策略回测平台仓库，当前保留的是可运行主链路，已清理未接入页面的旧组件、备份文件和历史调试脚本。

默认部署链路：

- `frontend`：Vite 构建后由 `nginx` 提供静态页面和反向代理
- `backend`：Django + Gunicorn
- `db`：MySQL 8.4

自动交易模块默认关闭，不影响主站、策略管理和回测功能。

## 推荐阅读顺序

- 局域网或服务器部署：[`DOCKER_DEPLOY.md`](DOCKER_DEPLOY.md)
- 本地开发启动：[`QUICK_START.md`](QUICK_START.md)
- `xtquant` 补数脚本部署：[`XTQUANT_BACKFILL_DEPLOY.md`](XTQUANT_BACKFILL_DEPLOY.md)

## 当前仓库结构

```text
backend_main/   Django 后端
frontend/       Vue 3 + Vite 前端
docker/         Dockerfile、nginx 与 MySQL 初始化目录
docker-compose.yml
docker-compose.offline.yml
```

## 最短部署方式

前提：

- 已安装 Docker Desktop 或 Docker Engine + Docker Compose
- 已准备好数据库 SQL，或接受先启动一个空库再执行迁移

如果你已有业务数据：

1. 把 `.sql` 或 `.sql.gz` 放到 `docker/mysql/init/`
2. 在仓库根目录执行：

```bash
docker compose up -d --build
```

如果你暂时没有 SQL，也可以直接启动，系统会按当前 Django migrations 初始化空库：

```bash
docker compose up -d --build
```

启动成功后默认访问地址：

- 首页：`http://localhost:8080`
- 健康检查：`http://localhost:8080/api/health/`
- Django Admin：`http://localhost:8080/admin/`

## 常用环境变量

仓库已提供 [`.env.example`](.env.example)。不复制 `.env` 也能启动，但在局域网部署时建议按需覆盖：

- `FRONTEND_PORT`
- `MYSQL_PORT`
- `MYSQL_INNODB_REDO_LOG_CAPACITY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`

## 常用命令

启动：

```bash
docker compose up -d --build
```

查看服务状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

删除数据库卷后重建：

```bash
docker compose down -v
docker compose up -d --build
```

## 局域网访问

服务启动后，局域网其他电脑可通过以下地址访问：

```text
http://部署机IP:8080
```

Windows 部署时，请确认系统防火墙已放行 `8080` 端口。更完整的局域网部署说明见 [`DOCKER_DEPLOY.md`](DOCKER_DEPLOY.md)。
