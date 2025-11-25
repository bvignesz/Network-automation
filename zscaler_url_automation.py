#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Purpose: List rules, update policies, add URLs, generate reports
Author: Network Automation Team
Version: 2.2
Cloud: zscalerbeta (sandbox/test)
API Base: zsapi.zscalerbeta.net/api/v1
"""

import os
import sys
import json
import csv
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def install_zscaler_sdk():
    """Attempt to install Zscaler SDK if not present"""
    logger.info("📦 Attempting to install zscaler-sdk-python...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "zscaler-sdk-python", "--quiet", "--user"
        ])
        logger.info("✅ Successfully installed zscaler-sdk-python")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install SDK: {e}")
        return False


# Try to import Zscaler SDK, install if missing
try:
    from zscaler.zia import ZIAClientHelper
    SDK_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Zscaler SDK not found, attempting to install...")
    if install_zscaler_sdk():
        try:
            from zscaler.zia import ZIAClientHelper
            SDK_AVAILABLE = True
        except ImportError:
            logger.error("❌ Zscaler SDK installation failed. Please run: pip install zscaler-sdk-python")
            SDK_AVAILABLE = False
    else:
        SDK_AVAILABLE = False


# ==========================================
# Zscaler Cloud Configuration
# ==========================================
ZSCALER_CLOUDS = {
    'zscaler': 'zsapi.zscaler.net',
    'zscalerone': 'zsapi.zscalerone.net',
    'zscalertwo': 'zsapi.zscalertwo.net',
    'zscalerthree': 'zsapi.zscalerthree.net',
    'zscloud': 'zsapi.zscloud.net',
    'zscalerbeta': 'zsapi.zscalerbeta.net',
    'zscalergov': 'zsapi.zscalergov.net',
}


class ZscalerAutomation:
    """Main class for Zscaler URL filtering automation"""
    
    def __init__(self):
        """Initialize Zscaler client with environment variables"""
        if not SDK_AVAILABLE:
            logger.error("❌ Cannot initialize: Zscaler SDK not available")
            sys.exit(1)
            
        self.username = os.getenv('ZSCALER_USERNAME')
        self.password = os.getenv('ZSCALER_PASSWORD')
        self.api_key = os.getenv('ZSCALER_API_KEY')
        self.cloud = os.getenv('ZSCALER_CLOUD', 'zscalerbeta')
        
        self._validate_credentials()
        self._validate_cloud()
        self.client = self._initialize_client()
        
    def _validate_credentials(self):
        """Validate all required environment variables are set"""
        missing = []
        if not self.username:
            missing.append('ZSCALER_USERNAME')
        if not self.password:
            missing.append('ZSCALER_PASSWORD')
        if not self.api_key:
            missing.append('ZSCALER_API_KEY')
            
        if missing:
            logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
            logger.error("Set them in Semaphore Environment or export them")
            sys.exit(1)
    
    def _validate_cloud(self):
        """Validate cloud name is supported"""
        if self.cloud not in ZSCALER_CLOUDS:
            logger.error(f"❌ Invalid cloud '{self.cloud}'")
            logger.error(f"   Supported clouds: {', '.join(ZSCALER_CLOUDS.keys())}")
            sys.exit(1)
        logger.info(f"☁️  Cloud: {self.cloud}")
        logger.info(f"🌐 API Base: {ZSCALER_CLOUDS[self.cloud]}/api/v1")
            
    def _initialize_client(self):
        """Initialize and authenticate Zscaler client"""
        try:
            logger.info(f"🔐 Connecting to Zscaler cloud: {self.cloud}")
            client = ZIAClientHelper(
                username=self.username,
                password=self.password,
                api_key=self.api_key,
                cloud=self.cloud
            )
            logger.info("✅ Successfully authenticated with Zscaler API")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to authenticate: {str(e)}")
            logger.error(f"   Cloud: {self.cloud}")
            logger.error(f"   Username: {self.username}")
            logger.error(f"   API Endpoint: {ZSCALER_CLOUDS.get(self.cloud, 'unknown')}")
            sys.exit(1)
            
    def list_all_rules(self, output_format: str = 'table') -> List[Dict]:
        """List all URL filtering rules with their status"""
        try:
            logger.info("📋 Fetching all URL filtering rules...")
            rules, response, error = self.client.url_filtering.list_rules()
            
            if error:
                logger.error(f"❌ Error fetching rules: {error}")
                return []
                
            if not rules:
                logger.warning("⚠️  No URL filtering rules found")
                return []
                
            logger.info(f"✅ Found {len(rules)} URL filtering rules")
            
            rules_data = []
            for rule in rules:
                rule_info = {
                    'id': rule.id,
                    'name': rule.name,
                    'state': rule.state,
                    'action': rule.action,
                    'order': rule.order,
                    'rank': getattr(rule, 'rank', 'N/A'),
                    'description': rule.description or 'N/A',
                    'url_categories': ', '.join(rule.url_categories) if rule.url_categories else 'N/A',
                    'protocols': ', '.join(rule.protocols) if rule.protocols else 'N/A',
                    'locations': len(rule.locations) if rule.locations else 0,
                    'groups': len(rule.groups) if rule.groups else 0,
                    'users': len(rule.users) if rule.users else 0,
                }
                rules_data.append(rule_info)
                
            rules_data.sort(key=lambda x: x['order'])
            
            if output_format == 'table':
                self._display_table(rules_data)
            elif output_format == 'csv':
                self._export_csv(rules_data)
            elif output_format == 'json':
                self._export_json(rules_data)
                
            return rules_data
            
        except Exception as e:
            logger.error(f"❌ Error listing rules: {str(e)}")
            return []
            
    def _display_table(self, rules_data: List[Dict]):
        """Display rules in formatted table"""
        if not rules_data:
            return
            
        print("\n" + "="*150)
        print(f"{'ID':<10} {'Name':<30} {'State':<10} {'Action':<10} {'Order':<6} {'URL Categories':<40} {'Description':<30}")
        print("="*150)
        
        for rule in rules_data:
            name = str(rule['name'])[:28] + '..' if len(str(rule['name'])) > 30 else rule['name']
            categories = str(rule['url_categories'])[:38] + '..' if len(str(rule['url_categories'])) > 40 else rule['url_categories']
            desc = str(rule['description'])[:28] + '..' if len(str(rule['description'])) > 30 else rule['description']
            
            print(f"{rule['id']:<10} {name:<30} {rule['state']:<10} {rule['action']:<10} "
                  f"{rule['order']:<6} {categories:<40} {desc:<30}")
                  
        print("="*150)
        print(f"\n📊 Total Rules: {len(rules_data)}")
        print(f"✅ Enabled: {sum(1 for r in rules_data if r['state'] == 'ENABLED')}")
        print(f"❌ Disabled: {sum(1 for r in rules_data if r['state'] == 'DISABLED')}")
        
    def _export_csv(self, rules_data: List[Dict]):
        """Export rules to CSV file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reports/zscaler_rules_{timestamp}.csv"
        
        os.makedirs('reports', exist_ok=True)
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                if rules_data:
                    writer = csv.DictWriter(csvfile, fieldnames=rules_data[0].keys())
                    writer.writeheader()
                    writer.writerows(rules_data)
                    
            logger.info(f"✅ CSV report exported: {filename}")
            print(f"\n📄 Report saved: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error exporting CSV: {str(e)}")
            
    def _export_json(self, rules_data: List[Dict]):
        """Export rules to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reports/zscaler_rules_{timestamp}.json"
        
        os.makedirs('reports', exist_ok=True)
        
        try:
            with open(filename, 'w') as jsonfile:
                json.dump({
                    'cloud': self.cloud,
                    'api_base': ZSCALER_CLOUDS[self.cloud],
                    'exported_at': datetime.now().isoformat(),
                    'total_rules': len(rules_data),
                    'rules': rules_data
                }, jsonfile, indent=2)
                
            logger.info(f"✅ JSON report exported: {filename}")
            print(f"\n📄 Report saved: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error exporting JSON: {str(e)}")
            
    def find_rule_by_name(self, rule_name: str) -> Optional[object]:
        """Find a specific rule by name"""
        try:
            rules, response, error = self.client.url_filtering.list_rules(
                query_params={'search': rule_name}
            )
            
            if error or not rules:
                logger.warning(f"⚠️  Rule '{rule_name}' not found")
                return None
                
            for rule in rules:
                if rule.name.lower() == rule_name.lower():
                    logger.info(f"✅ Found rule: {rule.name} (ID: {rule.id})")
                    return rule
            
            if len(rules) > 1:
                logger.warning(f"⚠️  Multiple rules found matching '{rule_name}'. Using first match.")
                
            rule = rules[0]
            logger.info(f"✅ Found rule: {rule.name} (ID: {rule.id})")
            return rule
            
        except Exception as e:
            logger.error(f"❌ Error finding rule: {str(e)}")
            return None
            
    def add_url_category_to_rule(self, rule_name: str, url_category: str) -> bool:
        """Add a URL category to an existing rule"""
        try:
            rule = self.find_rule_by_name(rule_name)
            if not rule:
                return False
                
            current_categories = rule.url_categories or []
            
            if url_category in current_categories:
                logger.warning(f"⚠️  Category '{url_category}' already exists in rule '{rule_name}'")
                return True
                
            updated_categories = current_categories + [url_category]
            
            logger.info(f"📝 Adding category '{url_category}' to rule '{rule_name}'")
            
            updated_rule, response, error = self.client.url_filtering.update_rule(
                rule_id=str(rule.id),
                url_categories=updated_categories
            )
            
            if error:
                logger.error(f"❌ Error updating rule: {error}")
                return False
                
            logger.info(f"✅ Successfully added category to rule '{rule_name}'")
            logger.info(f"   Previous categories: {', '.join(current_categories)}")
            logger.info(f"   Updated categories: {', '.join(updated_categories)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding URL category: {str(e)}")
            return False
            
    def block_url_in_rule(self, rule_name: str, url_to_block: str) -> bool:
        """Block a specific URL by updating rule action"""
        try:
            logger.info(f"🚫 Attempting to block URL: {url_to_block}")
            logger.info(f"📝 Target rule: {rule_name}")
            
            rule = self.find_rule_by_name(rule_name)
            if not rule:
                logger.error(f"❌ Cannot proceed without finding the rule")
                return False
                
            logger.info(f"ℹ️  Note: Zscaler rules use URL categories, not individual URLs")
            logger.info(f"ℹ️  Consider using Custom URL Categories to block specific domains")
            
            if rule.action != 'BLOCK':
                logger.info(f"📝 Changing rule action to BLOCK")
                updated_rule, response, error = self.client.url_filtering.update_rule(
                    rule_id=str(rule.id),
                    action='BLOCK'
                )
                
                if error:
                    logger.error(f"❌ Error updating rule: {error}")
                    return False
                    
                logger.info(f"✅ Rule '{rule_name}' action set to BLOCK")
            else:
                logger.info(f"ℹ️  Rule already set to BLOCK")
                
            logger.warning(f"⚠️  Manual step required to block specific URL:")
            logger.warning(f"   1. Go to Zscaler Admin > URL & Cloud App Control > Custom Categories")
            logger.warning(f"   2. Add '{url_to_block}' to a custom category")
            logger.warning(f"   3. Assign that category to rule '{rule_name}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error blocking URL: {str(e)}")
            return False
            
    def update_rule_action(self, rule_name: str, action: str) -> bool:
        """Update the action of a rule"""
        valid_actions = ['ALLOW', 'BLOCK', 'CAUTION', 'NONE', 'ICAP_RESPONSE']
        
        if action.upper() not in valid_actions:
            logger.error(f"❌ Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
            return False
            
        try:
            rule = self.find_rule_by_name(rule_name)
            if not rule:
                return False
                
            logger.info(f"📝 Updating rule '{rule_name}' action to '{action}'")
            
            updated_rule, response, error = self.client.url_filtering.update_rule(
                rule_id=str(rule.id),
                action=action.upper()
            )
            
            if error:
                logger.error(f"❌ Error updating rule: {error}")
                return False
                
            logger.info(f"✅ Rule action updated successfully")
            logger.info(f"   Previous action: {rule.action}")
            logger.info(f"   New action: {action.upper()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating rule action: {str(e)}")
            return False


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation Tool (Beta Cloud)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cloud: zscalerbeta (zsapi.zscalerbeta.net/api/v1)

Examples:
  python zscaler_url_automation.py --list-rules
  python zscaler_url_automation.py --list-rules --format csv
  python zscaler_url_automation.py --rule-name "Block Social Media" --add-category "STREAMING_MEDIA"
  python zscaler_url_automation.py --rule-name "Allow Finance" --action ALLOW
  python zscaler_url_automation.py --rule-name "Block Malicious" --block-url "badsite.com"
        """
    )
    
    parser.add_argument('--list-rules', action='store_true',
                        help='List all URL filtering rules')
    parser.add_argument('--format', choices=['table', 'csv', 'json'], default='table',
                        help='Output format for listing rules (default: table)')
    
    parser.add_argument('--rule-name', type=str,
                        help='Name of the rule to operate on')
    parser.add_argument('--add-category', type=str,
                        help='URL category to add to the rule')
    parser.add_argument('--block-url', type=str,
                        help='URL to block (requires custom category setup)')
    parser.add_argument('--action', type=str, choices=['ALLOW', 'BLOCK', 'CAUTION'],
                        help='Update rule action')
    
    args = parser.parse_args()
    
    # Check SDK availability before proceeding
    if not SDK_AVAILABLE:
        logger.error("❌ Zscaler SDK not installed. Run: pip install zscaler-sdk-python")
        sys.exit(1)
    
    # Initialize automation client
    zscaler = ZscalerAutomation()
    
    success = True
    
    if args.list_rules or (not any([args.add_category, args.block_url, args.action])):
        zscaler.list_all_rules(output_format=args.format)
        
    if args.rule_name:
        if args.add_category:
            success = zscaler.add_url_category_to_rule(args.rule_name, args.add_category)
            
        if args.block_url:
            success = zscaler.block_url_in_rule(args.rule_name, args.block_url)
            
        if args.action:
            success = zscaler.update_rule_action(args.rule_name, args.action)
            
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
