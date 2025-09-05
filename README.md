# LeafLow 自动签到脚本

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/keggin-CHN/leaflow-checkin?style=social)](https://github.com/keggin-CHN/leaflow-checkin/stargazers)

[English](README_EN.md) | [简体中文](#简体中文)

LeafLow 自动签到脚本，支持多账号批量签到，使用 Token-based 认证方式，适合在服务器环境中稳定运行。

## ✨ 特性

- 🔐 **Token-based 认证**：基于 Cookie/Token 认证，绕过复杂的登录流程
- 🖥️ **服务器友好**：无需浏览器环境，纯 HTTP 请求实现
- 👥 **多账号支持**：支持批量管理多个账号
- 📊 **详细日志**：完整的操作日志和调试信息
- 🔔 **通知推送**：支持 Telegram、企业微信等多种通知方式
- ⚡ **自动重试**：智能错误处理和重试机制
- 🎯 **积分统计**：自动提取和显示获得的积分
- 🛡️ **安全可靠**：支持 CSRF Token 自动处理

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/keggin-CHN/leaflow-checkin.git
cd leaflow-checkin
pip3 install -r requirements.txt
```

### 2. 获取认证信息

#### 方法A：手动获取（推荐新手）

1. 在浏览器中登录 [LeafLow](https://leaflow.net)
2. 按 `F12` 打开开发者工具，切换到 `Network`（网络）标签页
3. 刷新页面，在请求列表中找到主站的请求（例如 `leaflow.net`）
4. 在右侧的 `Headers` 标签页中，找到 `Request Headers` 下的 `cookie` 字段，并复制其完整内容。

![获取Cookie示例](3D2481C647EF7447A0149366C6802284.png)

#### 方法B：使用辅助工具

适合熟悉开发者工具的用户：

```bash
python3 get_tokens_helper.py
```

详细步骤请参考：[HOW_TO_GET_TOKENS.md](HOW_TO_GET_TOKENS.md)

### 3. 配置账号信息

#### 方法A: 手动创建 `config.accounts.json`

```json
{
  "accounts": [
    {
      "token_data": {
        "cookies": {
          "leaflow_session": "your_session_token",
          "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": "your_remember_token",
          "XSRF-TOKEN": "your_csrf_token"
        }
      }
    }
  ]
}
```

#### 方法B: 使用 `get_tokens_helper.py` 生成配置 (推荐)

1.  **本地运行**: 直接运行 `python get_tokens_helper.py`，会使用内置的cookie字符串生成配置文件。
2.  **GitHub Actions**: 脚本会自动从环境变量 `LEAFLOW_COOKIES` 读取cookie字符串，并生成配置文件。

### 4. 通知配置

#### 方法A: 使用环境变量

```bash
# Telegram 通知
export TG_BOT_TOKEN="your_telegram_bot_token"
export TG_USER_ID="your_telegram_user_id"

# 企业微信通知
export QYWX_KEY="your_wechat_webhook_key"
```

#### 方法B: 使用 `config.notify.json` (推荐)

创建 `config.notify.json` 文件，填入通知配置：

```json
{
  "QYWX_KEY": "your_wechat_webhook_key",
  "TG_BOT_TOKEN": "your_telegram_bot_token",
  "TG_USER_ID": "your_telegram_user_id"
}
```

### 5. 运行签到

```bash
# 基础运行
python3 checkin_token.py

# 调试模式
python3 checkin_token.py --debug

# 启用通知推送
python3 checkin_token.py --notify
```

## 📋 配置说明

### 账号配置

| 字段 | 说明 | 必填 |
|------|------|------|
| `email` | 账号邮箱 | 否（仅用于日志显示） |
| `note` | 账号备注 | 否（仅用于日志显示） |
| `enabled` | 是否启用 | 否（默认true） |
| `token_data` | 认证数据 | **是（核心必需）** |

### 认证数据

必需的 Cookies（至少需要以下之一）：
- `leaflow_session`：会话令牌
- `remember_web_*`：记住登录令牌
- `XSRF-TOKEN`：CSRF 保护令牌

### 通知配置

通过环境变量配置通知推送：

```bash
# Telegram 通知
export TG_BOT_TOKEN="your_telegram_bot_token"
export TG_USER_ID="your_telegram_user_id"

# 企业微信通知
export QYWX_KEY="your_wechat_webhook_key"

# 启用一言
export HITOKOTO="true"
```

或在代码中直接配置：

```python
from notify import send
send("标题", "内容", TG_BOT_TOKEN="token", TG_USER_ID="user_id")
```

## 🤖 自动化部署

### Crontab 定时任务

```bash
# 编辑 crontab
crontab -e

# 每天上午 8:30 执行签到
30 8 * * * cd /path/to/leaflow-checkin && python3 checkin_token.py >> cron.log 2>&1
```

### GitHub Actions

1.  **Fork 本仓库**
2.  **添加 Secrets**:
    在你的仓库 `Settings` -> `Secrets and variables` -> `Actions` 中, 添加以下 secrets:
    *   `LEAFLOW_COOKIES`: 你的完整浏览器 cookie 字符串。
    *   `QYWX_KEY`: (可选) 你的企业微信机器人 Webhook Key。
    *   `TG_BOT_TOKEN`: (可选) 你的 Telegram Bot Token。
    *   `TG_USER_ID`: (可选) 你的 Telegram User ID。
3.  **启用 Actions**:
    在你的仓库 `Actions` 页面，启用 GitHub Actions。

#### `checkin.yml` 示例:

```yaml
name: LeafLow Auto Checkin

on:
  schedule:
    - cron: '30 0 * * *'  # 每天 8:30 UTC+8
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install requests
    - name: Prepare config
      run: python3 get_tokens_helper.py
      env:
        LEAFLOW_COOKIES: ${{ secrets.LEAFLOW_COOKIES }}
    - name: Run checkin
      run: python3 checkin_token.py --notify
      env:
        QYWX_KEY: ${{ secrets.QYWX_KEY }}
        TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
        TG_USER_ID: ${{ secrets.TG_USER_ID }}
```

## 📁 文件结构

```
leaflow-checkin/
├── checkin_token.py          # 主签到脚本
├── get_tokens_helper.py      # Token 获取辅助工具
├── notify.py                 # 通知推送模块
├── quick_start.py           # 快速开始脚本
├── config.accounts.json     # 账号配置文件
├── config.token.template.json # 配置模板
├── TOKEN_USAGE_GUIDE.md     # 详细使用指南
└── README.md               # 说明文档
```

## 🛠️ 工具说明

### checkin_token.py
主要的签到脚本，支持：
- Token-based 认证
- 多账号批量处理
- 自动签到检测
- 错误重试机制

### get_tokens_helper.py
Token 获取辅助工具：
- 解析 cURL 命令
- 提取 Cookies 和 Headers
- 生成配置条目

### notify.py
通知推送模块，支持：
- Telegram Bot 推送
- 企业微信机器人推送
- 控制台输出
- 一言随机句子

## 🔧 参数说明

### 命令行参数

```bash
python3 checkin_token.py [options]

Options:
  --config FILE    指定配置文件路径
  --debug          启用调试模式
  --notify         启用通知推送
  --no-notify      禁用通知推送
```

### 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `log_level` | 日志级别 | INFO |
| `retry_delay` | 重试延迟(秒) | 3 |
| `timeout` | 请求超时(秒) | 30 |
| `user_agent` | 用户代理 | Chrome/139.0.0.0 |

## 🐛 故障排除

### 常见问题

1. **认证失败**
   - 检查 Token 是否过期
   - 重新获取最新的 Cookies

2. **签到失败**
   - 检查网络连接
   - 使用 `--debug` 模式查看详细日志

3. **通知推送失败**
   - 检查通知配置是否正确
   - 验证 Token 和权限

### 调试模式

```bash
python3 checkin_token.py --debug
```

调试模式会输出详细的请求和响应信息，帮助诊断问题。

## 📝 更新日志

### v1.0.0 (2025-08-17)
- ✨ 初始版本发布
- 🔐 Token-based 认证支持
- 👥 多账号批量签到
- 🔔 通知推送功能
- 📊 详细日志记录

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

- 本脚本仅供学习和研究使用
- 请遵守 LeafLow 网站的使用条款
- 使用本脚本造成的任何后果由用户自行承担
- 请合理使用，避免对服务器造成过大压力

## 🙏 致谢

- [LeafLow](https://leaflow.net) - 容器化部署平台
- [Hitokoto](https://hitokoto.cn) - 一言 API 服务

---

⭐ 如果这个项目对您有帮助，请给个 Star！

## 简体中文

*本文档默认为中文版本，英文版本请查看 [README_EN.md](README_EN.md)*

# 新增功能：app.py
## 环境变量说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `PORT` | Web控制面板端口 | `8181` |
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` |
| `JWT_SECRET_KEY` | JWT密钥（留空自动生成） | 自动生成 |
| `DB_TYPE` | 数据库类型 (sqlite/mysql) | `sqlite` |
| `DB_HOST` | MySQL主机地址 | `localhost` |
| `DB_PORT` | MySQL端口 | `3306` |
| `DB_NAME` | MySQL数据库名 | `leaflow_checkin` |
| `DB_USER` | MySQL用户名 | `root` |
| `DB_PASSWORD` | MySQL密码 | 空 |

## 主要功能特性

1. **Web控制面板**：监听8181端口，提供完整的Web管理界面
2. **JWT认证**：7天有效期的安全认证机制
3. **账户管理**：支持添加、删除、启用/禁用账户
4. **定时签到**：每个账户可设置独立的签到时间
5. **签到历史**：记录所有签到历史和统计信息
6. **通知管理**：支持Telegram和企业微信通知配置
7. **数据持久化**：支持SQLite和MySQL数据库

## 使用方法

1. **构建并运行Docker容器**：
```bash
docker build -t leaflow-checkin .
docker run -d -p 8181:8181 \
  -e ADMIN_PASSWORD=your_secure_password \
  -v $(pwd)/data:/app/data \
  --name leaflow-checkin \
  leaflow-checkin
```

2. **访问控制面板**：
   - 打开浏览器访问 `http://localhost:8181`
   - 使用设置的用户名密码登录

3. **添加账户**：
   - 登录后点击"Add Account"
   - 输入账户名称和token数据
   - 设置每日签到时间

这个解决方案完全解决了Docker容器重启的问题，因为现在应用程序作为一个持续运行的Web服务存在。
