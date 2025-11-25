#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Manages URL filtering rules in Zscaler Internet Access (ZIA)
Uses Cloud Service API Key authentication
"""

import os
import sys
import logging
import subprocess
import argparse
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import zscaler SDK with proper fallback handling
try:
    from zscaler.oneapi_client import LegacyZIAClient
    logger.info("✅ Successfully imported LegacyZIAClient from zscaler")
except ImportError as e:
    logger.warning(f"⚠️ Import failed: {e}")
    logger.info("📦 Attempting to install zscaler-sdk-python...")
    
    try:
        # Install the SDK using the current Python interpreter
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "zscaler-sdk-python", "--upgrade", "--quiet"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("✅ Successfully installed zscaler-sdk-python")
        
        # Try importing again after installation
        from zscaler.oneapi_client import LegacyZIAClient
        logger.info("✅ Import successful after installation")
            
    except (subprocess.CalledProcessError, ImportError) as install_error:
        logger.error(f"❌ Failed to install or import SDK: {install_error}")
        logger.error("❌ Zscaler SDK not installed. Run: pip install zscaler-sdk-python")
        sys.exit(1)


class ZscalerURLAutomation:
    """Handles Zscaler URL filtering automation operations using Cloud Service API Key"""
    
    def __init__(self):
        """Initialize Zscaler client with Cloud Service API Key from environment variables"""
        self.api_key = os.getenv('ZSCALER_API_KEY')
        self.base_url = os.getenv('ZSCALER_BASE_URL', 'https://zsapi.zscalerbeta.net/api/v1')
        self.cloud = os.getenv('ZSCALER_CLOUD', 'zscalerbeta')
        
        # Validate credentials
        if not self.api_key:
            logger.error("❌ Missing required API key. Set ZSCALER_API_KEY environment variable")
            sys.exit(1)
        
        logger.info(f"🔐 Authenticating to Zscaler using Cloud Service API Key...")
        logger.info(f"📍 Base URL: {self.base_url}")
        logger.info(f"☁️  Cloud: {self.cloud}")
        
        try:
            # Initialize ZIA client with Cloud Service API Key
            config = {
                "apiKey": self.api_key,
                "cloud": self.cloud
            }
            
            self.client = LegacyZIAClient(config)
            logger.info("✅ Authentication successful")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            sys.exit(1)
    
    def list_rules(self, format_type: str = "table") -> None:
        """
        List all URL filtering rules
        
        Args:
            format_type: Output format (table, json, or simple)
        """
        logger.info("📋 Fetching URL filtering rules...")
        
        try:
            rules, _, err = self.client.url_filtering_rules.list_rules()
            
            if err:
                logger.error(f"❌ Error fetching rules: {err}")
                sys.exit(1)
            
            if not rules:
                logger.warning("⚠️ No URL filtering rules found")
                return
            
            logger.info(f"✅ Found {len(rules)} URL filtering rules")
            
            if format_type == "json":
                import json
                print(json.dumps(rules, indent=2, default=str))
            elif format_type == "simple":
                for rule in rules:
                    print(f"{rule.get('id')} - {rule.get('name')} - {rule.get('action', 'N/A')}")
            else:  # table format
                print("\n" + "="*120)
                print(f"{'ID':<10} {'Rule Name':<40} {'Action':<15} {'State':<10} {'Order':<8}")
                print("="*120)
                for rule in rules:
                    rule_id = rule.get('id', 'N/A')
                    name = rule.get('name', 'N/A')[:38]
                    action = rule.get('action', 'N/A')
                    state = rule.get('state', 'N/A')
                    order = rule.get('order', 'N/A')
                    print(f"{rule_id:<10} {name:<40} {action:<15} {state:<10} {order:<8}")
                print("="*120 + "\n")
                
        except Exception as e:
            logger.error(f"❌ Failed to list rules: {e}")
            sys.exit(1)
    
    def get_rule_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by its name
        
        Args:
            rule_name: Name of the rule to find
            
        Returns:
            Rule dictionary if found, None otherwise
        """
        try:
            rules, _, err = self.client.url_filtering_rules.list_rules()
            
            if err:
                logger.error(f"❌ Error fetching rules: {err}")
                return None
            
            for rule in rules:
                if rule.get('name') == rule_name or str(rule.get('id')) == rule_name:
                    return rule
            
            logger.error(f"❌ Rule '{rule_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get rule: {e}")
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
        logger.info(f"➕ Adding category {category_id} to rule '{rule_name}'...")
        
        # Get the rule
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        try:
            rule_id = rule['id']
            current_categories = rule.get('urlCategories', [])
            
            # Check if category already exists
            if category_id in current_categories:
                logger.warning(f"⚠️ Category {category_id} already exists in rule '{rule_name}'")
                return True
            
            # Add the new category
            updated_categories = current_categories + [category_id]
            
            # Update the rule
            update_data = {
                'urlCategories': updated_categories
            }
            
            _, _, err = self.client.url_filtering_rules.update_rule(
                rule_id=rule_id,
                **update_data
            )
            
            if err:
                logger.error(f"❌ Failed to update rule: {err}")
                return False
            
            logger.info(f"✅ Successfully added category {category_id} to rule '{rule_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add category: {e}")
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
        
        try:
            rule_id = rule['id']
            current_urls = rule.get('blockOverride', [])
            
            # Check if URL already exists
            if url in current_urls:
                logger.warning(f"⚠️ URL '{url}' is already blocked in rule '{rule_name}'")
                return True
            
            # Add the new URL
            updated_urls = current_urls + [url]
            
            # Update the rule
            update_data = {
                'blockOverride': updated_urls
            }
            
            _, _, err = self.client.url_filtering_rules.update_rule(
                rule_id=rule_id,
                **update_data
            )
            
            if err:
                logger.error(f"❌ Failed to update rule: {err}")
                return False
            
            logger.info(f"✅ Successfully blocked URL '{url}' in rule '{rule_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to block URL: {e}")
            return False
    
    def update_rule_action(self, rule_name: str, action: str) -> bool:
        """
        Update the action of a rule
        
        Args:
            rule_name: Name or ID of the rule
            action: New action (ALLOW, BLOCK, CAUTION, etc.)
            
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
        
        try:
            rule_id = rule['id']
            
            # Update the rule action
            update_data = {
                'action': action.upper()
            }
            
            _, _, err = self.client.url_filtering_rules.update_rule(
                rule_id=rule_id,
                **update_data
            )
            
            if err:
                logger.error(f"❌ Failed to update rule: {err}")
                return False
            
            logger.info(f"✅ Successfully updated rule '{rule_name}' action to '{action}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule action: {e}")
            return False


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation (Cloud Service API Key)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all rules in table format
  python zscaler_url_automation.py --list-rules
  
  # List all rules in JSON format
  python zscaler_url_automation.py --list-rules --format json
  
  # Add a category to a rule
  python zscaler_url_automation.py --rule-name "Block Social Media" --add-category "SOCIAL_NETWORKING"
  
  # Block a specific URL in a rule
  python zscaler_url_automation.py --rule-name "Block Malicious Sites" --block-url "bad-site.com"
  
  # Update rule action
  python zscaler_url_automation.py --rule-name "Test Rule" --update-action BLOCK

Environment Variables Required:
  ZSCALER_API_KEY    - Your Cloud Service API Key
  ZSCALER_BASE_URL   - API base URL (default: https://zsapi.zscalerbeta.net/api/v1)
        """
    )
    
    # Operation flags
    parser.add_argument('--list-rules', action='store_true', 
                       help='List all URL filtering rules')
    parser.add_argument('--format', choices=['table', 'json', 'simple'], 
                       default='table',
                       help='Output format for list operation (default: table)')
    
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
    if not any([args.list_rules, args.add_category, args.block_url, args.update_action]):
        parser.error("No operation specified. Use --list-rules, --add-category, --block-url, or --update-action")
    
    if (args.add_category or args.block_url or args.update_action) and not args.rule_name:
        parser.error("--rule-name is required for add-category, block-url, and update-action operations")
    
    # Initialize automation
    automation = ZscalerURLAutomation()
    
    # Execute operations
    success = True
    
    if args.list_rules:
        automation.list_rules(format_type=args.format)
    
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
