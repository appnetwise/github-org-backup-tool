#!/usr/bin/env python3
"""
GitHub Organization Repository Backup Tool

This script backs up all repositories from a source GitHub organization
and pushes them to a destination organization.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GitHubOrgBackup:
    """Main class for backing up GitHub organization repositories."""
    
    def __init__(self, source_org: str, dest_org: str, 
                 source_token: str, dest_token: str,
                 clone_dir: str = "./temp_clones",
                 include_private: bool = False,
                 workers: int = 3,
                 repo_prefix: str = "",
                 include_date_prefix: bool = False):
        self.source_org = source_org
        self.dest_org = dest_org
        self.source_token = source_token
        self.dest_token = dest_token
        self.clone_dir = Path(clone_dir)
        self.include_private = include_private
        self.workers = workers
        self.repo_prefix = repo_prefix
        self.include_date_prefix = include_date_prefix
        
        # Generate date prefix if requested
        if self.include_date_prefix:
            date_prefix = datetime.now().strftime("%Y%m%d-")
            self.repo_prefix = date_prefix + self.repo_prefix
        
        # Setup logging
        self.setup_logging()
        
        # Setup HTTP sessions with retry logic
        self.source_session = self.create_session(source_token)
        self.dest_session = self.create_session(dest_token)
        
        # Statistics
        self.stats = {
            'total_repos': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def setup_logging(self):
        """Configure logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backup.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, token: str) -> requests.Session:
        """Create a requests session with retry logic and authentication."""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Org-Backup-Tool/1.0'
        })
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        
        return session
    
    def get_repositories(self, org: str, session: requests.Session) -> List[Dict]:
        """Get all repositories from a GitHub organization."""
        repos = []
        page = 1
        per_page = 100
        
        self.logger.info(f"Fetching repositories from {org}...")
        
        while True:
            url = f"https://api.github.com/orgs/{org}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'type': 'all' if self.include_private else 'public'
            }
            
            try:
                response = session.get(url, params=params)
                
                if response.status_code == 403:
                    # Check if it's a rate limit
                    if 'X-RateLimit-Remaining' in response.headers:
                        remaining = int(response.headers['X-RateLimit-Remaining'])
                        if remaining == 0:
                            reset_time = int(response.headers['X-RateLimit-Reset'])
                            wait_time = reset_time - int(time.time()) + 1
                            self.logger.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                
                response.raise_for_status()
                page_repos = response.json()
                
                if not page_repos:
                    break
                
                repos.extend(page_repos)
                self.logger.info(f"Fetched {len(page_repos)} repositories (page {page})")
                page += 1
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching repositories: {e}")
                raise
        
        self.logger.info(f"Found {len(repos)} repositories in {org}")
        return repos
    
    def get_dest_repo_name(self, original_name: str) -> str:
        """Generate the destination repository name with prefix."""
        return f"{self.repo_prefix}{original_name}"
    
    def repository_exists(self, repo_name: str) -> bool:
        """Check if a repository exists in the destination organization."""
        dest_name = self.get_dest_repo_name(repo_name)
        url = f"https://api.github.com/repos/{self.dest_org}/{dest_name}"
        try:
            response = self.dest_session.get(url)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def create_repository(self, repo_data: Dict) -> bool:
        """Create a repository in the destination organization."""
        url = f"https://api.github.com/orgs/{self.dest_org}/repos"
        
        original_name = repo_data['name']
        dest_name = self.get_dest_repo_name(original_name)
        
        # Update description to include source information
        original_desc = repo_data.get('description', '')
        backup_desc = f"[BACKUP from {self.source_org}/{original_name}] {original_desc}".strip()
        
        payload = {
            'name': dest_name,
            'description': backup_desc,
            'private': repo_data.get('private', False),
            'has_issues': repo_data.get('has_issues', True),
            'has_projects': repo_data.get('has_projects', True),
            'has_wiki': repo_data.get('has_wiki', True),
            'auto_init': False
        }
        
        try:
            response = self.dest_session.post(url, json=payload)
            
            if response.status_code == 201:
                self.logger.info(f"Created repository: {dest_name}")
                return True
            elif response.status_code == 422:
                # Repository might already exist
                error_msg = response.json().get('message', '')
                if 'already exists' in error_msg.lower():
                    self.logger.info(f"Repository {dest_name} already exists")
                    return True
                else:
                    self.logger.error(f"Error creating repository {dest_name}: {error_msg}")
                    return False
            else:
                self.logger.error(f"Error creating repository {dest_name}: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creating repository {dest_name}: {e}")
            return False
    
    def clone_repository(self, repo_data: Dict, clone_path: Path) -> bool:
        """Clone a repository to the local filesystem."""
        clone_url = repo_data['clone_url'].replace(
            'https://github.com/',
            f'https://{self.source_token}@github.com/'
        )
        
        try:
            self.logger.info(f"Cloning {repo_data['name']}...")
            
            # Clone with all branches and tags
            result = subprocess.run([
                'git', 'clone', '--mirror', clone_url, str(clone_path)
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode == 0:
                self.logger.info(f"Successfully cloned {repo_data['name']}")
                return True
            else:
                self.logger.error(f"Error cloning {repo_data['name']}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout cloning {repo_data['name']}")
            return False
        except Exception as e:
            self.logger.error(f"Error cloning {repo_data['name']}: {e}")
            return False
    
    def push_repository(self, repo_name: str, clone_path: Path) -> bool:
        """Push a cloned repository to the destination organization."""
        dest_name = self.get_dest_repo_name(repo_name)
        dest_url = f"https://{self.dest_token}@github.com/{self.dest_org}/{dest_name}.git"
        
        try:
            self.logger.info(f"Pushing {repo_name} -> {dest_name}...")
            
            # Verify clone path exists
            if not clone_path.exists():
                self.logger.error(f"Clone path does not exist: {clone_path}")
                return False
            
            # Change to the cloned repository directory
            original_cwd = os.getcwd()
            os.chdir(clone_path)
            
            try:
                # First, try to push all branches and tags, excluding pull request refs
                # Get all refs except pull request refs
                get_refs_result = subprocess.run([
                    'git', 'for-each-ref', '--format=%(refname)', 'refs/'
                ], capture_output=True, text=True)
                
                if get_refs_result.returncode != 0:
                    self.logger.error(f"Error getting refs for {repo_name}: {get_refs_result.stderr}")
                    return False
                
                # Filter out pull request refs and other unwanted refs
                all_refs = get_refs_result.stdout.strip().split('\n')
                valid_refs = [ref for ref in all_refs if ref and not ref.startswith('refs/pull/')]
                
                if not valid_refs:
                    self.logger.warning(f"No valid refs found for {repo_name}")
                    return True
                
                # Push refs in batches to avoid overwhelming the server
                batch_size = 50
                for i in range(0, len(valid_refs), batch_size):
                    batch_refs = valid_refs[i:i + batch_size]
                    
                    # Push this batch of refs
                    push_cmd = ['git', 'push', dest_url] + [f"{ref}:{ref}" for ref in batch_refs]
                    result = subprocess.run(push_cmd, capture_output=True, text=True, timeout=3600)
                    
                    if result.returncode != 0:
                        # If batch push fails, try individual refs
                        self.logger.warning(f"Batch push failed for {repo_name}, trying individual refs...")
                        failed_refs = []
                        
                        for ref in batch_refs:
                            single_result = subprocess.run([
                                'git', 'push', dest_url, f"{ref}:{ref}"
                            ], capture_output=True, text=True, timeout=600)
                            
                            if single_result.returncode != 0:
                                # Only log as warning for pull request refs, error for others
                                if 'refs/pull/' in ref:
                                    self.logger.debug(f"Skipped pull request ref {ref} (expected)")
                                else:
                                    self.logger.warning(f"Failed to push ref {ref}: {single_result.stderr.strip()}")
                                    failed_refs.append(ref)
                        
                        if failed_refs and not any('refs/pull/' in ref for ref in failed_refs):
                            self.logger.error(f"Failed to push some important refs for {repo_name}: {failed_refs}")
                
                self.logger.info(f"Successfully pushed {repo_name} -> {dest_name}")
                return True
                    
            finally:
                os.chdir(original_cwd)
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout pushing {repo_name} -> {dest_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error pushing {repo_name} -> {dest_name}: {e}")
            return False
    
    def backup_repository(self, repo_data: Dict) -> bool:
        """Backup a single repository."""
        repo_name = repo_data['name']
        # Use timestamp and process id to ensure unique clone paths for concurrent operations
        import os
        timestamp = int(time.time() * 1000000)  # microsecond precision
        pid = os.getpid()
        unique_id = f"{timestamp}-{pid}-{hash(repo_name) % 10000:04d}"
        clone_path = self.clone_dir.absolute() / f"{repo_name}-{unique_id}.git"
        
        try:
            # Ensure clone directory exists
            self.clone_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if destination repository exists, create if not
            if not self.repository_exists(repo_name):
                if not self.create_repository(repo_data):
                    return False
            
            # Clone the repository
            if not self.clone_repository(repo_data, clone_path):
                return False
            
            # Verify clone was successful before pushing
            if not clone_path.exists():
                self.logger.error(f"Clone path {clone_path} does not exist after cloning {repo_name}")
                return False
            
            # Additional verification - check if it's a valid git repository
            if not (clone_path / 'refs').exists() or not (clone_path / 'objects').exists():
                self.logger.error(f"Clone path {clone_path} exists but is not a valid git repository for {repo_name}")
                return False
            
            # Push to destination
            success = self.push_repository(repo_name, clone_path)
            
            # Cleanup
            try:
                if clone_path.exists():
                    shutil.rmtree(clone_path)
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to cleanup {clone_path}: {cleanup_error}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error backing up {repo_name}: {e}")
            # Cleanup on error
            try:
                if clone_path.exists():
                    shutil.rmtree(clone_path)
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to cleanup {clone_path} after error: {cleanup_error}")
            return False
            return False
    
    def run_backup(self, exclude_repos: Optional[Set[str]] = None, 
                   include_only: Optional[Set[str]] = None,
                   dry_run: bool = False) -> None:
        """Run the backup process."""
        exclude_repos = exclude_repos or set()
        
        # Create clone directory
        self.clone_dir.mkdir(exist_ok=True)
        
        try:
            # Get repositories from source organization
            repos = self.get_repositories(self.source_org, self.source_session)
            
            # Filter repositories
            if include_only:
                repos = [r for r in repos if r['name'] in include_only]
            
            repos = [r for r in repos if r['name'] not in exclude_repos]
            
            self.stats['total_repos'] = len(repos)
            
            if dry_run:
                self.logger.info("DRY RUN - Repositories that would be backed up:")
                for repo in repos:
                    dest_name = self.get_dest_repo_name(repo['name'])
                    privacy = 'private' if repo['private'] else 'public'
                    self.logger.info(f"  - {repo['name']} -> {dest_name} ({privacy})")
                
                if self.repo_prefix:
                    self.logger.info(f"\nUsing prefix: '{self.repo_prefix}'")
                return
            
            self.logger.info(f"Starting backup of {len(repos)} repositories...")
            
            # Process repositories with thread pool
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_repo = {
                    executor.submit(self.backup_repository, repo): repo
                    for repo in repos
                }
                
                for future in as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        success = future.result()
                        if success:
                            self.stats['successful'] += 1
                        else:
                            self.stats['failed'] += 1
                    except Exception as e:
                        self.logger.error(f"Repository {repo['name']} generated an exception: {e}")
                        self.stats['failed'] += 1
            
            self.print_summary()
            
        except Exception as e:
            self.logger.error(f"Backup process failed: {e}")
            raise
        finally:
            # Cleanup clone directory if empty
            if self.clone_dir.exists() and not any(self.clone_dir.iterdir()):
                self.clone_dir.rmdir()
    
    def print_summary(self):
        """Print backup summary statistics."""
        self.logger.info("=" * 50)
        self.logger.info("BACKUP SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total repositories: {self.stats['total_repos']}")
        self.logger.info(f"Successful: {self.stats['successful']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        if self.stats['total_repos'] > 0:
            self.logger.info(f"Success rate: {(self.stats['successful'] / self.stats['total_repos'] * 100):.1f}%")
        else:
            self.logger.info("Success rate: N/A (no repositories found)")


def load_config(config_file: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backup all repositories from one GitHub organization to another",
        epilog="""
Authentication Options:
  1. GitHub CLI (recommended): Use --use-gh-auth for seamless authentication
  2. OAuth: Use --use-oauth for browser-based authentication  
  3. Personal Access Tokens: Use --source-token/--dest-token or environment variables
  4. Configuration file: Store credentials in config.json

Examples:
  # GitHub CLI authentication (recommended)
  gh auth login --scopes 'repo,read:org'
  python3 backup_org.py --source-org SOURCE --dest-org DEST --use-gh-auth --dry-run
  
  # OAuth authentication  
  python3 backup_org.py --source-org SOURCE --dest-org DEST --use-oauth --dry-run
  
  # Personal access tokens
  python3 backup_org.py --source-org SOURCE --dest-org DEST --source-token TOKEN --dry-run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--source-org', required=True,
                       help='Source GitHub organization name')
    parser.add_argument('--dest-org', required=True,
                       help='Destination GitHub organization name')
    parser.add_argument('--source-token',
                       help='GitHub token for source organization (or use SOURCE_GITHUB_TOKEN env var)')
    parser.add_argument('--dest-token',
                       help='GitHub token for destination organization (or use DEST_GITHUB_TOKEN env var)')
    parser.add_argument('--include-private', action='store_true',
                       help='Include private repositories')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be backed up without actually doing it')
    parser.add_argument('--exclude',
                       help='Comma-separated list of repositories to exclude')
    parser.add_argument('--include-only',
                       help='Comma-separated list of repositories to include only')
    parser.add_argument('--clone-dir', default='./temp_clones',
                       help='Directory for temporary clones (default: ./temp_clones)')
    parser.add_argument('--workers', type=int, default=3,
                       help='Number of parallel workers (default: 3)')
    parser.add_argument('--repo-prefix', default='',
                       help='Prefix to add to repository names in destination org')
    parser.add_argument('--include-date-prefix', action='store_true',
                       help='Include current date (YYYYMMDD) as prefix')
    parser.add_argument('--config', default='config.json',
                       help='Configuration file (default: config.json)')
    parser.add_argument('--use-oauth', action='store_true',
                       help='Use OAuth authentication instead of personal access tokens')
    parser.add_argument('--oauth-config', default='oauth_config.json',
                       help='OAuth configuration file (default: oauth_config.json)')
    parser.add_argument('--use-gh-auth', action='store_true',
                       help='Use GitHub CLI (gh) authentication (recommended)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Handle OAuth authentication
    if args.use_oauth:
        try:
            from oauth_auth import load_oauth_config, main as oauth_main
            
            print("🔐 Using OAuth authentication...")
            oauth_config = load_oauth_config()
            
            if not oauth_config or not oauth_config.get('access_token'):
                print("📱 OAuth not configured. Starting setup...")
                token = oauth_main()
                if not token:
                    print("❌ OAuth setup failed")
                    sys.exit(1)
                source_token = dest_token = token
            else:
                source_token = dest_token = oauth_config['access_token']
                print("✅ Using existing OAuth token")
                
        except ImportError:
            print("❌ OAuth module not found. Please ensure oauth_auth.py is available.")
            sys.exit(1)
    elif args.use_gh_auth:
        try:
            from gh_auth import GitHubCLIAuth
            
            print("🔐 Using GitHub CLI authentication...")
            gh_auth = GitHubCLIAuth()
            
            # Check if already authenticated
            auth_status = gh_auth.check_gh_auth_status()
            if auth_status.get('authenticated'):
                token = gh_auth.get_token()
                if token:
                    print(f"✅ Using GitHub CLI token for user: {auth_status.get('username', 'unknown')}")
                    source_token = dest_token = token
                else:
                    print("❌ Could not get token from GitHub CLI")
                    sys.exit(1)
            else:
                print("❌ Not authenticated with GitHub CLI")
                print("💡 Run: gh auth login --scopes 'repo,read:org'")
                print("💡 Or run: python3 gh_auth.py --org", args.source_org)
                sys.exit(1)
                
        except ImportError:
            print("❌ GitHub CLI auth module not found. Please ensure gh_auth.py is available.")
            sys.exit(1)
    else:
        # Get tokens from arguments, environment, or config
        source_token = (args.source_token or 
                       os.getenv('SOURCE_GITHUB_TOKEN') or 
                       config.get('source_token'))
        dest_token = (args.dest_token or 
                     os.getenv('DEST_GITHUB_TOKEN') or 
                     config.get('dest_token'))
    
    if not source_token or not dest_token:
        print("Error: GitHub tokens are required. Provide them via:")
        print("  - GitHub CLI authentication: --use-gh-auth (recommended)")
        print("  - OAuth authentication: --use-oauth")
        print("  - Command line arguments: --source-token/--dest-token")
        print("  - Environment variables: SOURCE_GITHUB_TOKEN/DEST_GITHUB_TOKEN")
        print("  - Configuration file: config.json")
        sys.exit(1)
    
    # Process exclude/include lists
    exclude_repos = set()
    if args.exclude:
        exclude_repos = set(repo.strip() for repo in args.exclude.split(','))
    elif config.get('exclude_repos'):
        exclude_repos = set(config['exclude_repos'])
    
    include_only = None
    if args.include_only:
        include_only = set(repo.strip() for repo in args.include_only.split(','))
    elif config.get('include_only'):
        include_only = set(config['include_only'])
    
    # Create backup instance
    backup = GitHubOrgBackup(
        source_org=args.source_org,
        dest_org=args.dest_org,
        source_token=source_token,
        dest_token=dest_token,
        clone_dir=args.clone_dir or config.get('clone_dir', './temp_clones'),
        include_private=args.include_private or config.get('include_private', False),
        workers=args.workers or config.get('workers', 3),
        repo_prefix=args.repo_prefix or config.get('repo_prefix', ''),
        include_date_prefix=args.include_date_prefix or config.get('include_date_prefix', False)
    )
    
    try:
        backup.run_backup(
            exclude_repos=exclude_repos,
            include_only=include_only,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        print("\nBackup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
