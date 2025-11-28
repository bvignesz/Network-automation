#!/usr/bin/env python3
"""
Enterprise Zscaler ZIA URL Management Script

Supports:
  - List current denylist/allowlist
  - Bulk add URLs (with deduplication)
  - Batch processing for large files
  - Detailed logging
  - JSON output for Ansible parsing

Environment Variables:
  ZIA_USERNAME
  ZIA_PASSWORD
  ZIA_API_KEY
  ZIA_CLOUD (e.g., zscaler, zscalerbeta, zscalerone, etc.)

Author: Network Automation Team
Version: 2.0
"""

import os
import sys
import logging
import argparse
import json
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime

import requests

# ============================================================================
# Logging Configuration
# ============================================================================

def setup_logging(log_file: Optional[str] = None, verbose: bool = False):
    """Configure logging with file and console handlers"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stderr)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


# ============================================================================
# SDK Client Loader
# ============================================================================

def get_zia_client_class():
    """
    Dynamically load Zscaler SDK client class.
    Tries multiple import paths for SDK version compatibility.
    """
    # Try newer oneapi_client structure
    try:
        from zscaler.oneapi_client import LegacyZIAClient
        logging.info("✓ Loaded LegacyZIAClient from zscaler.oneapi_client")
        return LegacyZIAClient
    except ImportError:
        pass

    # Try standard zia module
    try:
        from zscaler.zia import ZIAClientHelper
        logging.info("✓ Loaded ZIAClientHelper from zscaler.zia")
        return ZIAClientHelper
    except ImportError:
        pass

    # Try direct import
    try:
        from zscaler import ZIAClientHelper
        logging.info("✓ Loaded ZIAClientHelper from zscaler")
        return ZIAClientHelper
    except ImportError:
        pass

    logging.error("✗ Failed to import Zscaler SDK")
    logging.error("Run: pip install zscaler-sdk-python")
    sys.exit(1)


# ============================================================================
# Utility Functions
# ============================================================================

def normalize_urls(urls: List[str]) -> List[str]:
    """
    Normalize URL list: strip whitespace, remove empties, deduplicate.
    Preserves original order.
    """
    seen = set()
    normalized = []
    
    for url in urls:
        url = url.strip()
        
        # Skip empty lines and comments
        if not url or url.startswith('#'):
            continue
        
        # Case-insensitive deduplication
        url_lower = url.lower()
        if url_lower in seen:
            logging.debug(f"Skipping duplicate: {url}")
            continue
        
        seen.add(url_lower)
        normalized.append(url)
    
    return normalized


def read_urls_from_file(path: str) -> List[str]:
    """Read URLs from file, one per line"""
    if not os.path.isfile(path):
        logging.error(f"✗ Bulk file not found: {path}")
        sys.exit(1)
    
    logging.info(f"Reading URLs from: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"✗ Failed to read file: {e}")
        sys.exit(1)
    
    urls = normalize_urls(lines)
    logging.info(f"✓ Loaded {len(urls)} unique URLs from file")
    
    return urls


def validate_environment():
    """Validate required environment variables are set"""
    required_vars = ["ZIA_USERNAME", "ZIA_PASSWORD", "ZIA_API_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        logging.error(f"✗ Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    logging.info("✓ Environment variables validated")


# ============================================================================
# Zscaler Manager Class
# ============================================================================

class ZscalerURLManager:
    """
    Manages Zscaler ZIA URL lists (denylist/allowlist) via SDK + direct API.
    
    Uses SDK for authentication, then direct HTTP for operations.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.username = os.environ.get("ZIA_USERNAME")
        self.password = os.environ.get("ZIA_PASSWORD")
        self.api_key = os.environ.get("ZIA_API_KEY")
        self.cloud = os.environ.get("ZIA_CLOUD", "zscaler")
        
        validate_environment()
        
        # Initialize SDK client
        ClientClass = get_zia_client_class()
        config = {
            "username": self.username,
            "password": self.password,
            "api_key": self.api_key,
            "cloud": self.cloud,
        }
        
        self.logger.info(f"Initializing ZIA client for cloud: {self.cloud}")
        
        try:
            self.client = ClientClass(config)
            self.client.__enter__()
            self.logger.info("✓ SDK client initialized")
        except Exception as e:
            self.logger.error(f"✗ Failed to initialize SDK client: {e}")
            sys.exit(1)
        
        # Extract session ID
        self.session_id = self._extract_session_id()
        if not self.session_id:
            self.logger.error("✗ Failed to extract JSESSIONID from SDK")
            sys.exit(1)
        
        self.logger.info("✓ Session ID extracted successfully")
        
        self.base_url = f"https://zsapi.{self.cloud}.net/api/v1"
        self.logger.info(f"API Base URL: {self.base_url}")
    
    def __del__(self):
        """Cleanup SDK client session"""
        try:
            if hasattr(self, 'client'):
                self.client.__exit__(None, None, None)
                self.logger.info("✓ SDK session closed")
        except Exception:
            pass
    
    def _extract_session_id(self) -> str:
        """
        Extract JSESSIONID from SDK client.
        Handles multiple SDK version structures.
        """
        # Try newer oneapi_client style
        if hasattr(self.client, "zia_legacy_client"):
            legacy = self.client.zia_legacy_client
            if hasattr(legacy, "session_id"):
                return legacy.session_id
        
        # Try older style through request executor
        if hasattr(self.client, "_request_executor"):
            executor = self.client._request_executor
            if hasattr(executor, "zia_legacy_client"):
                legacy = executor.zia_legacy_client
                if hasattr(legacy, "session_id"):
                    return legacy.session_id
        
        return ""
    
    def _request(
        self, 
        method: str, 
        path: str, 
        json_body=None,
        retry_count: int = 3
    ) -> requests.Response:
        """
        Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, PUT, POST, DELETE)
            path: API endpoint path
            json_body: Request body (for PUT/POST)
            retry_count: Number of retries on failure
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": f"JSESSIONID={self.session_id}"
        }
        
        for attempt in range(1, retry_count + 1):
            try:
                self.logger.info(f"{method} {path} (attempt {attempt}/{retry_count})")
                
                resp = requests.request(
                    method, 
                    url, 
                    headers=headers, 
                    json=json_body, 
                    timeout=60
                )
                
                self.logger.info(f"Response: {resp.status_code}")
                
                if resp.status_code >= 400:
                    self.logger.error(f"Error response: {resp.text[:500]}")
                
                return resp
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt}): {e}")
                
                if attempt < retry_count:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"✗ Request failed after {retry_count} attempts")
                    raise
    
    # ========================================================================
    # Denylist Operations
    # ========================================================================
    
    def get_denylist(self) -> List[str]:
        """
        Fetch current denylist URLs.
        
        Returns:
            List of URLs currently in denylist
        """
        self.logger.info("Fetching current denylist...")
        
        try:
            resp = self._request("GET", "/security/advanced/blacklistUrls")
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Handle different response formats
                if isinstance(data, dict) and "blacklistUrls" in data:
                    urls = data.get("blacklistUrls", [])
                elif isinstance(data, list):
                    urls = data
                else:
                    urls = []
                
                urls = normalize_urls(urls)
                self.logger.info(f"✓ Retrieved {len(urls)} URLs from denylist")
                return urls
            else:
                self.logger.error(f"✗ Failed to fetch denylist: {resp.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"✗ Exception fetching denylist: {e}")
            return []
    
    def update_denylist_bulk(
        self, 
        new_urls: List[str],
        dry_run: bool = False
    ) -> Dict:
        """
        Bulk add URLs to denylist (ignores duplicates).
        
        Args:
            new_urls: List of URLs to add
            dry_run: If True, only simulate the operation
        
        Returns:
            Dict with operation results
        """
        self.logger.info(f"Starting denylist bulk update (dry_run={dry_run})")
        
        new_urls = normalize_urls(new_urls)
        self.logger.info(f"Processing {len(new_urls)} URLs")
        
        # Fetch existing denylist
        existing = self.get_denylist()
        existing_set = {url.lower() for url in existing}
        
        # Compute URLs to add
        to_add = [url for url in new_urls if url.lower() not in existing_set]
        
        if not to_add:
            self.logger.info("✓ All URLs already exist in denylist")
            return {
                "status": "no_change",
                "message": "All URLs already exist",
                "existing_count": len(existing),
                "added_count": 0,
                "added": [],
                "final_count": len(existing)
            }
        
        self.logger.info(f"Found {len(to_add)} new URLs to add")
        
        if dry_run:
            self.logger.info("✓ Dry-run mode: No changes made")
            return {
                "status": "dry_run",
                "message": "Dry-run completed successfully",
                "existing_count": len(existing),
                "would_add_count": len(to_add),
                "would_add": to_add,
                "final_count": len(existing) + len(to_add)
            }
        
        # Merge and update
        updated = existing + to_add
        
        self.logger.info(f"Updating denylist: {len(existing)} → {len(updated)} URLs")
        
        try:
            resp = self._request("PUT", "/security/advanced/blacklistUrls", json_body=updated)
            
            if resp.status_code in (200, 204):
                self.logger.info("✓ Denylist updated successfully")
                return {
                    "status": "updated",
                    "message": "Denylist updated successfully",
                    "existing_count": len(existing),
                    "added_count": len(to_add),
                    "added": to_add,
                    "final_count": len(updated)
                }
            else:
                self.logger.error(f"✗ Update failed: HTTP {resp.status_code}")
                return {
                    "status": "error",
                    "message": f"API returned status {resp.status_code}",
                    "http_status": resp.status_code,
                    "error_body": resp.text[:500]
                }
                
        except Exception as e:
            self.logger.error(f"✗ Exception during update: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ========================================================================
    # Allowlist Operations
    # ========================================================================
    
    def get_allowlist(self) -> Tuple[List[str], Dict]:
        """
        Fetch current allowlist URLs and full security object.
        
        Returns:
            Tuple of (allowlist_urls, full_security_object)
        """
        self.logger.info("Fetching current allowlist...")
        
        try:
            resp = self._request("GET", "/security")
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Handle different field names
                allow = (
                    data.get("allowlistUrls", []) or 
                    data.get("allowlist_urls", []) or 
                    data.get("whitelistUrls", []) or
                    []
                )
                
                allow = normalize_urls(allow)
                self.logger.info(f"✓ Retrieved {len(allow)} URLs from allowlist")
                return allow, data
            else:
                self.logger.error(f"✗ Failed to fetch allowlist: {resp.status_code}")
                return [], {}
                
        except Exception as e:
            self.logger.error(f"✗ Exception fetching allowlist: {e}")
            return [], {}
    
    def update_allowlist_bulk(
        self, 
        new_urls: List[str],
        dry_run: bool = False
    ) -> Dict:
        """
        Bulk add URLs to allowlist (ignores duplicates).
        
        Note: Allowlist requires PUT of entire /security object.
        
        Args:
            new_urls: List of URLs to add
            dry_run: If True, only simulate the operation
        
        Returns:
            Dict with operation results
        """
        self.logger.info(f"Starting allowlist bulk update (dry_run={dry_run})")
        
        new_urls = normalize_urls(new_urls)
        self.logger.info(f"Processing {len(new_urls)} URLs")
        
        # Fetch existing allowlist and security object
        existing, sec_obj = self.get_allowlist()
        
        if not sec_obj:
            self.logger.error("✗ Failed to fetch security object")
            return {
                "status": "error",
                "message": "Could not fetch security object"
            }
        
        existing_set = {url.lower() for url in existing}
        
        # Compute URLs to add
        to_add = [url for url in new_urls if url.lower() not in existing_set]
        
        if not to_add:
            self.logger.info("✓ All URLs already exist in allowlist")
            return {
                "status": "no_change",
                "message": "All URLs already exist",
                "existing_count": len(existing),
                "added_count": 0,
                "added": [],
                "final_count": len(existing)
            }
        
        self.logger.info(f"Found {len(to_add)} new URLs to add")
        
        if dry_run:
            self.logger.info("✓ Dry-run mode: No changes made")
            return {
                "status": "dry_run",
                "message": "Dry-run completed successfully",
                "existing_count": len(existing),
                "would_add_count": len(to_add),
                "would_add": to_add,
                "final_count": len(existing) + len(to_add)
            }
        
        # Merge and update security object
        updated = existing + to_add
        sec_obj["allowlistUrls"] = updated
        
        self.logger.info(f"Updating allowlist: {len(existing)} → {len(updated)} URLs")
        
        try:
            resp = self._request("PUT", "/security", json_body=sec_obj)
            
            if resp.status_code in (200, 204):
                self.logger.info("✓ Allowlist updated successfully")
                return {
                    "status": "updated",
                    "message": "Allowlist updated successfully",
                    "existing_count": len(existing),
                    "added_count": len(to_add),
                    "added": to_add,
                    "final_count": len(updated)
                }
            else:
                self.logger.error(f"✗ Update failed: HTTP {resp.status_code}")
                return {
                    "status": "error",
                    "message": f"API returned status {resp.status_code}",
                    "http_status": resp.status_code,
                    "error_body": resp.text[:500]
                }
                
        except Exception as e:
            self.logger.error(f"✗ Exception during update: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Zscaler ZIA URL Management Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # List current denylist
  python3 zscaler_url_automation.py --list deny

  # List current allowlist
  python3 zscaler_url_automation.py --list allow

  # Bulk add URLs to denylist
  python3 zscaler_url_automation.py --mode deny --bulk-file urls.txt

  # Bulk add URLs to allowlist
  python3 zscaler_url_automation.py --mode allow --bulk-file urls.txt

  # Dry-run (simulate without changes)
  python3 zscaler_url_automation.py --mode deny --bulk-file urls.txt --dry-run

Environment Variables Required:
  ZIA_USERNAME    - Zscaler admin username
  ZIA_PASSWORD    - Zscaler admin password
  ZIA_API_KEY     - Zscaler API key
  ZIA_CLOUD       - Zscaler cloud (default: zscaler)
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["deny", "allow"],
        help="Operation mode: deny (denylist) or allow (allowlist)"
    )
    
    parser.add_argument(
        "--list",
        choices=["deny", "allow"],
        help="List current URLs in deny/allow list"
    )
    
    parser.add_argument(
        "--bulk-file",
        type=str,
        help="Path to file containing URLs (one per line)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operation without making changes"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (default: stderr only)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(log_file=args.log_file, verbose=args.verbose)
    
    logger.info("=" * 70)
    logger.info("Zscaler URL Automation Script Started")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 70)
    
    # Initialize manager
    manager = ZscalerURLManager(logger)
    
    # Handle list operations
    if args.list:
        if args.list == "deny":
            urls = manager.get_denylist()
            result = {
                "operation": "list_denylist",
                "count": len(urls),
                "urls": urls
            }
        else:  # allow
            urls, _ = manager.get_allowlist()
            result = {
                "operation": "list_allowlist",
                "count": len(urls),
                "urls": urls
            }
        
        # Output JSON to stdout for Ansible
        print(json.dumps(result, indent=2))
        return
    
    # Handle bulk operations
    if args.mode and args.bulk_file:
        urls = read_urls_from_file(args.bulk_file)
        
        if args.mode == "deny":
            result = manager.update_denylist_bulk(urls, dry_run=args.dry_run)
        else:  # allow
            result = manager.update_allowlist_bulk(urls, dry_run=args.dry_run)
        
        result["operation"] = f"bulk_update_{args.mode}list"
        result["timestamp"] = datetime.now().isoformat()
        
        # Output JSON to stdout for Ansible
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["status"] == "error":
            sys.exit(1)
        
        return
    
    # No valid operation specified
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
