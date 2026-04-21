# Docker 部署与局域网访问指南

本文档面向这类部署场景：

- 一台电脑作为部署机长期运行服务
- 局域网内其他电脑只通过浏览器访问
- 使用 Docker 统一启动前端、后端和 MySQL

默认部署链路：

- `frontend`：Vite 构建产物由 `nginx` 提供页面和反向代理
- `backend`：Django + Gunicorn
- `db`：MySQL 8.4

自动交易模块默认关闭，不影响主站、策略管理和回测功能。

如果你还需要 `xtquant` 付费接口补全股票数据，请另外阅读 [`XTQUANT_BACKFILL_DEPLOY.md`](XTQUANT_BACKFILL_DEPLOY.md)。

## 1. 部署前准备

部署机至少需要：

- `Git`
- `Docker Desktop`

Linux 机器可替换为：

- `Docker Engine`
- `Docker Compose`

建议部署机满足以下条件：

- 长时间开机
- 与使用电脑处于同一局域网
- 局域网 IP 稳定

## 2. 获取代码

在部署机终端执行：

```powershell
git clone https://github.com/MrcKiv/Daoquant-platform.git
cd Daoquant-platform
```

## 3. 创建部署配置

建议基于仓库内的 [`.env.example`](.env.example) 新建 `.env`：

```powershell
Copy-Item .env.example .env
```

局域网部署时，至少检查这些配置：

```env
FRONTEND_PORT=8080
MYSQL_PORT=3306

DJANGO_ALLOWED_HOSTS=*,127.0.0.1,localhost,部署机局域网IP
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://部署机局域网IP:8080
DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://部署机局域网IP:8080

DJANGO_AUTO_MIGRATE=1
DJANGO_TIME_ZONE=Asia/Shanghai

ENABLE_TRADE=0
ENABLE_TRADE_MODULE=0
```

例如部署机 IP 为 `192.168.1.23`：

```env
DJANGO_ALLOWED_HOSTS=*,127.0.0.1,localhost,192.168.1.23
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://192.168.1.23:8080
DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://192.168.1.23:8080
```

说明：

- `DJANGO_ALLOWED_HOSTS` 过窄时，局域网通过 IP 访问会失败
- `DJANGO_CSRF_TRUSTED_ORIGINS` 与 `DJANGO_CORS_ALLOWED_ORIGINS` 建议显式加入部署机 IP
- 仅提供网页访问时，通常只需要开放前端端口 `8080`

## 4. 准备数据库

你有两种方式启动数据库。

### 方式 A：带现有业务数据启动

先从旧环境导出数据库 SQL，例如 `jdgp.sql`，再复制到 [`docker/mysql/init`](docker/mysql/init) 目录：

```text
docker/mysql/init/jdgp.sql
```

支持文件类型：

- `.sql`
- `.sql.gz`
- `.sh`

注意：`docker/mysql/init/` 中的脚本只会在 `mysql_data` 数据卷第一次初始化时执行一次。

### 方式 B：先启动空库

如果你暂时没有导出的 SQL，也可以直接启动。MySQL 会先创建空数据库，后端会根据 `DJANGO_AUTO_MIGRATE=1` 自动执行当前 migrations。

## 5. 启动服务

在项目根目录执行：

```powershell
docker compose up -d --build
```

首次启动会完成：

- 启动 MySQL 容器
- 执行 `docker/mysql/init/` 中的初始化脚本（如果数据卷为空）
- 启动 Django + Gunicorn
- 启动前端 `nginx`

如果你的 SQL 很大，默认配置已经做了两项保护：

- `db` 健康检查使用更长的 `start_period`
- MySQL 默认启用 `MYSQL_INNODB_REDO_LOG_CAPACITY=1G`

需要时可在 `.env` 中调高：

```env
MYSQL_INNODB_REDO_LOG_CAPACITY=2G
```

## 6. 检查服务状态

执行：

```powershell
docker compose ps
docker compose logs -f
```

部署成功后，部署机本机应至少可访问：

- `http://localhost:8080`
- `http://localhost:8080/api/health/`
- `http://localhost:8080/admin/`

## 7. 获取局域网访问地址

在部署机上执行：

```powershell
ipconfig
```

找到当前网卡的 IPv4 地址，例如：

```text
192.168.1.23
```

局域网其他电脑使用以下地址访问：

```text
http://192.168.1.23:8080
```

## 8. Windows 防火墙

如果部署机是 Windows，通常还需要放行入站 TCP `8080` 端口，否则局域网其他电脑可能打不开页面。

只有在以下场景下，才需要考虑放行 `3306`：

- 你要从其他电脑直连 MySQL
- 你要用数据库工具远程管理数据库

如果只是让其他电脑访问网页，一般只需要开放 `8080`。

## 9. 常见问题

### 我已经启动过一次空库，再放 SQL 为什么没生效？

因为 `docker/mysql/init/` 只会在数据卷首次初始化时执行。需要删除旧卷后重启：

```powershell
docker compose down -v
docker compose up -d --build
```

### 局域网其他电脑打不开页面怎么办？

优先检查：

- 部署机本机能否访问 `http://localhost:8080`
- Windows 防火墙是否已放行 `8080`
- 局域网是否允许同网段互访
- `.env` 中 `DJANGO_ALLOWED_HOSTS` 是否过窄
- `.env` 中 `DJANGO_CSRF_TRUSTED_ORIGINS` 是否遗漏部署机 IP

### `3306` 端口被占用怎么办？

在 `.env` 中修改：

```env
MYSQL_PORT=3307
```

然后重新启动：

```powershell
docker compose up -d --build
```

### `8080` 端口被占用怎么办？

在 `.env` 中修改：

```env
FRONTEND_PORT=8081
```

此时局域网访问地址也要改为：

```text
http://部署机局域网IP:8081
```

### 后续如何更新代码？

在部署机根目录执行：

```powershell
git pull
docker compose up -d --build
```

如果数据库结构发生变化，当前配置会自动执行 Django migrations。

## 10. 最短操作清单

1. 在部署机安装 `Git` 和 `Docker Desktop`
2. `git clone` 仓库并进入目录
3. 复制 [`.env.example`](.env.example) 为 `.env`
4. 把部署机局域网 IP 写入 `DJANGO_ALLOWED_HOSTS`、`DJANGO_CSRF_TRUSTED_ORIGINS`、`DJANGO_CORS_ALLOWED_ORIGINS`
5. 有旧数据就把 SQL 放到 [`docker/mysql/init`](docker/mysql/init)
6. 执行 `docker compose up -d --build`
7. 在部署机确认 `http://localhost:8080` 可访问
8. 放行部署机防火墙 `8080`
9. 其他电脑通过 `http://部署机局域网IP:8080` 使用系统
