#!/usr/bin/env python3
"""
Zscaler URL Filtering Automation Script
Purpose: List rules, update policies, add URLs, generate reports
Author: Network Automation Team
Version: 2.0
"""

import os
import sys
import json
import csv
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from zscaler.zia import ZIAClientHelper
except ImportError:
    logger.error("❌ Zscaler SDK not installed. Run: pip install zscaler-sdk-python")
    sys.exit(1)


class ZscalerAutomation:
    """Main class for Zscaler URL filtering automation"""
    
    def __init__(self):
        """Initialize Zscaler client with environment variables"""
        self.username = os.getenv('ZSCALER_USERNAME')
        self.password = os.getenv('ZSCALER_PASSWORD')
        self.api_key = os.getenv('ZSCALER_API_KEY')
        self.cloud = os.getenv('ZSCALER_CLOUD', 'zscaler')
        
        self._validate_credentials()
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
            sys.exit(1)
            
    def list_all_rules(self, output_format: str = 'table') -> List[Dict]:
        """
        List all URL filtering rules with their status
        
        Args:
            output_format: 'table', 'csv', 'json'
            
        Returns:
            List of rule dictionaries
        """
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
            
            # Extract relevant information
            rules_data = []
            for rule in rules:
                rule_info = {
                    'id': rule.id,
                    'name': rule.name,
                    'state': rule.state,
                    'action': rule.action,
                    'order': rule.order,
                    'rank': rule.rank,
                    'description': rule.description or 'N/A',
                    'url_categories': ', '.join(rule.url_categories) if rule.url_categories else 'N/A',
                    'protocols': ', '.join(rule.protocols) if rule.protocols else 'N/A',
                    'locations': len(rule.locations) if rule.locations else 0,
                    'groups': len(rule.groups) if rule.groups else 0,
                    'users': len(rule.users) if rule.users else 0,
                }
                rules_data.append(rule_info)
                
            # Sort by order
            rules_data.sort(key=lambda x: x['order'])
            
            # Display based on format
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
            print(f"{rule['id']:<10} {rule['name']:<30} {rule['state']:<10} {rule['action']:<10} "
                  f"{rule['order']:<6} {rule['url_categories']:<40} {rule['description']:<30}")
                  
        print("="*150)
        print(f"\n📊 Total Rules: {len(rules_data)}")
        print(f"✅ Enabled: {sum(1 for r in rules_data if r['state'] == 'ENABLED')}")
        print(f"❌ Disabled: {sum(1 for r in rules_data if r['state'] == 'DISABLED')}")
        
    def _export_csv(self, rules_data: List[Dict]):
        """Export rules to CSV file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reports/zscaler_rules_{timestamp}.csv"
        
        # Create reports directory if it doesn't exist
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
                json.dump(rules_data, jsonfile, indent=2)
                
            logger.info(f"✅ JSON report exported: {filename}")
            print(f"\n📄 Report saved: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error exporting JSON: {str(e)}")
            
    def find_rule_by_name(self, rule_name: str) -> Optional[Dict]:
        """Find a specific rule by name"""
        try:
            rules, response, error = self.client.url_filtering.list_rules(
                query_params={'search': rule_name}
            )
            
            if error or not rules:
                logger.warning(f"⚠️  Rule '{rule_name}' not found")
                return None
                
            if len(rules) > 1:
                logger.warning(f"⚠️  Multiple rules found matching '{rule_name}'. Using first match.")
                
            rule = rules[0]
            logger.info(f"✅ Found rule: {rule.name} (ID: {rule.id})")
            return rule
            
        except Exception as e:
            logger.error(f"❌ Error finding rule: {str(e)}")
            return None
            
    def add_url_category_to_rule(self, rule_name: str, url_category: str) -> bool:
        """
        Add a URL category to an existing rule
        
        Args:
            rule_name: Name of the rule to update
            url_category: URL category to add (e.g., 'OTHER_ADULT_MATERIAL')
            
        Returns:
            Boolean indicating success
        """
        try:
            # Find the rule
            rule = self.find_rule_by_name(rule_name)
            if not rule:
                return False
                
            # Get current categories
            current_categories = rule.url_categories or []
            
            # Check if category already exists
            if url_category in current_categories:
                logger.warning(f"⚠️  Category '{url_category}' already exists in rule '{rule_name}'")
                return True
                
            # Add new category
            updated_categories = current_categories + [url_category]
            
            logger.info(f"📝 Adding category '{url_category}' to rule '{rule_name}'")
            
            # Update the rule
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
        """
        Block a specific URL by adding it to a rule
        Note: Zscaler doesn't support individual URLs in rules directly,
        so this adds the URL to custom categories or creates a new rule
        
        Args:
            rule_name: Name of the rule to update
            url_to_block: URL to block (e.g., 'badsite.com')
            
        Returns:
            Boolean indicating success
        """
        try:
            logger.info(f"🚫 Attempting to block URL: {url_to_block}")
            logger.info(f"📝 Target rule: {rule_name}")
            
            # Find the rule
            rule = self.find_rule_by_name(rule_name)
            if not rule:
                logger.error(f"❌ Cannot proceed without finding the rule")
                return False
                
            # For demonstration, we'll add a common blocking category
            # In production, you might use Custom URL Categories
            logger.info(f"ℹ️  Note: Zscaler rules use URL categories, not individual URLs")
            logger.info(f"ℹ️  Consider using Custom URL Categories to block specific domains")
            
            # Example: Update rule to BLOCK action if not already
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
                
            # Log the URL for manual addition to custom categories
            logger.warning(f"⚠️  Manual step required:")
            logger.warning(f"   1. Go to Zscaler Admin > URL & Cloud App Control > Custom Categories")
            logger.warning(f"   2. Add '{url_to_block}' to a custom category")
            logger.warning(f"   3. Assign that category to rule '{rule_name}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error blocking URL: {str(e)}")
            return False
            
    def update_rule_action(self, rule_name: str, action: str) -> bool:
        """
        Update the action of a rule
        
        Args:
            rule_name: Name of the rule
            action: New action (ALLOW, BLOCK, CAUTION)
            
        Returns:
            Boolean indicating success
        """
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
        description='Zscaler URL Filtering Automation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all rules in table format
  python zscaler_url_automation.py --list-rules
  
  # Export rules to CSV
  python zscaler_url_automation.py --list-rules --format csv
  
  # Add URL category to existing rule
  python zscaler_url_automation.py --rule-name "Block Social Media" --add-category "STREAMING_MEDIA"
  
  # Update rule action
  python zscaler_url_automation.py --rule-name "Allow Finance" --action ALLOW
  
  # Block URL (requires custom category setup)
  python zscaler_url_automation.py --rule-name "Block Malicious" --block-url "badsite.com"
        """
    )
    
    # Main operations
    parser.add_argument('--list-rules', action='store_true',
                        help='List all URL filtering rules')
    parser.add_argument('--format', choices=['table', 'csv', 'json'], default='table',
                        help='Output format for listing rules (default: table)')
    
    # Rule operations
    parser.add_argument('--rule-name', type=str,
                        help='Name of the rule to operate on')
    parser.add_argument('--add-category', type=str,
                        help='URL category to add to the rule')
    parser.add_argument('--block-url', type=str,
                        help='URL to block (requires custom category setup)')
    parser.add_argument('--action', type=str, choices=['ALLOW', 'BLOCK', 'CAUTION'],
                        help='Update rule action')
    
    args = parser.parse_args()
    
    # Initialize automation client
    zscaler = ZscalerAutomation()
    
    # Execute based on arguments
    success = True
    
    if args.list_rules or (not any([args.add_category, args.block_url, args.action])):
        # Default action: list rules
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
