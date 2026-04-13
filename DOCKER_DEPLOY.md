# Docker 部署说明

## 当前部署内容

- `frontend`: 构建前端并通过 `nginx` 暴露服务
- `backend`: Django + Gunicorn
- `db`: MySQL 8.4

默认部署已经适配局域网访问，自动交易模块默认关闭。

## 最简流程

如果你只是要把仓库克隆到另一台机器上直接跑起来，只需要：

1. 导入项目所需的 MySQL SQL
2. 执行：

```bash
docker compose up -d --build
```

默认访问地址：

- `http://localhost:8080`
- `http://宿主机局域网IP:8080`

## 数据库初始化方式

### 首次启动前自动导入

把 SQL 文件放到 `docker/mysql/init/` 中：

- `.sql`
- `.sql.gz`
- `.sh`

然后启动容器：

```bash
docker compose up -d --build
```

注意：只有第一次创建 `mysql_data` 数据卷时会自动执行。

### 启动后手动导入

默认 MySQL 对宿主机暴露 `3306`：

```bash
mysql -h 127.0.0.1 -P 3306 -u daoquant -p jdgp < your_dump.sql
```

## 默认配置

当前仓库已经提供默认值，不需要强制创建 `.env`。

如需覆盖，可复制 `.env.example` 为 `.env`，常用配置包括：

- `FRONTEND_PORT`
- `MYSQL_PORT`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`

## 局域网访问说明

容器已通过宿主机端口映射监听：

- 前端：`${FRONTEND_PORT:-8080}`
- 数据库：`${MYSQL_PORT:-3306}`

因此局域网其他主机可以直接访问：

```text
http://宿主机IP:8080
```

如果无法访问，请检查：

- 宿主机防火墙是否放行对应端口
- 路由器或交换网络是否允许同网段互访
- `.env` 中是否把 `DJANGO_ALLOWED_HOSTS` 改得过窄

## 常用命令

启动：

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

重建数据库卷：

```bash
docker compose down -v
docker compose up -d --build
```
