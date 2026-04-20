# xtquant 手动补数说明

## 适用场景

当前仓库已经移除了网页端“补全股票数据”入口，也不再通过 Docker 后端代理补数。

如果你仍然需要使用 `xtquant` 付费接口补全 `stock_1d` 数据，请由服务器管理员在支持 `xtquant` 的机器上手动运行：

- `xtquant_backfill.py`

## 基本原则

- Docker 主站继续负责日常网页访问
- `xtquant` 补数不在 Linux Docker 容器中执行
- 服务器管理员按需手动执行脚本补数
- 补数完成后，网站直接读取更新后的数据库

## 依赖安装

建议在支持 `xtquant` 的 Windows 机器上单独准备一个 Python 环境，然后安装：

```powershell
pip install -r requirements-xtquant-backfill.txt
```

如果你已经有可用的 Python 环境，也可以手动安装：

```powershell
pip install xtquant pandas pymysql SQLAlchemy
```

## 配置方式

脚本会优先读取仓库根目录的 `.env`，你可以直接复用现有数据库配置。

至少确认以下配置可用：

```env
DB_NAME=jdgp
DB_USER=daoquant
DB_PASSWORD=daoquant123
DB_HOST=127.0.0.1
DB_PORT=3306
DB_CHARSET=utf8mb4

XTQUANT_TOKEN=你的xtquant付费token
```

可选补数参数：

```env
BACKFILL_TABLE=stock_1d
BACKFILL_BATCH_SIZE=50
BACKFILL_INITIAL_START_DATE=20200101
BACKFILL_START_DATE=
BACKFILL_END_DATE=
BACKFILL_DB_NAME=
BACKFILL_DB_USER=
BACKFILL_DB_PASSWORD=
BACKFILL_DB_HOST=
BACKFILL_DB_PORT=
BACKFILL_DB_CHARSET=
XTQUANT_OPTIMIZED_ADDRESSES=115.231.218.73:55310,115.231.218.79:55310,42.228.16.211:55300,42.228.16.210:55300,36.99.48.20:55300,36.99.48.21:55300
```

说明：

- 不设置 `BACKFILL_START_DATE` 时，脚本会自动读取目标表最大 `trade_date`，从下一天开始续传
- 不设置 `BACKFILL_END_DATE` 时，脚本默认补到当天
- 如果需要连接另一台数据库，可以单独配置 `BACKFILL_DB_*`

## 运行方式

在仓库根目录执行：

```powershell
python xtquant_backfill.py
```

脚本会输出：

- 当前连接的数据库和表
- 本次补数区间
- 每批处理进度
- 总入库行数和总耗时

## 常见用法

### 1. 自动续传到今天

```powershell
python xtquant_backfill.py
```

### 2. 指定起止日期补数

```powershell
$env:BACKFILL_START_DATE="20240101"
$env:BACKFILL_END_DATE="20240131"
python xtquant_backfill.py
```

### 3. 指定另一台数据库

```powershell
$env:BACKFILL_DB_HOST="192.168.1.10"
$env:BACKFILL_DB_PORT="3306"
$env:BACKFILL_DB_NAME="jdgp"
$env:BACKFILL_DB_USER="daoquant"
$env:BACKFILL_DB_PASSWORD="daoquant123"
python xtquant_backfill.py
```

## 常见问题

### 1. 为什么不再提供网页端补数

`xtquant` 依赖 Windows 二进制模块，不适合绑定到当前 Linux Docker 主站流程里。
为减少部署复杂度，仓库只保留手动补数脚本，由管理员按需执行。

### 2. Linux Docker 里可以直接跑吗

不建议。
如果必须使用 `xtquant`，请在支持 `xtquant` 的 Windows 环境手动运行脚本。

### 3. 补数后网站需要重启吗

通常不需要。
只要数据已经写入同一个业务数据库，网页端读取到的就是最新结果。
