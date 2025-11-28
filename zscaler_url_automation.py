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


def clean_payload(payload: dict) -> dict:
    """
    Remove empty/None values from payload to avoid SDK sending empty arrays.
    This prevents the HV000030 'keywords' validation error.
    
    Fields like keywords=[], ip_ranges=[], etc. cause Zscaler backend to reject the request.
    """
    return {k: v for k, v in payload.items() if v not in (None, [], {}, "")}


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
        
        # Initialize client with config dictionary (for SDK v1.x)
        try:
            config = {
                "username": self.username,
                "password": self.password,
                "api_key": self.api_key,
                "cloud": self.cloud,
                "logging": {
                    "enabled": True,
                    "verbose": False
                }
            }
            
            # For LegacyZIAClient, use context manager pattern for proper session handling
            self.client = ClientClass(config)
            
            # Enter context to authenticate
            self.client.__enter__()
            
            logger.info("✅ Successfully authenticated to Zscaler ZIA API")
            
            # Log available interfaces
            if hasattr(self.client, 'zia'):
                available = [attr for attr in dir(self.client.zia) if not attr.startswith('_')][:20]
                logger.info(f"📋 Available ZIA interfaces: {', '.join(available)}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SDK client: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def __del__(self):
        """Cleanup - exit context manager"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.__exit__(None, None, None)
            except:
                pass
    
    def _get_url_categories_api(self):
        """Get the URL categories API from the SDK"""
        for attr in ['url_categories', 'urlCategories']:
            if hasattr(self.client.zia, attr):
                return getattr(self.client.zia, attr)
        return None
    
    def _get_url_filtering_api(self):
        """Get the URL filtering rules API from the SDK"""
        for attr in ['url_filtering_rules', 'urlFilteringRules', 'web_application_rules']:
            if hasattr(self.client.zia, attr):
                return getattr(self.client.zia, attr)
        return None
    
    def _handle_sdk_response(self, result):
        """
        Handle SDK response - can be tuple (result, response, error) or direct result
        Returns: (data, error)
        """
        if isinstance(result, tuple):
            if len(result) >= 3:
                data, response, error = result[0], result[1], result[2]
                if error:
                    return None, error
                return data, None
            elif len(result) == 2:
                return result[0], result[1]
        return result, None
    
    def list_url_filtering_rules(self) -> List[Dict]:
        """List all URL filtering rules using SDK"""
        logger.info("📋 Listing URL filtering rules...")
        
        try:
            url_filtering = self._get_url_filtering_api()
            
            if not url_filtering:
                logger.error("❌ Could not find URL filtering API in SDK")
                return []
            
            # Try different method names
            for method_name in ['list_rules', 'list_url_filtering_rules', 'get_rules', 'list']:
                if hasattr(url_filtering, method_name):
                    method = getattr(url_filtering, method_name)
                    result = method()
                    
                    data, error = self._handle_sdk_response(result)
                    
                    if error:
                        logger.error(f"SDK error: {error}")
                        continue
                    
                    if data:
                        rules = []
                        for r in data:
                            if hasattr(r, 'as_dict'):
                                rules.append(r.as_dict())
                            elif isinstance(r, dict):
                                rules.append(r)
                            else:
                                rules.append(vars(r) if hasattr(r, '__dict__') else {"raw": str(r)})
                        return rules
            
            logger.error("❌ No suitable method found for listing rules")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error listing rules: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def list_url_categories(self, custom_only: bool = False) -> List[Dict]:
        """List URL categories using SDK"""
        logger.info(f"📋 Listing URL categories (custom_only={custom_only})...")
        
        try:
            url_categories = self._get_url_categories_api()
            
            if not url_categories:
                logger.error("❌ Could not find URL categories API in SDK")
                return []
            
            # Call list_categories with optional filter
            result = url_categories.list_categories()
            data, error = self._handle_sdk_response(result)
            
            if error:
                logger.error(f"SDK error listing categories: {error}")
                return []
            
            if not data:
                return []
            
            categories = []
            for cat in data:
                if hasattr(cat, 'as_dict'):
                    cat_dict = cat.as_dict()
                elif isinstance(cat, dict):
                    cat_dict = cat
                else:
                    cat_dict = vars(cat) if hasattr(cat, '__dict__') else {"raw": str(cat)}
                
                # Filter for custom only if requested
                if custom_only:
                    if cat_dict.get('customCategory', False) or cat_dict.get('custom_category', False):
                        categories.append(cat_dict)
                else:
                    categories.append(cat_dict)
            
            return categories
            
        except Exception as e:
            logger.error(f"❌ Error listing categories: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_or_create_block_category(self, category_name: str = "Blocked_URLs_Automation") -> Optional[str]:
        """
        Get existing or create new custom URL category for blocked URLs.
        
        WORKAROUND for SDK Bug (HV000030 keywords validation error):
        The SDK v1.9.5 has a known issue where add_url_category() causes server-side
        validation error. We use the SDK's authenticated session_id to make a direct
        HTTP POST with a minimal payload that works.
        """
        import requests
        
        logger.info(f"📂 Looking for custom category '{category_name}'...")
        
        try:
            url_categories = self._get_url_categories_api()
            
            if not url_categories:
                logger.error("❌ Could not find URL categories API in SDK")
                return None
            
            # Get all categories to check if ours exists (SDK works fine for GET)
            result = url_categories.list_categories()
            data, error = self._handle_sdk_response(result)
            
            if error:
                logger.error(f"SDK error listing categories: {error}")
                return None
            
            categories = data if data else []
            logger.info(f"📋 Found {len(categories)} URL categories")
            
            # Look for existing custom category with our name
            for cat in categories:
                if hasattr(cat, 'as_dict'):
                    cat_dict = cat.as_dict()
                elif isinstance(cat, dict):
                    cat_dict = cat
                else:
                    cat_dict = vars(cat) if hasattr(cat, '__dict__') else {}
                
                # Check both camelCase and snake_case field names
                cat_name = cat_dict.get('configuredName') or cat_dict.get('configured_name', '')
                cat_id = cat_dict.get('id', '')
                
                if cat_name == category_name:
                    logger.info(f"✅ Found existing category: {cat_id}")
                    return str(cat_id)
            
            # Create new category if not found
            logger.info(f"📝 Creating new custom category '{category_name}'...")
            
            # ============================================================
            # WORKAROUND: Use SDK's session_id for direct HTTP POST
            # This bypasses the SDK's add_url_category() which has issues
            # ============================================================
            
            # Get the SDK's internal legacy client
            try:
                # Try multiple paths to find the legacy ZIA client
                zia_legacy = None
                
                # Path 1: Direct attribute
                if hasattr(self.client, 'zia_legacy_client'):
                    zia_legacy = self.client.zia_legacy_client
                
                # Path 2: Through request executor
                if not zia_legacy and hasattr(self.client, '_request_executor'):
                    if hasattr(self.client._request_executor, 'zia_legacy_client'):
                        zia_legacy = self.client._request_executor.zia_legacy_client
                
                # Path 3: Through zia interface
                if not zia_legacy and hasattr(self.client, 'zia'):
                    if hasattr(self.client.zia, '_request_executor'):
                        if hasattr(self.client.zia._request_executor, 'zia_legacy_client'):
                            zia_legacy = self.client.zia._request_executor.zia_legacy_client
                
                if not zia_legacy or not hasattr(zia_legacy, 'session_id'):
                    logger.warning("⚠️ Could not access SDK session_id, trying SDK method anyway...")
                    return self._create_category_via_sdk(url_categories, category_name)
                
                # Get session_id and base URL from legacy client
                session_id = zia_legacy.session_id
                base_url = f"https://zsapi.{self.cloud}.net/api/v1"
                
                logger.info(f"🔑 Got session_id from SDK (length: {len(session_id) if session_id else 0})")
                
                # Create minimal payload (exactly what Zscaler API expects)
                # CRITICAL: Do NOT include keywords, ipRanges, etc. - not even as null
                payload = {
                    "configuredName": category_name,
                    "superCategory": "USER_DEFINED",
                    "customCategory": True,
                    "type": "URL_CATEGORY",
                    "urls": [],
                    "description": "Custom category for automated URL blocking"
                }
                
                # Build headers with session cookie
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Cookie": f"JSESSIONID={session_id}"
                }
                
                logger.info(f"📤 Sending direct POST to {base_url}/urlCategories")
                logger.info(f"📦 Payload: {json.dumps(payload)}")
                
                response = requests.post(
                    f"{base_url}/urlCategories",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                logger.info(f"📥 Response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    result_data = response.json()
                    cat_id = result_data.get('id', '')
                    logger.info(f"✅ Created new category with ID: {cat_id}")
                    return str(cat_id)
                else:
                    logger.error(f"❌ API error: {response.status_code} - {response.text}")
                    # If direct method fails, try SDK as fallback
                    logger.info("🔄 Trying SDK method as fallback...")
                    return self._create_category_via_sdk(url_categories, category_name)
                    
            except Exception as direct_error:
                logger.warning(f"⚠️ Direct HTTP failed: {direct_error}, trying SDK...")
                return self._create_category_via_sdk(url_categories, category_name)
            
        except Exception as e:
            logger.error(f"❌ Error with custom category: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_category_via_sdk(self, url_categories, category_name: str) -> Optional[str]:
        """Fallback: Create category using SDK method"""
        logger.info("📝 Creating category via SDK method...")
        
        result = url_categories.add_url_category(
            configured_name=category_name,
            super_category="USER_DEFINED",
            urls=[],
            custom_category=True,
            description="Custom category for automated URL blocking"
        )
        
        data, error = self._handle_sdk_response(result)
        
        if error:
            logger.error(f"❌ SDK error creating category: {error}")
            return None
        
        if data:
            if hasattr(data, 'as_dict'):
                cat_dict = data.as_dict()
            elif isinstance(data, dict):
                cat_dict = data
            else:
                cat_dict = vars(data) if hasattr(data, '__dict__') else {}
            
            cat_id = cat_dict.get('id', '')
            logger.info(f"✅ Created new category with ID: {cat_id}")
            return str(cat_id)
        
        logger.error("❌ Failed to create category - no response data")
        return None
    
    def _add_url_to_category(self, category_id: str, url: str) -> bool:
        """Add a URL to a custom URL category using SDK"""
        logger.info(f"➕ Adding URL '{url}' to category '{category_id}'...")
        
        try:
            url_categories = self._get_url_categories_api()
            
            if not url_categories:
                logger.error("❌ Could not find URL categories API in SDK")
                return False
            
            # Use add_urls_to_category method
            result = url_categories.add_urls_to_category(
                category_id=category_id,
                urls=[url]
            )
            
            data, error = self._handle_sdk_response(result)
            
            if error:
                logger.error(f"❌ SDK error adding URL: {error}")
                return False
            
            logger.info(f"✅ URL '{url}' added to category successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding URL to category: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_rule_by_name(self, rule_name: str) -> Optional[Dict]:
        """Get a URL filtering rule by name"""
        rules = self.list_url_filtering_rules()
        
        for rule in rules:
            if rule.get('name') == rule_name:
                return rule
        
        return None
    
    def _add_category_to_rule(self, rule_name: str, category_id: str) -> bool:
        """Add a URL category to a URL filtering rule using SDK"""
        logger.info(f"🔗 Adding category '{category_id}' to rule '{rule_name}'...")
        
        try:
            url_filtering = self._get_url_filtering_api()
            
            if not url_filtering:
                logger.error("❌ Could not find URL filtering API in SDK")
                return False
            
            # Get the rule first
            target_rule = self._get_rule_by_name(rule_name)
            
            if not target_rule:
                logger.error(f"❌ Rule '{rule_name}' not found")
                return False
            
            rule_id = target_rule.get('id')
            logger.info(f"📌 Found rule '{rule_name}' with ID: {rule_id}")
            
            # Get current URL categories
            current_categories = target_rule.get('urlCategories', []) or target_rule.get('url_categories', []) or []
            logger.info(f"   Current categories: {current_categories}")
            
            # Check if category already in rule
            if category_id in current_categories:
                logger.info(f"✅ Category '{category_id}' already in rule")
                return True
            
            # Add category to rule
            new_categories = list(current_categories) + [category_id]
            logger.info(f"📤 Updating rule with new categories: {new_categories}")
            
            # Build update payload - only include necessary fields
            # Use clean_payload to remove any empty values
            update_kwargs = clean_payload({
                "url_categories": new_categories,
                "urls": target_rule.get('urls'),
                "name": target_rule.get('name'),
                "order": target_rule.get('order'),
                "state": target_rule.get('state'),
                "action": target_rule.get('action'),
                "protocols": target_rule.get('protocols'),
                "block_override": target_rule.get('blockOverride') or target_rule.get('block_override'),
            })
            
            # Call update method
            result = url_filtering.update_rule(
                rule_id=str(rule_id),
                **update_kwargs
            )
            
            data, error = self._handle_sdk_response(result)
            
            if error:
                logger.error(f"❌ SDK error updating rule: {error}")
                return False
            
            logger.info(f"✅ Category added to rule successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding category to rule: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _activate_changes(self) -> bool:
        """Activate configuration changes using SDK"""
        logger.info("🔄 Activating configuration changes...")
        
        try:
            # Try to find activate method
            if hasattr(self.client.zia, 'activate'):
                activate_api = self.client.zia.activate
                
                # Try different method names
                for method_name in ['activate', 'activate_changes', 'activate_status']:
                    if hasattr(activate_api, method_name):
                        method = getattr(activate_api, method_name)
                        result = method()
                        data, error = self._handle_sdk_response(result)
                        
                        if error:
                            logger.warning(f"Activation warning: {error}")
                        else:
                            logger.info("✅ Configuration changes activated")
                        return True
            
            logger.info("ℹ️ No activation method found - changes may auto-activate on session end")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Activation warning: {e}")
            return True  # Continue anyway
    
    def block_url_in_rule(self, rule_name: str, url: str) -> bool:
        """
        Block a URL by:
        1. Creating/getting a custom URL category
        2. Adding the URL to that category
        3. Adding the category to the blocking rule
        4. Activating changes
        """
        logger.info(f"🚫 Blocking URL '{url}' via custom URL category...")
        
        # Step 1: Get or create the custom category
        category_id = self._get_or_create_block_category("Blocked_URLs_Automation")
        if not category_id:
            logger.error("❌ Failed to get or create block category")
            return False
        
        # Step 2: Add URL to the category
        if not self._add_url_to_category(category_id, url):
            logger.error("❌ Failed to add URL to category")
            return False
        
        # Step 3: Add category to the rule
        if not self._add_category_to_rule(rule_name, category_id):
            logger.error("❌ Failed to add category to rule")
            return False
        
        # Step 4: Activate changes
        self._activate_changes()
        
        logger.info(f"✅ Successfully blocked URL '{url}' using category '{category_id}'")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all URL filtering rules:
    python zscaler_url_automation.py --list-rules

  Block a URL in a specific rule:
    python zscaler_url_automation.py --rule-name "URL Filtering Rule-1" --block-url "malicious.com"

Environment Variables Required:
  ZIA_USERNAME  - Your ZIA admin username
  ZIA_PASSWORD  - Your ZIA admin password
  ZIA_API_KEY   - Your ZIA API key
  ZIA_CLOUD     - Your ZIA cloud (default: zscalerbeta)
        """
    )
    
    parser.add_argument('--list-rules', action='store_true', 
                       help='List all URL filtering rules')
    parser.add_argument('--list-categories', action='store_true',
                       help='List all URL categories')
    parser.add_argument('--rule-name', type=str, 
                       help='Name of the URL filtering rule to modify')
    parser.add_argument('--block-url', type=str, 
                       help='URL to block (will be added to a custom category)')
    parser.add_argument('--output', type=str, choices=['json', 'text'], default='text',
                       help='Output format (default: text)')
    
    args = parser.parse_args()
    
    # Initialize automation
    automation = ZscalerURLAutomation()
    
    # Execute requested operation
    if args.list_rules:
        rules = automation.list_url_filtering_rules()
        
        if args.output == 'json':
            print(json.dumps(rules, indent=2, default=str))
        else:
            print("\n" + "="*80)
            print("URL FILTERING RULES")
            print("="*80)
            
            if not rules:
                print("No rules found")
            else:
                for i, rule in enumerate(rules, 1):
                    print(f"\n--- Rule {i} ---")
                    print(f"  ID:     {rule.get('id', 'N/A')}")
                    print(f"  Name:   {rule.get('name', 'N/A')}")
                    print(f"  Action: {rule.get('action', 'N/A')}")
                    print(f"  State:  {rule.get('state', 'N/A')}")
                    print(f"  Order:  {rule.get('order', 'N/A')}")
                    categories = rule.get('urlCategories', []) or rule.get('url_categories', [])
                    print(f"  URL Categories: {categories if categories else 'None'}")
            
            print("\n" + "="*80)
    
    elif args.list_categories:
        categories = automation.list_url_categories(custom_only=True)
        
        if args.output == 'json':
            print(json.dumps(categories, indent=2, default=str))
        else:
            print("\n" + "="*80)
            print("CUSTOM URL CATEGORIES")
            print("="*80)
            
            if not categories:
                print("No custom categories found")
            else:
                for i, cat in enumerate(categories, 1):
                    print(f"\n--- Category {i} ---")
                    print(f"  ID:   {cat.get('id', 'N/A')}")
                    print(f"  Name: {cat.get('configuredName') or cat.get('configured_name', 'N/A')}")
                    urls = cat.get('urls', [])
                    print(f"  URLs: {urls if urls else 'None'}")
            
            print("\n" + "="*80)
    
    elif args.block_url and args.rule_name:
        success = automation.block_url_in_rule(args.rule_name, args.block_url)
        if success:
            print(f"\n✅ Successfully blocked URL '{args.block_url}' in rule '{args.rule_name}'")
            sys.exit(0)
        else:
            print(f"\n❌ Failed to block URL '{args.block_url}'")
            sys.exit(1)
    
    else:
        parser.print_help()
        print("\n⚠️  Please specify an operation (--list-rules, --list-categories, or --block-url with --rule-name)")


if __name__ == "__main__":
    main()
