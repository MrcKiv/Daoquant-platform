# Docker 部署与局域网访问指南

本文档适用于这样的使用场景：

- 项目部署在一台专门的电脑上
- 局域网内其他电脑通过浏览器访问系统
- 其他电脑不需要安装 Docker，也不需要再克隆仓库

默认部署链路如下：

- `frontend`: Vite 构建后由 `nginx` 提供静态页面与反向代理
- `backend`: Django + Gunicorn
- `db`: MySQL 8.4

自动交易模块在默认 Docker 部署中关闭，不影响主站与回测功能。

## 推荐部署方式

推荐把系统部署在一台稳定在线的电脑上，作为局域网内的服务端。  
其他电脑只需要通过浏览器访问：

```text
http://部署机局域网IP:8080
```

例如：

```text
http://192.168.1.23:8080
```

## 第一步：从当前电脑导出数据库 SQL

如果你现在已有一套正在使用的数据，先从当前电脑导出 MySQL SQL 文件。

建议导出内容包含：

- 表结构
- 业务数据
- 必要的初始化数据

可以使用以下任一方式导出：

- `mysqldump`
- Navicat
- MySQL Workbench

建议最终得到一个完整的 `.sql` 文件，例如：

```text
jdgp.sql
```

## 第二步：在目标电脑安装运行环境

目标电脑至少需要安装：

- `Git`
- `Docker Desktop`

如果不是 Windows，也可以安装：

- `Docker Engine`
- `Docker Compose`

建议目标电脑具备以下条件：

- 长时间开机
- 位于与你的使用电脑同一局域网
- 具备固定或相对稳定的局域网 IP

## 第三步：在目标电脑拉取代码

在目标电脑打开终端，执行：

```powershell
git clone https://github.com/MrcKiv/Daoquant-platform.git
cd Daoquant-platform
```

## 第四步：创建部署用 `.env`

不要直接复制源机器当前正在使用的私有 `.env`。  
更稳妥的方式是基于仓库提供的 [.env.example](/D:/Daoquant-platform/.env.example) 新建一份 `.env`。

执行：

```powershell
Copy-Item .env.example .env
```

然后至少确认以下配置：

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

例如部署机 IP 为 `192.168.1.23` 时，可以写成：

```env
DJANGO_ALLOWED_HOSTS=*,127.0.0.1,localhost,192.168.1.23
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://192.168.1.23:8080
DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080,http://192.168.1.23:8080
```

说明：

- `DJANGO_ALLOWED_HOSTS` 过窄时，局域网通过 IP 访问可能失败
- `DJANGO_CSRF_TRUSTED_ORIGINS` 与 `DJANGO_CORS_ALLOWED_ORIGINS` 建议显式加入部署机 IP
- 如果你只需要别人通过网页访问系统，通常只需要开放前端端口 `8080`

## 第五步：准备数据库导入文件

把上一步导出的 SQL 文件复制到：

[docker/mysql/init](/D:/Daoquant-platform/docker/mysql/init)

例如放成：

```text
docker/mysql/init/jdgp.sql
```

支持的初始化文件类型包括：

- `.sql`
- `.sql.gz`
- `.sh`

默认部署已经针对“大体积首次导入”做了两项更保守的处理：

- `db` 健康检查增加了更长的 `start_period`，并提高了 `retries`
- MySQL 默认启用 `innodb_redo_log_capacity=1G`

如果你的 SQL 特别大，还可以在 `.env` 中继续覆盖：

```env
MYSQL_INNODB_REDO_LOG_CAPACITY=2G
```

## 第六步：首次启动服务

在项目根目录执行：

```powershell
docker compose up -d --build
```

首次启动会完成以下工作：

- 启动 MySQL 容器
- 自动执行 `docker/mysql/init/` 中的初始化 SQL
- 启动 Django + Gunicorn
- 启动前端 `nginx`

## 第七步：检查服务是否正常

执行：

```powershell
docker compose ps
docker compose logs -f
```

如果部署成功，部署机本机应至少可以访问：

- `http://localhost:8080`
- `http://localhost:8080/api/health/`
- `http://localhost:8080/admin/`

## 第八步：获取部署机的局域网 IP

在目标电脑执行：

```powershell
ipconfig
```

查看当前网卡的 IPv4 地址，例如：

```text
192.168.1.23
```

## 第九步：让局域网其他电脑访问

局域网中的其他电脑不需要安装 Docker，也不需要克隆仓库。  
它们只需要在浏览器中打开：

```text
http://部署机局域网IP:8080
```

例如：

```text
http://192.168.1.23:8080
```

## Windows 防火墙设置

如果目标电脑是 Windows，通常还需要放行入站 TCP `8080` 端口，否则局域网其他电脑可能无法访问页面。

只有在以下场景下，才需要考虑开放 `3306`：

- 你希望其他电脑直接连接 MySQL
- 你要用数据库工具远程管理数据库

如果只是让其他电脑使用网页回测系统，通常只需要开放 `8080`。

## 数据库导入的两个常见方式

### 方式 1：首次启动前自动导入

把 SQL 放入 `docker/mysql/init/` 后，直接执行：

```powershell
docker compose up -d --build
```

注意：只有第一次创建 `mysql_data` 数据卷时，MySQL 才会自动执行该目录下的初始化脚本。

### 方式 2：容器启动后手动导入

如果你已经启动过容器，也可以手动导入：

```powershell
mysql -h 127.0.0.1 -P 3306 -u daoquant -p jdgp < your_dump.sql
```

默认账号如下：

- 用户名：`daoquant`
- 密码：`daoquant123`
- Root 密码：`root123456`

## 常见问题

### 1. 我已经先启动过一次空库，现在再把 SQL 放进去为什么没生效？

因为 `docker/mysql/init/` 中的脚本只会在 MySQL 数据卷第一次初始化时执行一次。  
如果你已经起过一次空库，需要删除旧数据卷后重新启动：

```powershell
docker compose down -v
docker compose up -d --build
```

### 2. 局域网其他电脑打不开页面怎么办？

优先检查以下几项：

- 部署机是否能本机访问 `http://localhost:8080`
- Windows 防火墙是否已放行 `8080`
- 局域网内网络是否允许同网段互访
- `.env` 中 `DJANGO_ALLOWED_HOSTS` 是否限制过窄
- `.env` 中 `DJANGO_CSRF_TRUSTED_ORIGINS` 是否没有加入部署机 IP

### 3. `3306` 端口被占用了怎么办？

可以在 `.env` 中修改：

```env
MYSQL_PORT=3307
```

然后重新启动：

```powershell
docker compose up -d --build
```

### 4. `8080` 端口被占用了怎么办？

可以在 `.env` 中修改：

```env
FRONTEND_PORT=8081
```

然后局域网访问地址也改成：

```text
http://部署机局域网IP:8081
```

### 5. 首次导入大 SQL 很慢，甚至看起来像卡住了，怎么办？

先不要急着判断失败，首次导入大 SQL 时，`db` 容器可能会花比较长时间初始化。  
当前默认配置已经放宽了数据库健康检查，并把 `innodb_redo_log_capacity` 提高到 `1G`。

如果导入数据量更大，可以在 `.env` 中继续调高：

```env
MYSQL_INNODB_REDO_LOG_CAPACITY=2G
```

然后重新启动：

```powershell
docker compose up -d --build
```

## 后续更新项目

以后如果你在仓库里更新了代码，可以在目标电脑执行：

```powershell
git pull
docker compose up -d --build
```

如果数据库结构发生变化，当前配置会自动执行 Django migrations。

## 最短操作清单

如果你只想按最短路径完成部署，可以直接照下面做：

1. 从当前电脑导出业务数据库为 `jdgp.sql`
2. 在目标电脑安装 `Git` 和 `Docker Desktop`
3. 执行 `git clone`
4. 复制 [.env.example](/D:/Daoquant-platform/.env.example) 为 `.env`
5. 在 `.env` 中加入部署机局域网 IP 相关配置
6. 把 `jdgp.sql` 放到 [docker/mysql/init](/D:/Daoquant-platform/docker/mysql/init)
7. 执行 `docker compose up -d --build`
8. 在部署机上确认 `http://localhost:8080` 可访问
9. 放行部署机防火墙 `8080`
10. 其他电脑通过 `http://部署机局域网IP:8080` 使用系统
