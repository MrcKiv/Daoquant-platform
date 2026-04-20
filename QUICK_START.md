# Daoquant-platform 快速启动指南

## 系统要求

- Python 3.8+
- Node.js 16+
- MySQL 5.7+

## 一键启动

```bash
python start_system.py
```

这个脚本会自动：
- 启动Django后端服务
- 启动Vue前端服务
- 打开浏览器访问前端首页

## 手动启动

### 1. 启动后端服务
```bash
cd backend_main
python manage.py runserver 0.0.0.0:8000
```

### 2. 启动前端服务
```bash
cd frontend
npm install
npm run dev
```

## 访问地址

- **前端页面**: http://localhost:5173
- **后端API**: http://localhost:8000

## 主要保留模块

- 首页
- 编写策略
- AI策略助手
- 我的策略
- 用户与后台管理

## 注意事项

1. 确保 MySQL 服务运行且连接配置正确。
2. 确保 `8000` 和 `5173` 端口未被占用。
3. 前端首次运行前需要先执行 `npm install`。

## 常见问题

### 后端启动失败
检查 MySQL 服务是否运行，以及数据库连接配置是否正确。

### 前端启动失败
检查 Node.js 版本，确保 `npm` 命令可用。

### 页面空白或接口报错
检查前后端是否都已启动，以及浏览器控制台 / Django 日志中的错误信息。

### 需要补全股票数据
前端已经移除了在线补数入口。
如果你使用的是 `xtquant` 付费接口，请由服务器管理员手动运行 `xtquant_backfill.py`，说明见 [XTQUANT_BACKFILL_DEPLOY.md](XTQUANT_BACKFILL_DEPLOY.md)。

## 建议排查顺序

1. 先看终端启动日志。
2. 再看浏览器开发者工具的 Network / Console。
3. 最后检查 Django 服务日志。

