# Leaflow Auto Check-in Script

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/keggin-CHN/leaflow-checkin?style=social)](https://github.com/keggin-CHN/leaflow-checkin/stargazers)

[English](#english) | [简体中文](README.md)

An automated check-in script for Leaflow that supports multi-account batch operations using Token-based authentication, designed to run stably in server environments.

## ✨ Features

- 🔐 **Token-based Authentication**: Uses Cookie/Token authentication to bypass complex login processes
- 🖥️ **Server-Friendly**: No browser environment required, pure HTTP requests
- 👥 **Multi-Account Support**: Batch management of multiple accounts
- 📊 **Detailed Logging**: Complete operation logs and debug information
- 🔔 **Push Notifications**: Support for Telegram, WeChat Work, and other notification methods
- ⚡ **Auto Retry**: Intelligent error handling and retry mechanism
- 🎯 **Credit Statistics**: Automatic extraction and display of earned credits
- 🛡️ **Secure & Reliable**: Support for automatic CSRF token handling

## 🚀 Quick Start

### 1. Install Dependencies

```bash
git clone https://github.com/keggin-CHN/leaflow-checkin.git
cd leaflow-checkin
pip3 install -r requirements.txt
```

### 2. Get Authentication Information

Use browser developer tools to get Cookies:

1. Login to [Leaflow](https://leaflow.net) in your browser
2. Press `F12` to open developer tools
3. Switch to "Network" tab
4. Visit any page that requires login
5. Right-click on request → "Copy as cURL"

Or use the provided helper tool:

```bash
python3 get_tokens_helper.py
```

### 3. Configure Account Information

Edit `config.accounts.json`:

```json
{
  "settings": {
    "log_level": "INFO",
    "retry_delay": 3,
    "timeout": 30
  },
  "accounts": [
    {
      "email": "your_email@example.com",
      "note": "Main Account",
      "enabled": true,
      "token_data": {
        "cookies": {
          "leaflow_session": "your_session_token",
          "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d": "your_remember_token"
        }
      }
    }
  ]
}
```

### 4. Run Check-in

```bash
# Basic run
python3 checkin_token.py

# Debug mode
python3 checkin_token.py --debug

# Enable push notifications
python3 checkin_token.py --notify
```

## 📋 Configuration Guide

### Account Configuration

| Field | Description | Required |
|-------|-------------|----------|
| `email` | Account email | No (for display only) |
| `note` | Account note | No (for display only) |
| `enabled` | Whether enabled | No (default true) |
| `token_data` | Authentication data | **Yes (Essential)** |

### Authentication Data

Required Cookies (at least one of the following):
- `leaflow_session`: Session token
- `remember_web_*`: Remember login token
- `XSRF-TOKEN`: CSRF protection token

### Notification Configuration

Configure push notifications via environment variables:

```bash
# Telegram notifications
export TG_BOT_TOKEN="your_telegram_bot_token"
export TG_USER_ID="your_telegram_user_id"

# WeChat Work notifications
export QYWX_KEY="your_wechat_webhook_key"

# Enable Hitokoto
export HITOKOTO="true"
```

Or configure directly in code:

```python
from notify import send
send("Title", "Content", TG_BOT_TOKEN="token", TG_USER_ID="user_id")
```

## 🤖 Automated Deployment

### Crontab Scheduled Task

```bash
# Edit crontab
crontab -e

# Execute check-in daily at 8:30 AM
30 8 * * * cd /path/to/leaflow-checkin && python3 checkin_token.py >> cron.log 2>&1
```

### GitHub Actions

Create `.github/workflows/checkin.yml`:

```yaml
name: Leaflow Auto Checkin

on:
  schedule:
    - cron: '30 0 * * *'  # Daily at 8:30 UTC+8
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
    - name: Run checkin
      run: python3 checkin_token.py
      env:
        TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
        TG_USER_ID: ${{ secrets.TG_USER_ID }}
```

## 📁 File Structure

```
leaflow-checkin/
├── checkin_token.py          # Main check-in script
├── get_tokens_helper.py      # Token extraction helper tool
├── notify.py                 # Push notification module
├── quick_start.py           # Quick start script
├── config.accounts.json     # Account configuration file
├── config.token.template.json # Configuration template
├── TOKEN_USAGE_GUIDE.md     # Detailed usage guide
└── README.md               # Documentation
```

## 🛠️ Tool Description

### checkin_token.py
Main check-in script supporting:
- Token-based authentication
- Multi-account batch processing
- Automatic check-in detection
- Error retry mechanism

### get_tokens_helper.py
Token extraction helper tool:
- Parse cURL commands
- Extract Cookies and Headers
- Generate configuration entries

### notify.py
Push notification module supporting:
- Telegram Bot push
- WeChat Work bot push
- Console output
- Hitokoto random sentences

## 🔧 Parameter Description

### Command Line Parameters

```bash
python3 checkin_token.py [options]

Options:
  --config FILE    Specify configuration file path
  --debug          Enable debug mode
  --notify         Enable push notifications
  --no-notify      Disable push notifications
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `log_level` | Log level | INFO |
| `retry_delay` | Retry delay (seconds) | 3 |
| `timeout` | Request timeout (seconds) | 30 |
| `user_agent` | User agent | Chrome/139.0.0.0 |

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check if tokens have expired
   - Re-obtain the latest Cookies

2. **Check-in Failed**
   - Check network connection
   - Use `--debug` mode to view detailed logs

3. **Push Notification Failed**
   - Check if notification configuration is correct
   - Verify tokens and permissions

### Debug Mode

```bash
python3 checkin_token.py --debug
```

Debug mode outputs detailed request and response information to help diagnose issues.

## 📝 Changelog

### v1.0.0 (2025-08-17)
- ✨ Initial release
- 🔐 Token-based authentication support
- 👥 Multi-account batch check-in
- 🔔 Push notification functionality
- 📊 Detailed logging

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

- This script is for learning and research purposes only
- Please comply with Leaflow website's terms of use
- Users are responsible for any consequences of using this script
- Please use reasonably and avoid putting excessive pressure on servers

## 🙏 Acknowledgments

- [Leaflow](https://leaflow.net) - Container deployment platform
- [Hitokoto](https://hitokoto.cn) - Hitokoto API service

---

⭐ If this project helps you, please give it a Star!

## English

*This is the English version. For Chinese version, please see [README.md](README.md)*
