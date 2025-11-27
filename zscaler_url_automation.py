#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Uses Official zscaler-sdk-python with Native Authentication

This script requires the following environment variables:
  ZIA_USERNAME  - Your ZIA admin username (email)
  ZIA_PASSWORD  - Your ZIA admin password
  ZIA_API_KEY   - Your ZIA API key from Admin Portal
  ZIA_CLOUD     - Your ZIA cloud (e.g., zscalerbeta, zscaler, zscalerone, etc.)

Install: pip install zscaler-sdk-python
"""

import os
import sys
import logging
import argparse
import json
from typing import Optional, Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        from zscaler.zia import ZIAClientHelper
        return True
    except ImportError:
        logger.error("❌ Missing required package: zscaler-sdk-python")
        logger.error("   Install it with: pip install zscaler-sdk-python")
        return False


class ZscalerURLAutomation:
    """Handles Zscaler URL filtering automation operations using official SDK"""
    
    def __init__(self):
        """Initialize automation with ZIA client using Native Authentication"""
        # Import here to allow dependency check first
        from zscaler.zia import ZIAClientHelper
        
        # Get credentials from environment variables
        self.username = os.environ.get('ZIA_USERNAME')
        self.password = os.environ.get('ZIA_PASSWORD')
        self.api_key = os.environ.get('ZIA_API_KEY')
        self.cloud = os.environ.get('ZIA_CLOUD', 'zscalerbeta')
        
        # Validate credentials
        missing_creds = []
        if not self.username:
            missing_creds.append('ZIA_USERNAME')
        if not self.password:
            missing_creds.append('ZIA_PASSWORD')
        if not self.api_key:
            missing_creds.append('ZIA_API_KEY')
        
        if missing_creds:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_creds)}")
            logger.error("")
            logger.error("Please set the following environment variables:")
            logger.error("  export ZIA_USERNAME='your_admin_email@company.com'")
            logger.error("  export ZIA_PASSWORD='your_password'")
            logger.error("  export ZIA_API_KEY='your_api_key_from_admin_portal'")
            logger.error("  export ZIA_CLOUD='zscalerbeta'  # or your cloud name")
            sys.exit(1)
        
        logger.info("🔐 Initializing Zscaler ZIA client...")
        logger.info(f"📍 Cloud: {self.cloud}")
        logger.info(f"👤 Username: {self.username}")
        logger.info(f"🔑 API Key length: {len(self.api_key)}")
        
        try:
            # Initialize ZIA client with Native Authentication
            # The SDK handles the API key obfuscation and session management automatically
            self.client = ZIAClientHelper(
                username=self.username,
                password=self.password,
                api_key=self.api_key,
                cloud=self.cloud
            )
            logger.info("✅ Successfully authenticated to Zscaler ZIA API")
            
        except Exception as e:
            logger.error(f"❌ Failed to authenticate to Zscaler ZIA API: {e}")
            logger.error("")
            logger.error("Common issues:")
            logger.error("  1. Invalid credentials - verify username/password in ZIA Admin Portal")
            logger.error("  2. API key incorrect - get it from Administration → API Key Management")
            logger.error("  3. Wrong cloud name - check your admin portal URL")
            logger.error("  4. API access not enabled for your admin account")
            sys.exit(1)
    
    def list_rules(self, format_type: str = "table") -> None:
        """
        List all URL filtering rules
        
        Args:
            format_type: Output format (table, json, or simple)
        """
        logger.info("📋 Fetching URL filtering rules...")
        
        try:
            # Use the SDK's url_filtering interface
            rules = self.client.url_filtering.list_rules()
            
            if not rules:
                logger.warning("⚠️ No URL filtering rules found")
                return
            
            # Convert BoxList to regular list if needed
            rules_list = list(rules) if hasattr(rules, '__iter__') else [rules]
            
            logger.info(f"✅ Found {len(rules_list)} URL filtering rules")
            
            if format_type == "json":
                # Convert to serializable format
                output = []
                for rule in rules_list:
                    if hasattr(rule, 'to_dict'):
                        output.append(rule.to_dict())
                    elif hasattr(rule, 'as_dict'):
                        output.append(rule.as_dict())
                    elif isinstance(rule, dict):
                        output.append(rule)
                    else:
                        output.append(dict(rule))
                print(json.dumps(output, indent=2, default=str))
                
            elif format_type == "simple":
                for rule in rules_list:
                    rule_id = getattr(rule, 'id', rule.get('id', 'N/A') if isinstance(rule, dict) else 'N/A')
                    name = getattr(rule, 'name', rule.get('name', 'N/A') if isinstance(rule, dict) else 'N/A')
                    action = getattr(rule, 'action', rule.get('action', 'N/A') if isinstance(rule, dict) else 'N/A')
                    print(f"{rule_id} - {name} - {action}")
                    
            else:  # table format
                print("\n" + "="*120)
                print(f"{'ID':<10} {'Rule Name':<40} {'Action':<15} {'State':<10} {'Order':<8}")
                print("="*120)
                
                for rule in rules_list:
                    # Handle both object and dict access patterns
                    if isinstance(rule, dict):
                        rule_id = str(rule.get('id', 'N/A'))
                        name = str(rule.get('name', 'N/A'))[:38]
                        action = str(rule.get('action', 'N/A'))
                        state = str(rule.get('state', 'N/A'))
                        order = str(rule.get('order', 'N/A'))
                    else:
                        rule_id = str(getattr(rule, 'id', 'N/A'))
                        name = str(getattr(rule, 'name', 'N/A'))[:38]
                        action = str(getattr(rule, 'action', 'N/A'))
                        state = str(getattr(rule, 'state', 'N/A'))
                        order = str(getattr(rule, 'order', 'N/A'))
                    
                    print(f"{rule_id:<10} {name:<40} {action:<15} {state:<10} {order:<8}")
                
                print("="*120 + "\n")
                
        except Exception as e:
            logger.error(f"❌ Failed to list rules: {e}")
            sys.exit(1)
    
    def get_rule_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by its name or ID
        
        Args:
            rule_name: Name or ID of the rule
            
        Returns:
            Rule dictionary if found, None otherwise
        """
        try:
            rules = self.client.url_filtering.list_rules()
            
            for rule in rules:
                # Handle both object and dict access
                if isinstance(rule, dict):
                    r_name = rule.get('name', '')
                    r_id = str(rule.get('id', ''))
                else:
                    r_name = getattr(rule, 'name', '')
                    r_id = str(getattr(rule, 'id', ''))
                
                if r_name == rule_name or r_id == rule_name:
                    # Convert to dict for consistent handling
                    if hasattr(rule, 'to_dict'):
                        return rule.to_dict()
                    elif hasattr(rule, 'as_dict'):
                        return rule.as_dict()
                    elif isinstance(rule, dict):
                        return rule
                    else:
                        return dict(rule)
            
            logger.error(f"❌ Rule '{rule_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get rules: {e}")
            return None
    
    def add_category_to_rule(self, rule_name: str, category_id: str) -> bool:
        """
        Add a URL category to a rule
        
        Args:
            rule_name: Name or ID of the rule
            category_id: Category ID to add
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"➕ Adding category '{category_id}' to rule '{rule_name}'...")
        
        # Get the rule
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule['id']
        current_categories = rule.get('urlCategories', [])
        
        # Check if category already exists
        if category_id in current_categories:
            logger.warning(f"⚠️ Category '{category_id}' already exists in rule '{rule_name}'")
            return True
        
        # Add the new category
        new_categories = current_categories + [category_id]
        
        try:
            # Update the rule using SDK
            self.client.url_filtering.update_rule(
                rule_id=rule_id,
                url_categories=new_categories
            )
            logger.info(f"✅ Successfully added category '{category_id}' to rule '{rule_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def block_url_in_rule(self, rule_name: str, url: str) -> bool:
        """
        Add a URL to the block list of a rule
        
        Args:
            rule_name: Name or ID of the rule
            url: URL to block
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"🚫 Blocking URL '{url}' in rule '{rule_name}'...")
        
        # Get the rule
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule['id']
        current_urls = rule.get('blockOverride', [])
        
        # Check if URL already exists
        if url in current_urls:
            logger.warning(f"⚠️ URL '{url}' is already blocked in rule '{rule_name}'")
            return True
        
        # Add the new URL
        new_urls = current_urls + [url]
        
        try:
            # Update the rule using SDK
            self.client.url_filtering.update_rule(
                rule_id=rule_id,
                block_override=new_urls
            )
            logger.info(f"✅ Successfully blocked URL '{url}' in rule '{rule_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def update_rule_action(self, rule_name: str, action: str) -> bool:
        """
        Update the action of a rule
        
        Args:
            rule_name: Name or ID of the rule
            action: New action (ALLOW, BLOCK, CAUTION, ISOLATE)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"🔄 Updating rule '{rule_name}' action to '{action}'...")
        
        # Validate action
        valid_actions = ['ALLOW', 'BLOCK', 'CAUTION', 'ISOLATE']
        if action.upper() not in valid_actions:
            logger.error(f"❌ Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
            return False
        
        # Get the rule
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule['id']
        
        try:
            # Update the rule using SDK
            self.client.url_filtering.update_rule(
                rule_id=rule_id,
                action=action.upper()
            )
            logger.info(f"✅ Successfully updated rule '{rule_name}' action to '{action}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def list_url_categories(self, format_type: str = "table") -> None:
        """
        List all URL categories
        
        Args:
            format_type: Output format (table, json, or simple)
        """
        logger.info("📋 Fetching URL categories...")
        
        try:
            categories = self.client.url_categories.list_categories()
            
            if not categories:
                logger.warning("⚠️ No URL categories found")
                return
            
            categories_list = list(categories) if hasattr(categories, '__iter__') else [categories]
            
            logger.info(f"✅ Found {len(categories_list)} URL categories")
            
            if format_type == "json":
                output = []
                for cat in categories_list:
                    if hasattr(cat, 'to_dict'):
                        output.append(cat.to_dict())
                    elif hasattr(cat, 'as_dict'):
                        output.append(cat.as_dict())
                    elif isinstance(cat, dict):
                        output.append(cat)
                    else:
                        output.append(dict(cat))
                print(json.dumps(output, indent=2, default=str))
                
            elif format_type == "simple":
                for cat in categories_list:
                    cat_id = getattr(cat, 'id', cat.get('id', 'N/A') if isinstance(cat, dict) else 'N/A')
                    name = getattr(cat, 'configuredName', cat.get('configuredName', 'N/A') if isinstance(cat, dict) else 'N/A')
                    print(f"{cat_id} - {name}")
                    
            else:  # table format
                print("\n" + "="*100)
                print(f"{'ID':<30} {'Category Name':<50} {'Type':<20}")
                print("="*100)
                
                for cat in categories_list:
                    if isinstance(cat, dict):
                        cat_id = str(cat.get('id', 'N/A'))
                        name = str(cat.get('configuredName', cat.get('id', 'N/A')))[:48]
                        cat_type = str(cat.get('superCategory', cat.get('type', 'N/A')))
                    else:
                        cat_id = str(getattr(cat, 'id', 'N/A'))
                        name = str(getattr(cat, 'configuredName', getattr(cat, 'id', 'N/A')))[:48]
                        cat_type = str(getattr(cat, 'superCategory', getattr(cat, 'type', 'N/A')))
                    
                    print(f"{cat_id:<30} {name:<50} {cat_type:<20}")
                
                print("="*100 + "\n")
                
        except Exception as e:
            logger.error(f"❌ Failed to list categories: {e}")
            sys.exit(1)


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation (Official SDK)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all URL filtering rules in table format
  python zscaler_url_automation.py --list-rules
  
  # List all rules in JSON format
  python zscaler_url_automation.py --list-rules --format json
  
  # List all URL categories
  python zscaler_url_automation.py --list-categories
  
  # Add a category to a rule
  python zscaler_url_automation.py --rule-name "Block Social Media" --add-category "SOCIAL_NETWORKING"
  
  # Block a specific URL in a rule
  python zscaler_url_automation.py --rule-name "Block Malicious Sites" --block-url "bad-site.com"
  
  # Update rule action
  python zscaler_url_automation.py --rule-name "Test Rule" --update-action BLOCK

Environment Variables Required:
  ZIA_USERNAME   - Your ZIA admin username (email)
  ZIA_PASSWORD   - Your ZIA admin password
  ZIA_API_KEY    - Your ZIA API key from Administration → API Key Management
  ZIA_CLOUD      - Your ZIA cloud name (default: zscalerbeta)
                   Options: zscalerbeta, zscaler, zscalerone, zscalertwo, zscalerthree, zscloud

Cloud Name Reference (based on your admin portal URL):
  admin.zscalerbeta.net  → ZIA_CLOUD=zscalerbeta
  admin.zscaler.net      → ZIA_CLOUD=zscaler
  admin.zscalerone.net   → ZIA_CLOUD=zscalerone
  admin.zscalertwo.net   → ZIA_CLOUD=zscalertwo
  admin.zscalerthree.net → ZIA_CLOUD=zscalerthree
  admin.zscloud.net      → ZIA_CLOUD=zscloud
        """
    )
    
    # Operation flags
    parser.add_argument('--list-rules', action='store_true', 
                       help='List all URL filtering rules')
    parser.add_argument('--list-categories', action='store_true',
                       help='List all URL categories')
    parser.add_argument('--format', choices=['table', 'json', 'simple'], 
                       default='table',
                       help='Output format for list operations (default: table)')
    
    # Rule operations
    parser.add_argument('--rule-name', type=str,
                       help='Rule name or ID for operations')
    parser.add_argument('--add-category', type=str,
                       help='Add a URL category to the specified rule')
    parser.add_argument('--block-url', type=str,
                       help='Block a URL in the specified rule')
    parser.add_argument('--update-action', type=str,
                       choices=['ALLOW', 'BLOCK', 'CAUTION', 'ISOLATE'],
                       help='Update the action of the specified rule')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.list_rules, args.list_categories, args.add_category, args.block_url, args.update_action]):
        parser.error("No operation specified. Use --list-rules, --list-categories, --add-category, --block-url, or --update-action")
    
    if (args.add_category or args.block_url or args.update_action) and not args.rule_name:
        parser.error("--rule-name is required for add-category, block-url, and update-action operations")
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Initialize automation
    automation = ZscalerURLAutomation()
    
    # Execute operations
    success = True
    
    if args.list_rules:
        automation.list_rules(format_type=args.format)
    
    if args.list_categories:
        automation.list_url_categories(format_type=args.format)
    
    if args.add_category:
        success = automation.add_category_to_rule(args.rule_name, args.add_category)
    
    if args.block_url:
        success = automation.block_url_in_rule(args.rule_name, args.block_url)
    
    if args.update_action:
        success = automation.update_rule_action(args.rule_name, args.update_action)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
