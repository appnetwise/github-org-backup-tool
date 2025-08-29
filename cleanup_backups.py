#!/usr/bin/env python3
"""
Cleanup script to delete backup repositories from destination organization.
"""

import argparse
import json
import logging
import os
import sys
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GitHubCleanup:
    """Class for cleaning up backup repositories from GitHub organization."""
    
    def __init__(self, org: str, token: str, prefix: str = ""):
        self.org = org
        self.token = token
        self.prefix = prefix
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        })
    
    def get_repositories(self) -> List[dict]:
        """Get all repositories from the organization that match the prefix."""
        repos = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/orgs/{self.org}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'type': 'all'
            }
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                page_repos = response.json()
                if not page_repos:
                    break
                
                # Filter repositories by prefix
                filtered_repos = [
                    repo for repo in page_repos 
                    if repo['name'].startswith(self.prefix)
                ]
                repos.extend(filtered_repos)
                
                self.logger.info(f"Found {len(filtered_repos)} backup repositories on page {page}")
                page += 1
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching repositories: {e}")
                return []
        
        return repos
    
    def delete_repository(self, repo_name: str) -> bool:
        """Delete a repository from the organization."""
        url = f"https://api.github.com/repos/{self.org}/{repo_name}"
        
        try:
            response = self.session.delete(url)
            
            if response.status_code == 204:
                self.logger.info(f"✅ Deleted repository: {repo_name}")
                return True
            elif response.status_code == 404:
                self.logger.warning(f"⚠️  Repository not found: {repo_name}")
                return True  # Consider as success since it's already gone
            else:
                self.logger.error(f"❌ Failed to delete {repo_name}: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error deleting {repo_name}: {e}")
            return False
    
    def cleanup_backups(self, dry_run: bool = False) -> None:
        """Clean up all backup repositories."""
        repos = self.get_repositories()
        
        if not repos:
            self.logger.info("No backup repositories found to clean up")
            return
        
        self.logger.info(f"Found {len(repos)} backup repositories to delete")
        
        if dry_run:
            self.logger.info("DRY RUN - Repositories that would be deleted:")
            for repo in repos:
                self.logger.info(f"  - {repo['name']} ({'private' if repo['private'] else 'public'})")
            return
        
        # Ask for confirmation
        print(f"\n🚨 WARNING: This will delete {len(repos)} repositories from the '{self.org}' organization!")
        print("Repositories to be deleted:")
        for repo in repos[:10]:  # Show first 10
            print(f"  - {repo['name']}")
        if len(repos) > 10:
            print(f"  ... and {len(repos) - 10} more")
        
        confirm = input("\nAre you sure you want to proceed? Type 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            print("❌ Cleanup cancelled")
            return
        
        successful = 0
        failed = 0
        
        for repo in repos:
            if self.delete_repository(repo['name']):
                successful += 1
            else:
                failed += 1
        
        self.logger.info("=" * 50)
        self.logger.info("CLEANUP SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total repositories: {len(repos)}")
        self.logger.info(f"Successfully deleted: {successful}")
        self.logger.info(f"Failed: {failed}")
        self.logger.info(f"Success rate: {(successful/len(repos)*100):.1f}%")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Delete backup repositories from GitHub organization"
    )
    parser.add_argument('--org', required=True,
                       help='GitHub organization name')
    parser.add_argument('--token',
                       help='GitHub token (or use GITHUB_TOKEN env var)')
    parser.add_argument('--prefix', default='20250829-backup-',
                       help='Prefix of repositories to delete (default: 20250829-backup-)')
    parser.add_argument('--use-gh-auth', action='store_true',
                       help='Use GitHub CLI authentication')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    # Get token
    if args.use_gh_auth:
        try:
            from gh_auth import GitHubCLIAuth
            
            print("🔐 Using GitHub CLI authentication...")
            gh_auth = GitHubCLIAuth()
            
            auth_status = gh_auth.check_gh_auth_status()
            if auth_status.get('authenticated'):
                token = gh_auth.get_token()
                if token:
                    print(f"✅ Using GitHub CLI token for user: {auth_status.get('username', 'unknown')}")
                else:
                    print("❌ Could not get token from GitHub CLI")
                    sys.exit(1)
            else:
                print("❌ Not authenticated with GitHub CLI")
                print("💡 Run: gh auth login --scopes 'repo,delete_repo,read:org'")
                sys.exit(1)
                
        except ImportError:
            print("❌ GitHub CLI auth module not found. Please ensure gh_auth.py is available.")
            sys.exit(1)
    else:
        token = args.token or os.getenv('GITHUB_TOKEN')
        if not token:
            print("Error: GitHub token is required. Provide via:")
            print("  - GitHub CLI authentication: --use-gh-auth")
            print("  - Command line argument: --token")
            print("  - Environment variable: GITHUB_TOKEN")
            sys.exit(1)
    
    # Create cleanup instance and run
    cleanup = GitHubCleanup(
        org=args.org,
        token=token,
        prefix=args.prefix
    )
    
    try:
        cleanup.cleanup_backups(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\nCleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
