#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Uses direct HTTP API calls with Cloud Service API Key
"""

import os
import sys
import logging
import argparse
import requests
from typing import Optional, List, Dict, Any
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZscalerAPIClient:
    """Direct HTTP API client for Zscaler using Cloud Service API Key"""
    
    def __init__(self):
        """Initialize Zscaler API client with Cloud Service API Key"""
        self.api_key = os.getenv('ZSCALER_API_KEY')
        self.base_url = os.getenv('ZSCALER_BASE_URL', 'https://zsapi.zscalerbeta.net/api/v1')
        
        # Validate credentials
        if not self.api_key:
            logger.error("❌ Missing required API key. Set ZSCALER_API_KEY environment variable")
            sys.exit(1)
        
        # Remove trailing slash from base URL if present
        self.base_url = self.base_url.rstrip('/')
        
        logger.info(f"🔐 Initializing Zscaler API client...")
        logger.info(f"📍 Base URL: {self.base_url}")
        logger.info(f"🔑 API Key length: {len(self.api_key)}")
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'auth-type': 'cloudkey',
            'cloudkey': self.api_key
        })
        
        # Test the connection
        if not self._test_connection():
            logger.error("❌ Failed to connect to Zscaler API")
            sys.exit(1)
        
        logger.info("✅ Successfully connected to Zscaler API")
    
    def _test_connection(self) -> bool:
        """Test API connectivity"""
        try:
            logger.info("🔍 Testing API connection...")
            response = self.session.get(f"{self.base_url}/urlFilteringRules")
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                logger.error("❌ Authentication failed - Invalid API key")
                return False
            elif response.status_code == 403:
                logger.error("❌ Access forbidden - Check API key permissions")
                return False
            else:
                logger.error(f"❌ Unexpected response: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> tuple:
        """
        Make an API request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request payload for POST/PUT
            
        Returns:
            Tuple of (response_data, error)
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                return None, f"Unsupported HTTP method: {method}"
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.text else {}, None
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {json.dumps(error_detail)}"
                except:
                    error_msg += f" - {response.text}"
                return None, error_msg
                
        except Exception as e:
            return None, str(e)
    
    def list_rules(self) -> tuple:
        """
        List all URL filtering rules
        
        Returns:
            Tuple of (rules_list, error)
        """
        logger.info("📋 Fetching URL filtering rules...")
        return self._make_request('GET', 'urlFilteringRules')
    
    def get_rule(self, rule_id: str) -> tuple:
        """
        Get a specific rule by ID
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Tuple of (rule_data, error)
        """
        return self._make_request('GET', f'urlFilteringRules/{rule_id}')
    
    def update_rule(self, rule_id: str, rule_data: Dict) -> tuple:
        """
        Update a rule
        
        Args:
            rule_id: Rule ID
            rule_data: Updated rule data
            
        Returns:
            Tuple of (updated_rule, error)
        """
        return self._make_request('PUT', f'urlFilteringRules/{rule_id}', rule_data)


class ZscalerURLAutomation:
    """Handles Zscaler URL filtering automation operations"""
    
    def __init__(self):
        """Initialize automation with API client"""
        self.client = ZscalerAPIClient()
    
    def list_rules(self, format_type: str = "table") -> None:
        """
        List all URL filtering rules
        
        Args:
            format_type: Output format (table, json, or simple)
        """
        rules, error = self.client.list_rules()
        
        if error:
            logger.error(f"❌ Failed to list rules: {error}")
            sys.exit(1)
        
        if not rules:
            logger.warning("⚠️ No URL filtering rules found")
            return
        
        logger.info(f"✅ Found {len(rules)} URL filtering rules")
        
        if format_type == "json":
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
    
    def get_rule_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by its name or ID
        
        Args:
            rule_name: Name or ID of the rule
            
        Returns:
            Rule dictionary if found, None otherwise
        """
        rules, error = self.client.list_rules()
        
        if error:
            logger.error(f"❌ Failed to get rules: {error}")
            return None
        
        for rule in rules:
            if rule.get('name') == rule_name or str(rule.get('id')) == rule_name:
                return rule
        
        logger.error(f"❌ Rule '{rule_name}' not found")
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
        
        rule_id = rule['id']
        current_categories = rule.get('urlCategories', [])
        
        # Check if category already exists
        if category_id in current_categories:
            logger.warning(f"⚠️ Category {category_id} already exists in rule '{rule_name}'")
            return True
        
        # Add the new category
        rule['urlCategories'] = current_categories + [category_id]
        
        # Update the rule
        updated_rule, error = self.client.update_rule(rule_id, rule)
        
        if error:
            logger.error(f"❌ Failed to update rule: {error}")
            return False
        
        logger.info(f"✅ Successfully added category {category_id} to rule '{rule_name}'")
        return True
    
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
        rule['blockOverride'] = current_urls + [url]
        
        # Update the rule
        updated_rule, error = self.client.update_rule(rule_id, rule)
        
        if error:
            logger.error(f"❌ Failed to update rule: {error}")
            return False
        
        logger.info(f"✅ Successfully blocked URL '{url}' in rule '{rule_name}'")
        return True
    
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
        
        rule_id = rule['id']
        rule['action'] = action.upper()
        
        # Update the rule
        updated_rule, error = self.client.update_rule(rule_id, rule)
        
        if error:
            logger.error(f"❌ Failed to update rule: {error}")
            return False
        
        logger.info(f"✅ Successfully updated rule '{rule_name}' action to '{action}'")
        return True


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Zscaler URL Filtering Automation (Direct HTTP API)',
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
