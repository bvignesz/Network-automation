#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Uses Official zscaler-sdk-python with LegacyZIAClient (for non-Zidentity tenants)

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


def get_zia_client():
    """
    Get ZIA client - tries multiple import paths for compatibility
    Returns the appropriate client class and type
    """
    # Try newer SDK first (v1.0+) - LegacyZIAClient
    try:
        from zscaler.oneapi_client import LegacyZIAClient
        logger.info("📦 Using zscaler-sdk-python (LegacyZIAClient)")
        return LegacyZIAClient, "legacy"
    except ImportError:
        pass
    
    # Try older SDK import path
    try:
        from zscaler.zia import ZIAClientHelper
        logger.info("📦 Using zscaler-sdk-python (ZIAClientHelper from zscaler.zia)")
        return ZIAClientHelper, "helper"
    except ImportError:
        pass
    
    # Try direct import
    try:
        from zscaler import ZIAClientHelper
        logger.info("📦 Using zscaler-sdk-python (ZIAClientHelper direct)")
        return ZIAClientHelper, "helper"
    except ImportError:
        pass
    
    logger.error("❌ Could not import Zscaler SDK")
    logger.error("   Install with: pip install zscaler-sdk-python")
    return None, None


class ZscalerURLAutomation:
    """Handles Zscaler URL filtering automation operations using official SDK"""
    
    def __init__(self):
        """Initialize automation with ZIA client using Native Authentication"""
        
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
            sys.exit(1)
        
        logger.info("🔐 Initializing Zscaler ZIA client...")
        logger.info(f"📍 Cloud: {self.cloud}")
        logger.info(f"👤 Username: {self.username}")
        logger.info(f"🔑 API Key length: {len(self.api_key)}")
        
        # Get the appropriate client class
        ClientClass, client_type = get_zia_client()
        
        if ClientClass is None:
            sys.exit(1)
        
        self.client_type = client_type
        self.client = None
        self.zia = None
        
        try:
            if client_type == "legacy":
                # New SDK using LegacyZIAClient with config dict
                config = {
                    "username": self.username,
                    "password": self.password,
                    "api_key": self.api_key,
                    "cloud": self.cloud,
                    "logging": {"enabled": True, "verbose": False}
                }
                self.client = ClientClass(config)
                # Enter the context manager
                self.client.__enter__()
                # Access the ZIA interface through client.zia
                self.zia = self.client.zia
            else:
                # Older SDK using ZIAClientHelper with keyword args
                self.client = ClientClass(
                    username=self.username,
                    password=self.password,
                    api_key=self.api_key,
                    cloud=self.cloud
                )
                self.zia = self.client
            
            logger.info("✅ Successfully authenticated to Zscaler ZIA API")
            
            # Debug: Print available attributes
            if self.zia:
                attrs = [attr for attr in dir(self.zia) if not attr.startswith('_')]
                logger.info(f"📋 Available ZIA interfaces: {', '.join(attrs[:20])}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to authenticate to Zscaler ZIA API: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def __del__(self):
        """Cleanup - exit context manager if using LegacyZIAClient"""
        if hasattr(self, 'client') and self.client and hasattr(self, 'client_type'):
            if self.client_type == "legacy":
                try:
                    self.client.__exit__(None, None, None)
                except:
                    pass
    
    def _get_url_filtering_interface(self):
        """Get the URL filtering interface - handles different SDK versions"""
        # Try different attribute names
        possible_attrs = ['url_filtering', 'url_filtering_rules', 'urlfiltering', 'web_application_rules']
        
        for attr in possible_attrs:
            if hasattr(self.zia, attr):
                logger.info(f"📌 Using URL filtering interface: {attr}")
                return getattr(self.zia, attr)
        
        # If none found, list available attributes
        attrs = [a for a in dir(self.zia) if not a.startswith('_')]
        logger.error(f"❌ Could not find URL filtering interface. Available: {attrs}")
        return None
    
    def list_rules(self, format_type: str = "table") -> None:
        """
        List all URL filtering rules
        
        Args:
            format_type: Output format (table, json, or simple)
        """
        logger.info("📋 Fetching URL filtering rules...")
        
        try:
            url_filtering = self._get_url_filtering_interface()
            if not url_filtering:
                logger.error("❌ URL filtering interface not available")
                sys.exit(1)
            
            # Try to list rules - SDK returns tuple (data, response, error) for legacy client
            result = url_filtering.list_rules()
            
            # Handle different return types
            if isinstance(result, tuple):
                # New SDK returns (data, response, error)
                if len(result) >= 3:
                    rules, response, error = result
                    if error:
                        logger.error(f"❌ API Error: {error}")
                        sys.exit(1)
                else:
                    rules = result[0] if result else []
            else:
                # Old SDK returns data directly
                rules = result
            
            if not rules:
                logger.warning("⚠️ No URL filtering rules found")
                print("\nNo URL filtering rules configured.")
                return
            
            # Ensure we have a list
            if isinstance(rules, dict):
                rules_list = [rules]
            elif hasattr(rules, '__iter__'):
                rules_list = list(rules)
            else:
                rules_list = [rules]
            
            logger.info(f"✅ Found {len(rules_list)} URL filtering rules")
            
            if format_type == "json":
                # Convert to JSON-serializable format
                output = []
                for rule in rules_list:
                    if isinstance(rule, dict):
                        output.append(rule)
                    elif hasattr(rule, 'to_dict'):
                        output.append(rule.to_dict())
                    elif hasattr(rule, '__dict__'):
                        output.append(dict(rule.__dict__))
                    else:
                        output.append(str(rule))
                print(json.dumps(output, indent=2, default=str))
                
            elif format_type == "simple":
                for rule in rules_list:
                    if isinstance(rule, dict):
                        rule_id = rule.get('id', 'N/A')
                        name = rule.get('name', 'N/A')
                        action = rule.get('action', 'N/A')
                    else:
                        rule_id = getattr(rule, 'id', 'N/A')
                        name = getattr(rule, 'name', 'N/A')
                        action = getattr(rule, 'action', 'N/A')
                    print(f"{rule_id} - {name} - {action}")
                    
            else:  # table format
                print("\n" + "="*120)
                print(f"{'ID':<10} {'Rule Name':<40} {'Action':<15} {'State':<10} {'Order':<8}")
                print("="*120)
                
                for rule in rules_list:
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
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def get_rule_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by its name or ID
        """
        try:
            url_filtering = self._get_url_filtering_interface()
            if not url_filtering:
                return None
            
            result = url_filtering.list_rules()
            
            # Handle tuple return
            if isinstance(result, tuple):
                rules = result[0] if result else []
                if len(result) >= 3 and result[2]:
                    logger.error(f"❌ API Error: {result[2]}")
                    return None
            else:
                rules = result
            
            for rule in rules:
                if isinstance(rule, dict):
                    r_name = rule.get('name', '')
                    r_id = str(rule.get('id', ''))
                else:
                    r_name = getattr(rule, 'name', '')
                    r_id = str(getattr(rule, 'id', ''))
                
                if r_name == rule_name or r_id == rule_name:
                    if isinstance(rule, dict):
                        return rule
                    elif hasattr(rule, 'to_dict'):
                        return rule.to_dict()
                    else:
                        return dict(rule) if hasattr(rule, '__iter__') else {'id': r_id, 'name': r_name}
            
            logger.error(f"❌ Rule '{rule_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get rules: {e}")
            return None
    
    def add_category_to_rule(self, rule_name: str, category_id: str) -> bool:
        """Add a URL category to a rule"""
        logger.info(f"➕ Adding category '{category_id}' to rule '{rule_name}'...")
        
        url_filtering = self._get_url_filtering_interface()
        if not url_filtering:
            return False
        
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule.get('id') if isinstance(rule, dict) else getattr(rule, 'id', None)
        current_categories = rule.get('urlCategories', []) if isinstance(rule, dict) else getattr(rule, 'urlCategories', [])
        
        if category_id in current_categories:
            logger.warning(f"⚠️ Category '{category_id}' already exists in rule '{rule_name}'")
            return True
        
        new_categories = list(current_categories) + [category_id]
        
        try:
            result = url_filtering.update_rule(rule_id=rule_id, url_categories=new_categories)
            
            if isinstance(result, tuple) and len(result) >= 3 and result[2]:
                logger.error(f"❌ API Error: {result[2]}")
                return False
            
            logger.info(f"✅ Successfully added category '{category_id}' to rule '{rule_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def block_url_in_rule(self, rule_name: str, url: str) -> bool:
        """
        Block a URL by adding it to a custom URL category and associating with a rule.
        
        The correct Zscaler workflow is:
        1. Create or find a custom URL category (e.g., "Blocked URLs - Automation")
        2. Add the URL to that custom category
        3. Add that category to the URL filtering rule
        """
        logger.info(f"🚫 Blocking URL '{url}' via custom URL category...")
        
        # Step 1: Get or create a custom URL category for blocked URLs
        category_name = "Blocked_URLs_Automation"
        category_id = self._get_or_create_block_category(category_name)
        
        if not category_id:
            logger.error("❌ Failed to get or create block category")
            return False
        
        # Step 2: Add the URL to the custom category
        if not self._add_url_to_category(category_id, url):
            return False
        
        # Step 3: Add the category to the rule (if not already there)
        if rule_name:
            if not self._add_category_to_rule(rule_name, category_id):
                return False
        
        logger.info(f"✅ Successfully blocked URL '{url}'")
        return True
    
    def _get_or_create_block_category(self, category_name: str) -> str:
        """Get existing or create new custom URL category for blocking"""
        logger.info(f"📂 Looking for custom category '{category_name}'...")
        
        try:
            # Get URL categories interface
            url_categories = None
            for attr in ['url_categories', 'urlCategories']:
                if hasattr(self.client.zia, attr):
                    url_categories = getattr(self.client.zia, attr)
                    break
            
            if not url_categories:
                logger.error("❌ Could not find url_categories interface")
                return None
            
            # List existing categories - no parameters, filter manually
            result = url_categories.list_categories()
            
            categories = []
            if isinstance(result, tuple):
                categories = result[0] if result[0] else []
            else:
                categories = result if result else []
            
            logger.info(f"📋 Found {len(categories)} URL categories")
            
            # Look for existing custom category with our name
            for cat in categories:
                cat_name = cat.get('configuredName', '') if isinstance(cat, dict) else getattr(cat, 'configuredName', '')
                cat_id = cat.get('id', '') if isinstance(cat, dict) else getattr(cat, 'id', '')
                custom = cat.get('customCategory', False) if isinstance(cat, dict) else getattr(cat, 'customCategory', False)
                
                if cat_name == category_name:
                    logger.info(f"✅ Found existing category: {cat_id}")
                    return str(cat_id)
            
            # Create new category if not found
            logger.info(f"📝 Creating new custom category '{category_name}'...")
            
            # Try different method signatures
            try:
                # Method 1: Using configured_name with custom_category=True
                new_cat = url_categories.add_url_category(
                    configured_name=category_name,
                    super_category="USER_DEFINED",
                    urls=[],
                    description="Custom category for automated URL blocking",
                    custom_category=True
                )
            except TypeError as e1:
                logger.info(f"Method 1 failed: {e1}, trying method 2...")
                try:
                    # Method 2: Without custom_category flag
                    new_cat = url_categories.add_url_category(
                        configured_name=category_name,
                        super_category="USER_DEFINED",
                        urls=[]
                    )
                except TypeError as e2:
                    logger.info(f"Method 2 failed: {e2}, trying method 3...")
                    # Method 3: Positional arguments
                    new_cat = url_categories.add_url_category(
                        category_name,
                        "USER_DEFINED",
                        []
                    )
            
            if isinstance(new_cat, tuple):
                if len(new_cat) >= 3 and new_cat[2]:
                    logger.error(f"❌ API Error creating category: {new_cat[2]}")
                    return None
                new_cat = new_cat[0] if new_cat[0] else None
            
            if new_cat:
                cat_id = new_cat.get('id', '') if isinstance(new_cat, dict) else getattr(new_cat, 'id', '')
                logger.info(f"✅ Created new category with ID: {cat_id}")
                return str(cat_id)
            
            logger.error("❌ Failed to create category - no response")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error with custom category: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _add_url_to_category(self, category_id: str, url: str) -> bool:
        """Add a URL to a custom URL category"""
        logger.info(f"➕ Adding URL '{url}' to category '{category_id}'...")
        
        try:
            url_categories = None
            for attr in ['url_categories', 'urlCategories']:
                if hasattr(self.client.zia, attr):
                    url_categories = getattr(self.client.zia, attr)
                    break
            
            if not url_categories:
                logger.error("❌ Could not find url_categories interface")
                return False
            
            # Try different method signatures for adding URL
            try:
                # Method 1: add_urls_to_category
                result = url_categories.add_urls_to_category(
                    category_id=category_id,
                    urls=[url]
                )
            except (TypeError, AttributeError) as e1:
                logger.info(f"Method 1 failed: {e1}, trying update_category...")
                try:
                    # Method 2: Get category first, then update with new URL
                    cat_result = url_categories.get_category(category_id)
                    if isinstance(cat_result, tuple):
                        cat_data = cat_result[0]
                    else:
                        cat_data = cat_result
                    
                    current_urls = cat_data.get('urls', []) if isinstance(cat_data, dict) else getattr(cat_data, 'urls', [])
                    if url not in current_urls:
                        new_urls = list(current_urls) + [url]
                        result = url_categories.update_url_category(
                            category_id=category_id,
                            urls=new_urls
                        )
                    else:
                        logger.warning(f"⚠️ URL '{url}' already exists in category")
                        return True
                except Exception as e2:
                    logger.error(f"Method 2 also failed: {e2}")
                    return False
            
            if isinstance(result, tuple) and len(result) >= 3 and result[2]:
                # Check if it's already there
                if "already exists" in str(result[2]).lower():
                    logger.warning(f"⚠️ URL '{url}' already exists in category")
                    return True
                logger.error(f"❌ API Error: {result[2]}")
                return False
            
            logger.info(f"✅ Added URL '{url}' to category")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add URL to category: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_category_to_rule(self, rule_name: str, category_id: str) -> bool:
        """Add a custom category to a URL filtering rule"""
        logger.info(f"🔗 Adding category '{category_id}' to rule '{rule_name}'...")
        
        url_filtering = self._get_url_filtering_interface()
        if not url_filtering:
            return False
        
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule.get('id') if isinstance(rule, dict) else getattr(rule, 'id', None)
        current_categories = rule.get('urlCategories', []) if isinstance(rule, dict) else getattr(rule, 'urlCategories', [])
        
        # Check if category already in rule
        if category_id in current_categories:
            logger.info(f"✅ Category already in rule")
            return True
        
        # Add new category
        new_categories = list(current_categories) + [category_id]
        
        try:
            result = url_filtering.update_rule(rule_id=rule_id, url_categories=new_categories)
            
            if isinstance(result, tuple) and len(result) >= 3 and result[2]:
                logger.error(f"❌ API Error: {json.dumps(result[2], indent=2)}")
                return False
            
            logger.info(f"✅ Added category to rule")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def update_rule_action(self, rule_name: str, action: str) -> bool:
        """Update the action of a rule"""
        logger.info(f"🔄 Updating rule '{rule_name}' action to '{action}'...")
        
        valid_actions = ['ALLOW', 'BLOCK', 'CAUTION', 'ISOLATE']
        if action.upper() not in valid_actions:
            logger.error(f"❌ Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
            return False
        
        url_filtering = self._get_url_filtering_interface()
        if not url_filtering:
            return False
        
        rule = self.get_rule_by_name(rule_name)
        if not rule:
            return False
        
        rule_id = rule.get('id') if isinstance(rule, dict) else getattr(rule, 'id', None)
        
        try:
            result = url_filtering.update_rule(rule_id=rule_id, action=action.upper())
            
            if isinstance(result, tuple) and len(result) >= 3 and result[2]:
                logger.error(f"❌ API Error: {result[2]}")
                return False
            
            logger.info(f"✅ Successfully updated rule '{rule_name}' action to '{action}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update rule: {e}")
            return False
    
    def list_url_categories(self, format_type: str = "table") -> None:
        """List all URL categories"""
        logger.info("📋 Fetching URL categories...")
        
        try:
            # Get url_categories interface
            if hasattr(self.zia, 'url_categories'):
                url_categories = self.zia.url_categories
            else:
                logger.error("❌ URL categories interface not available")
                sys.exit(1)
            
            result = url_categories.list_categories()
            
            # Handle tuple return
            if isinstance(result, tuple):
                categories = result[0] if result else []
                if len(result) >= 3 and result[2]:
                    logger.error(f"❌ API Error: {result[2]}")
                    sys.exit(1)
            else:
                categories = result
            
            if not categories:
                logger.warning("⚠️ No URL categories found")
                return
            
            categories_list = list(categories) if hasattr(categories, '__iter__') and not isinstance(categories, dict) else [categories]
            
            logger.info(f"✅ Found {len(categories_list)} URL categories")
            
            if format_type == "json":
                output = []
                for cat in categories_list:
                    if isinstance(cat, dict):
                        output.append(cat)
                    elif hasattr(cat, 'to_dict'):
                        output.append(cat.to_dict())
                    else:
                        output.append(str(cat))
                print(json.dumps(output, indent=2, default=str))
                
            elif format_type == "simple":
                for cat in categories_list:
                    if isinstance(cat, dict):
                        cat_id = cat.get('id', 'N/A')
                        name = cat.get('configuredName', cat.get('id', 'N/A'))
                    else:
                        cat_id = getattr(cat, 'id', 'N/A')
                        name = getattr(cat, 'configuredName', getattr(cat, 'id', 'N/A'))
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
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation (Official SDK)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python zscaler_url_automation.py --list-rules
  python zscaler_url_automation.py --list-rules --format json
  python zscaler_url_automation.py --list-categories
  python zscaler_url_automation.py --rule-name "My Rule" --add-category "SOCIAL_NETWORKING"
  python zscaler_url_automation.py --rule-name "My Rule" --block-url "bad-site.com"
  python zscaler_url_automation.py --rule-name "My Rule" --update-action BLOCK

Environment Variables:
  ZIA_USERNAME, ZIA_PASSWORD, ZIA_API_KEY, ZIA_CLOUD
        """
    )
    
    parser.add_argument('--list-rules', action='store_true', help='List all URL filtering rules')
    parser.add_argument('--list-categories', action='store_true', help='List all URL categories')
    parser.add_argument('--format', choices=['table', 'json', 'simple'], default='table')
    parser.add_argument('--rule-name', type=str, help='Rule name or ID')
    parser.add_argument('--add-category', type=str, help='Add URL category to rule')
    parser.add_argument('--block-url', type=str, help='Block URL in rule')
    parser.add_argument('--update-action', type=str, choices=['ALLOW', 'BLOCK', 'CAUTION', 'ISOLATE'])
    
    args = parser.parse_args()
    
    if not any([args.list_rules, args.list_categories, args.add_category, args.block_url, args.update_action]):
        parser.error("No operation specified")
    
    if (args.add_category or args.block_url or args.update_action) and not args.rule_name:
        parser.error("--rule-name required for modify operations")
    
    automation = ZscalerURLAutomation()
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
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
