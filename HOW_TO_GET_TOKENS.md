# Leaflow Token 使用指南

## 简介

Token-based 方案通过使用浏览器获取的认证信息（cookies/tokens）来实现自动签到，避开了复杂的登录流程。

## 优势

- ✅ **服务器友好**：无需安装浏览器或 Chrome
- ✅ **内存占用低**：只使用 HTTP 请求，不渲染 JavaScript
- ✅ **稳定可靠**：绕过复杂的 OAuth 流程
- ✅ **易于维护**：Token 有效期长，更新频率低

## 使用步骤

### 1. 获取认证信息

#### 方法A：使用浏览器开发者工具（推荐）

1. **打开浏览器**：使用 Chrome、Firefox、Edge 等现代浏览器
2. **访问网站**：导航到 `https://leaflow.net` 并登录
3. **打开开发者工具**：按 `F12` 或右键选择“检查”
4. **查看网络请求**：
   - 切换到 `Network`(网络) 标签页
   - 刷新页面或访问任意需要登录的页面（如个人中心）
   - 在请求列表中找到主站点的请求（例如 `leaflow.net`）
5. **复制 Cookies**：
   - 在右侧的 `Headers` 标签页中，向下滚动到 `Request Headers` 部分
   - 找到 `cookie` 字段，并复制其完整的字符串值。

![获取Cookie示例](3D2481C647EF7447A0149366C6802284.png)

#### 方法B：直接查看 Cookies

1. **在已登录状态下**：按 `F12` 打开开发者工具
2. **Application/应用程序标签页**：
   - 找到左侧的 "Storage" → "Cookies"
   - 点击 `https://leaflow.net`
   - 复制所有 cookies 的名称和值

### 2. 配置文件设置

1. **复制模板**：
   ```bash
   cp config.token.template.json config.accounts.json
   ```

2. **编辑配置**：
   ```bash
   nano config.accounts.json  # 或使用其他编辑器
   ```

3. **填入认证信息**：
   ```json
   {
     "settings": {
       "log_level": "INFO",
       "retry_delay": 3,
       "timeout": 30,
       "user_agent": "Mozilla/5.0..."
     },
     "accounts": [
       {
         "token_data": {
           "cookies": {
             "leaflow_session": "实际的session值",
             "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": "实际的remember_token值",
             "XSRF-TOKEN": "实际的XSRF-TOKEN值"
           }
         }
       }
     ]
   }
   ```

### 3. 运行签到脚本

```bash
# 基础运行
python3 checkin_token.py

# 调试模式（查看详细日志）
python3 checkin_token.py --debug

# 使用自定义配置文件
python3 checkin_token.py --config my_config.json

# 启用通知推送
python3 checkin_token.py --notify
```

## 配置文件详解

### Settings 设置项

```json
{
  "settings": {
    "log_level": "INFO",        // 日志级别：DEBUG, INFO, WARNING, ERROR
    "retry_delay": 3,           // 账号间延迟秒数
    "timeout": 30,              // HTTP请求超时时间
    "user_agent": "..."         // 浏览器User-Agent字符串
  }
}
```

### Account 账号配置

```json
{
  "token_data": {
    "cookies": {                // Cookie认证信息
      "leaflow_session": "会话cookie值",
      "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": "记住登录cookie值",
      "XSRF-TOKEN": "XSRF令牌值"
    }
  }
}
```

注意：配置已简化，现在只需要 `token_data` 字段，无需邮箱和备注。

## 常见认证信息类型

### 必需的 Cookies（需要以下所有）
- `leaflow_session`：会话cookie
- `remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d`：记住登录cookie
- `XSRF-TOKEN`：XSRF保护令牌

### 可能需要的 Cookies
- `csrf_token`：CSRF保护令牌
- `_ga`, `_gid`：Google Analytics（通常不影响认证）
- `language`：语言设置

### HTTP Headers（可选）
- `Authorization: Bearer xxx`：Bearer令牌认证
- `X-Requested-With: XMLHttpRequest`：AJAX请求标识
- `X-CSRF-TOKEN`：CSRF令牌头部

## Token 获取示例

### Chrome 浏览器示例

1. 登录 Leaflow 后，按 F12
2. Network 标签页，访问任意页面
3. 找到页面请求，右键选择 "Copy as cURL"
4. 从 cURL 命令中提取 cookies：

```bash
curl 'https://leaflow.net/dashboard' \
  -H 'Cookie: leaflow_session=abc123; remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d=def456; XSRF-TOKEN=ghi789'
```

提取结果：
```json
{
  "cookies": {
    "leaflow_session": "abc123",
    "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": "def456", 
    "XSRF-TOKEN": "ghi789"
  }
}
```

## 验证和测试

### 1. 测试认证有效性
```bash
python3 checkin_token.py --debug
```
查看日志中的认证测试结果。

### 2. 检查签到状态
脚本会自动检测是否已经签到，避免重复签到。

### 3. 日志分析
- 查看 `leaflow_token_checkin.log` 文件
- 关注认证测试和签到响应信息

## 自动化部署

### Crontab 定时任务
```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天8点30分执行）
30 8 * * * cd /path/to/script && python3 checkin_token.py >> cron.log 2>&1
```

### Systemd Timer（推荐）
```bash
# 创建服务文件
sudo nano /etc/systemd/system/leaflow-checkin.service

# 创建定时器文件
sudo nano /etc/systemd/system/leaflow-checkin.timer

# 启用定时器
sudo systemctl enable leaflow-checkin.timer
sudo systemctl start leaflow-checkin.timer
```

## 故障排除

### 1. 认证失败
- **症状**：`Authentication failed` 错误
- **解决**：重新获取最新的 cookies/tokens
- **原因**：Token过期或无效

### 2. 签到失败
- **症状**：`All checkin methods failed`
- **解决**：检查签到页面是否有变化，更新脚本逻辑
- **调试**：使用 `--debug` 模式查看详细信息

### 3. 网络问题
- **症状**：请求超时或连接错误
- **解决**：检查网络连接，增加 timeout 设置
- **代理**：如需要，在代码中添加 proxy 设置

### 4. 配置文件错误
- **症状**：`Configuration file format error`
- **解决**：检查 JSON 格式，使用在线 JSON 验证器

## Token 维护

### 更新频率
- **会话Token**：通常7-30天过期
- **记住登录Token**：通常30-90天过期
- **建议**：每月更新一次，或在失败时更新

### 自动检测
脚本会在认证失败时提示需要更新Token，无需手动监控。

## 安全注意事项

1. **保护配置文件**：
   ```bash
   chmod 600 config.accounts.json  # 仅所有者可读写
   ```

2. **定期更新**：及时更新过期的认证信息

3. **备份配置**：保留有效配置的备份

4. **监控日志**：定期检查日志中的异常信息

## 支持的功能

- ✅ 多账号批量签到
- ✅ 自动检测签到状态
- ✅ CSRF Token 自动处理
- ✅ 详细日志记录
- ✅ 通知推送支持
- ✅ 灵活的配置选项
- ✅ 错误重试机制

这个 Token-based 方案是目前在服务器环境中最可行的解决方案，避免了复杂的浏览器模拟，同时保持了自动化的便利性。
