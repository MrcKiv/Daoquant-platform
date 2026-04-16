# Daoquant Platform

这是一个已经整理成可直接 Docker 部署的版本库。

如果你要把项目部署到另一台电脑，并提供给局域网中的其他电脑使用，请优先查看 [DOCKER_DEPLOY.md](/D:/Daoquant-platform/DOCKER_DEPLOY.md)。

默认部署链路：

- `frontend`: Vite 打包后由 `nginx` 提供静态页面和反向代理
- `backend`: Django + Gunicorn
- `db`: MySQL 8.4

自动交易模块在默认 Docker 部署中关闭，不影响主站功能。

## 直接部署

前提：

- 已安装 Docker Desktop 或 Docker Engine + Docker Compose
- 你已经准备好项目依赖的 MySQL SQL 文件

首次部署只需要两步：

1. 把数据库 SQL 放到 `docker/mysql/init/` 目录，或者稍后手动导入到 MySQL 容器。
2. 在仓库根目录执行：

```bash
docker compose up -d --build
```

启动成功后默认可访问：

- 前端：`http://localhost:8080`
- 健康检查：`http://localhost:8080/api/health/`
- Django Admin：`http://localhost:8080/admin/`

## 局域网访问

当前配置已经监听宿主机端口，局域网其他主机可直接访问：

```text
http://你的宿主机IP:8080
```

如果你在 Windows 上部署，还需要确认系统防火墙已放行 `8080` 端口。

## 数据库导入

有两种方式：

### 方式 1：首次启动前放入初始化目录

把 `.sql` 或 `.sql.gz` 文件放到 `docker/mysql/init/`，然后执行：

```bash
docker compose up -d --build
```

注意：这个目录下的初始化脚本只会在 `mysql_data` 卷为空时执行一次。
默认配置已经放宽了数据库健康检查，并把 `MYSQL_INNODB_REDO_LOG_CAPACITY` 提高到 `1G`，更适合首次导入较大的 SQL。

### 方式 2：容器启动后手动导入

默认 MySQL 已映射到宿主机 `3306` 端口，可直接导入：

```bash
mysql -h 127.0.0.1 -P 3306 -u daoquant -p jdgp < your_dump.sql
```

默认账号：

- 用户名：`daoquant`
- 密码：`daoquant123`
- Root 密码：`root123456`

如果端口被占用，可在启动前通过环境变量覆盖，例如：

```bash
$env:MYSQL_PORT=3307
docker compose up -d --build
```

## 可选覆盖配置

仓库已经内置默认值，不复制 `.env` 也能启动。

如果你想自定义端口、密码或域名校验，可以复制 `.env.example` 为 `.env` 后再启动。常用项：

- `FRONTEND_PORT`
- `MYSQL_PORT`
- `MYSQL_INNODB_REDO_LOG_CAPACITY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`

## 常用命令

启动：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

清空数据库卷后重建：

```bash
docker compose down -v
docker compose up -d --build
```
