#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leaflow Token-Based Check-in Script
基于预设token/cookie的签到脚本
适用于服务器环境，无需浏览器

使用方法：
1. 手动在浏览器中登录 https://leaflow.net
2. 打开浏览器开发者工具 (F12)
3. 在Network/网络标签页中查找请求的Cookie或Authorization头
4. 将token/cookie添加到配置文件中
5. 运行此脚本进行自动签到
"""

import json
import time
import sys
import logging
import argparse
import requests
from datetime import datetime

class LeafLowTokenCheckin:
    def __init__(self, config_file="config.accounts.json"):
        """初始化Token签到类"""
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
        self.checkin_url = "https://checkin.leaflow.net"
        self.main_site = "https://leaflow.net"
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {self.config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Configuration file {self.config_file} format error")
            sys.exit(1)
    
    def setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config['settings'].get('log_level', 'INFO').upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('leaflow_token_checkin.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, token_data):
        """根据token数据创建会话"""
        session = requests.Session()
        
        # 设置基本headers
        session.headers.update({
            'User-Agent': self.config['settings']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 添加认证信息
        if 'cookies' in token_data:
            # 设置cookies
            for name, value in token_data['cookies'].items():
                session.cookies.set(name, value)
                
        if 'headers' in token_data:
            # 设置自定义headers (如Authorization)
            session.headers.update(token_data['headers'])
        
        return session
    
    def test_authentication(self, session, account_name):
        """测试认证是否有效"""
        try:
            # 尝试访问需要认证的页面
            test_urls = [
                f"{self.main_site}/dashboard",
                f"{self.main_site}/profile",
                f"{self.main_site}/user",
                self.checkin_url,
            ]
            
            for url in test_urls:
                response = session.get(url, timeout=30)
                self.logger.debug(f"[{account_name}] Test {url}: {response.status_code}")
                
                if response.status_code == 200:
                    content = response.text.lower()
                    if any(indicator in content for indicator in ['dashboard', 'profile', 'user', 'logout', 'welcome']):
                        self.logger.info(f"✅ [{account_name}] Authentication valid")
                        return True, "Authentication successful"
                elif response.status_code in [301, 302, 303]:
                    location = response.headers.get('location', '')
                    if 'login' not in location.lower():
                        self.logger.info(f"✅ [{account_name}] Authentication valid (redirect)")
                        return True, "Authentication successful (redirect)"
            
            return False, "Authentication failed - no valid authenticated pages found"
            
        except Exception as e:
            return False, f"Authentication test error: {str(e)}"
    
    def perform_checkin(self, session, account_name):
        """执行签到操作"""
        self.logger.info(f"🎯 [{account_name}] Performing checkin...")
        
        try:
            # 方法1: 直接访问签到页面
            response = session.get(self.checkin_url, timeout=30)
            
            if response.status_code == 200:
                result = self.analyze_and_checkin(session, response.text, self.checkin_url, account_name)
                if result[0]:
                    return result
            
            # 方法2: 尝试API端点
            api_endpoints = [
                f"{self.checkin_url}/api/checkin",
                f"{self.checkin_url}/checkin",
                f"{self.main_site}/api/checkin",
                f"{self.main_site}/checkin"
            ]
            
            for endpoint in api_endpoints:
                try:
                    # GET请求
                    response = session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        success, message = self.check_checkin_response(response.text)
                        if success:
                            return True, message
                    
                    # POST请求
                    response = session.post(endpoint, data={'checkin': '1'}, timeout=30)
                    if response.status_code == 200:
                        success, message = self.check_checkin_response(response.text)
                        if success:
                            return True, message
                            
                except Exception as e:
                    self.logger.debug(f"[{account_name}] API endpoint {endpoint} failed: {str(e)}")
                    continue
            
            return False, "All checkin methods failed"
            
        except Exception as e:
            return False, f"Checkin error: {str(e)}"
    
    def analyze_and_checkin(self, session, html_content, page_url, account_name):
        """分析页面内容并执行签到"""
        # 检查是否已经签到
        if self.already_checked_in(html_content):
            return True, "Already checked in today"
        
        # 检查是否需要签到
        if not self.is_checkin_page(html_content):
            return False, "Not a checkin page"
        
        # 尝试POST签到
        try:
            checkin_data = {'checkin': '1', 'action': 'checkin', 'daily': '1'}
            
            # 提取CSRF token
            csrf_token = self.extract_csrf_token(html_content)
            if csrf_token:
                checkin_data['_token'] = csrf_token
                checkin_data['csrf_token'] = csrf_token
            
            response = session.post(page_url, data=checkin_data, timeout=30)
            
            if response.status_code == 200:
                return self.check_checkin_response(response.text)
                
        except Exception as e:
            self.logger.debug(f"[{account_name}] POST checkin failed: {str(e)}")
        
        return False, "Failed to perform checkin"
    
    def already_checked_in(self, html_content):
        """检查是否已经签到"""
        content_lower = html_content.lower()
        indicators = [
            'already checked in', '今日已签到', 'checked in today',
            'attendance recorded', '已完成签到', 'completed today'
        ]
        return any(indicator in content_lower for indicator in indicators)
    
    def is_checkin_page(self, html_content):
        """判断是否是签到页面"""
        content_lower = html_content.lower()
        indicators = ['check-in', 'checkin', '签到', 'attendance', 'daily']
        return any(indicator in content_lower for indicator in indicators)
    
    def extract_csrf_token(self, html_content):
        """提取CSRF token"""
        import re
        patterns = [
            r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def check_checkin_response(self, html_content):
        """检查签到响应"""
        content_lower = html_content.lower()
        
        success_indicators = [
            'check-in successful', 'checkin successful', '签到成功',
            'attendance recorded', 'earned reward', '获得奖励',
            'success', '成功', 'completed'
        ]
        
        if any(indicator in content_lower for indicator in success_indicators):
            # 提取奖励信息
            import re
            reward_patterns = [
                r'获得奖励[^\d]*(\d+\.?\d*)\s*元',
                r'earned.*?(\d+\.?\d*)\s*(credits?|points?)',
                r'(\d+\.?\d*)\s*(credits?|points?|元)'
            ]
            
            for pattern in reward_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    reward = match.group(1)
                    return True, f"Check-in successful! Earned {reward} credits"
            
            return True, "Check-in successful!"
        
        return False, "Checkin response indicates failure"
    
    def perform_token_checkin(self, account_data, account_name):
        """使用token执行签到"""
        if 'token_data' not in account_data:
            return False, "No token data found in account configuration"
        
        try:
            session = self.create_session(account_data['token_data'])
            
            # 测试认证
            auth_result = self.test_authentication(session, account_name)
            if not auth_result[0]:
                return False, f"Authentication failed: {auth_result[1]}"
            
            # 执行签到
            return self.perform_checkin(session, account_name)
            
        except Exception as e:
            return False, f"Token checkin error: {str(e)}"
    
    def run_all_accounts(self):
        """为所有账号执行token签到"""
        self.logger.info("=" * 60)
        self.logger.info("🔑 Leaflow Token-Based Auto Check-in Started")
        self.logger.info("=" * 60)
        success_count = 0
        total_count = 0
        results = []
        
        for account_index, account in enumerate(self.config['accounts']):
            if not account.get('enabled', True):
                self.logger.info(f"⏭️ Skipping disabled account: Account{account_index+1}")
                continue
                
            total_count += 1
            account_name = f"账号{account_index + 1}"
            self.logger.info(f"\n📋 正在处理 {account_name}...")
            
            success, message = self.perform_token_checkin(account, account_name)
            results.append({
                'account': account_name,
                'success': success,
                'message': message,
            })
            
            if success:
                self.logger.info(f"✅ [{account_name}] {message}")
                success_count += 1
            else:
                self.logger.error(f"❌ [{account_name}] {message}")
            
            # 账号间延迟
            if account_index < len(self.config['accounts']) - 1:
                delay = self.config['settings'].get('retry_delay', 5)
                self.logger.info(f"⏱️ Waiting {delay} seconds before next account...")
                time.sleep(delay)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"🏁 Token check-in completed: {success_count}/{total_count} successful")
        self.logger.info("=" * 60)
        
        return success_count, total_count, results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Leaflow Token-Based Auto Check-in Script')
    parser.add_argument('--config', default='config.accounts.json', help='Configuration file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--notify', action='store_true', help='Enable notification push')
    parser.add_argument('--no-notify', action='store_true', help='Disable notification push')
    
    args = parser.parse_args()
    
    try:
        checkin = LeafLowTokenCheckin(args.config)
        
        if args.debug:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
            checkin.logger.info("🐛 Debug mode enabled")
        
        # 执行签到
        success_count, total_count, results = checkin.run_all_accounts()
        
        # 通知逻辑
        if args.notify or (not args.no_notify):
            try:
                from notify import send
                import os
                import json
                
                # Load notification config if exists
                notify_config = {}
                if os.path.exists('config.notify.json'):
                    with open('config.notify.json', 'r', encoding='utf-8') as f:
                        notify_config = json.load(f)
                
                # 构建通知内容
                title = "Leaflow Token-Based Auto Check-in Results"
                content_lines = [f"Token check-in completed: {success_count}/{total_count} successful\n"]
                
                for result in results:
                    status = "✅" if result['success'] else "❌"
                    content_lines.append(f"{status} {result['account']}: {result['message']}")
                
                content = "\n".join(content_lines)
                send(title, content, **notify_config)
                checkin.logger.info("📱 Notification sent")
                
            except ImportError:
                checkin.logger.warning("⚠️ Notify module not found, skipping notification")
            except Exception as e:
                checkin.logger.error(f"❌ Failed to send notification: {str(e)}")
        
    except KeyboardInterrupt:
        print("\n\n⏸️ User interrupted program")
    except Exception as e:
        print(f"\n\n💥 Program exception: {str(e)}")

if __name__ == "__main__":
    main()
