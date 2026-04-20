# xtquant 补数部署说明

## 架构说明

`xtquant` 依赖 Windows 二进制模块，不能在 Linux Docker 容器内原生运行。

当前仓库采用下面的部署方式：

- `frontend` 和 `backend` 继续走 Docker 部署
- 真正执行 `xtquant` 补数的是 Windows 主机上的独立 worker
- Docker 后端通过 `BACKFILL_HOST_SERVICE_URL` 调用 Windows worker

## 方案一：本机 Windows + Docker Desktop

适合本机开发或部署在一台 Windows 机器上。

### 1. 配置 `.env`

至少确认下面这些配置：

```env
BACKFILL_USE_HOST_SERVICE=1
BACKFILL_HOST_SERVICE_URL=http://host.docker.internal:8765
BACKFILL_HOST_SERVICE_TOKEN=

XTQUANT_BACKFILL_HOST=0.0.0.0
XTQUANT_BACKFILL_PORT=8765
XTQUANT_BACKFILL_TOKEN=
XTQUANT_TOKEN=你的xtquant付费token
```

如果 MySQL 也是当前仓库的 Docker 服务，Windows worker 默认会把 `DB_HOST=db` 自动转成 `127.0.0.1`，直接复用当前数据库配置即可。

### 2. 安装 Windows worker 独立环境

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_xtquant_backfill_host.ps1
```

这个脚本会在仓库根目录创建独立虚拟环境 `.venv-xtquant-backfill`，不会把依赖装进系统级 Python。
如果当前机器是精简版或 Conda Python，`venv` 可能不带 `pip`；这时建议安装标准版 Python 3.11，再执行一次安装脚本。

### 3. 启动 Windows worker

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_xtquant_backfill_host_service.ps1
```

日志默认写入：

- `runtime/xtquant_backfill_host_service.out.log`
- `runtime/xtquant_backfill_host_service.err.log`

### 4. 重建 Docker 主站

```powershell
docker compose up -d --build backend frontend
```

## 方案二：远程 Windows worker + 远程 Docker 主站

适合 Docker 主站不在 Windows 上，但你仍然必须使用 `xtquant`。

### 1. 在 Windows worker 上启动补数服务

同样执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_xtquant_backfill_host.ps1
powershell -ExecutionPolicy Bypass -File scripts\start_xtquant_backfill_host_service.ps1
```

### 2. 让 Docker 后端指向 Windows worker

把 Docker 主站的 `.env` 改成 Windows worker 的可访问地址，例如：

```env
BACKFILL_USE_HOST_SERVICE=1
BACKFILL_HOST_SERVICE_URL=http://192.168.1.20:8765
BACKFILL_HOST_SERVICE_TOKEN=自定义共享密钥
```

同时在 Windows worker 的环境里配置：

```env
XTQUANT_BACKFILL_TOKEN=自定义共享密钥
BACKFILL_DB_HOST=数据库地址
BACKFILL_DB_PORT=3306
BACKFILL_DB_NAME=jdgp
BACKFILL_DB_USER=daoquant
BACKFILL_DB_PASSWORD=daoquant123
XTQUANT_TOKEN=你的xtquant付费token
```

## 页面使用说明

前端新增入口：

- 导航栏首页后面的“补全股票数据”

页面会自动显示：

- 数据库当前最晚日期
- 今天日期
- 本次补数区间
- 补数进度、批次数、写入记录数
- 当前执行方式和 Windows worker 连接状态

## 常见问题

### 1. 提示无法连接 Windows 主机补数服务

优先检查：

- Windows worker 是否已经启动
- `BACKFILL_HOST_SERVICE_URL` 是否可从 Docker 后端访问
- 防火墙是否放行 `8765`

### 2. 提示鉴权失败

确认这两个值完全一致：

- Docker 后端：`BACKFILL_HOST_SERVICE_TOKEN`
- Windows worker：`XTQUANT_BACKFILL_TOKEN`

### 3. Windows worker 连不上数据库

如果 worker 不和 Docker MySQL 在同一台机器，必须显式配置：

- `BACKFILL_DB_HOST`
- `BACKFILL_DB_PORT`
- `BACKFILL_DB_NAME`
- `BACKFILL_DB_USER`
- `BACKFILL_DB_PASSWORD`
