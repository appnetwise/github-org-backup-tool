#!/usr/bin/env python3
"""
GitHub CLI Authentication Module for GitHub Organization Backup Tool
"""

import json
import subprocess
import sys
from typing import Optional, Dict


class GitHubCLIAuth:
    """GitHub CLI authentication handler."""
    
    def __init__(self):
        self.gh_token = None
    
    def check_gh_installed(self) -> bool:
        """Check if GitHub CLI is installed."""
        try:
            result = subprocess.run(['gh', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def check_gh_auth_status(self) -> Dict:
        """Check GitHub CLI authentication status."""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to get user info
                output = result.stderr  # gh auth status outputs to stderr
                lines = output.split('\n')
                
                status = {
                    'authenticated': True,
                    'username': None,
                    'scopes': [],
                    'account': None
                }
                
                for line in lines:
                    if 'Logged in to github.com as' in line:
                        username = line.split('as')[1].strip().split()[0]
                        status['username'] = username
                    elif 'Logged in to github.com account' in line:
                        account = line.split('account')[1].strip().split()[0]
                        status['account'] = account
                
                return status
            else:
                return {'authenticated': False, 'error': result.stderr}
                
        except Exception as e:
            return {'authenticated': False, 'error': str(e)}
    
    def login_with_gh(self, scopes: list = None) -> bool:
        """Login using GitHub CLI."""
        if scopes is None:
            scopes = ['repo', 'read:org']
        
        print("🔐 Authenticating with GitHub CLI...")
        print("📋 This will request the following scopes:", ', '.join(scopes))
        
        try:
            # Use gh auth login with specific scopes
            cmd = ['gh', 'auth', 'login', '--scopes', ','.join(scopes)]
            result = subprocess.run(cmd, text=True)
            
            if result.returncode == 0:
                print("✅ GitHub CLI authentication successful!")
                return True
            else:
                print("❌ GitHub CLI authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Error during GitHub CLI authentication: {e}")
            return False
    
    def get_token(self) -> Optional[str]:
        """Get GitHub token from GitHub CLI."""
        try:
            result = subprocess.run(['gh', 'auth', 'token'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                token = result.stdout.strip()
                if token:
                    return token
                else:
                    print("❌ No token returned from GitHub CLI")
                    return None
            else:
                print(f"❌ Error getting token from GitHub CLI: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting token: {e}")
            return None
    
    def test_token_access(self, token: str, org: str) -> Dict:
        """Test token access to organization repositories."""
        import requests
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        results = {
            'user_info': None,
            'org_access': False,
            'repo_count': 0,
            'scopes': []
        }
        
        try:
            # Test user info
            user_response = requests.get('https://api.github.com/user', headers=headers)
            if user_response.status_code == 200:
                user_data = user_response.json()
                results['user_info'] = {
                    'login': user_data['login'],
                    'type': user_data.get('type', 'User'),
                    'name': user_data.get('name', 'N/A')
                }
                
                # Get scopes
                scopes = user_response.headers.get('X-OAuth-Scopes', '')
                results['scopes'] = scopes.split(', ') if scopes else []
            
            # Test organization repository access
            org_response = requests.get(f'https://api.github.com/orgs/{org}/repos?type=all&per_page=100', 
                                      headers=headers)
            if org_response.status_code == 200:
                repos = org_response.json()
                results['org_access'] = True
                results['repo_count'] = len(repos)
                results['repositories'] = repos[:5]  # First 5 for preview
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def setup_auth(self, org: str) -> Optional[str]:
        """Complete GitHub CLI authentication setup."""
        print("🚀 GitHub CLI Authentication Setup")
        print("=" * 40)
        
        # Check if gh is installed
        if not self.check_gh_installed():
            print("❌ GitHub CLI (gh) is not installed!")
            print("📦 Install it with:")
            print("   macOS: brew install gh")
            print("   Other: https://cli.github.com/")
            return None
        
        print("✅ GitHub CLI is installed")
        
        # Check current auth status
        auth_status = self.check_gh_auth_status()
        
        if auth_status.get('authenticated'):
            username = auth_status.get('username') or auth_status.get('account')
            print(f"✅ Already authenticated as: {username}")
            
            # Ask if user wants to continue with current auth
            choice = input("Use current authentication? (y/n): ").lower().strip()
            if choice == 'y':
                token = self.get_token()
                if token:
                    # Test access
                    print(f"🧪 Testing access to organization: {org}")
                    test_results = self.test_token_access(token, org)
                    
                    if test_results.get('user_info'):
                        user = test_results['user_info']
                        print(f"👤 User: {user['login']} ({user['name']})")
                        print(f"🎯 Scopes: {test_results.get('scopes', [])}")
                    
                    if test_results.get('org_access'):
                        print(f"✅ Organization access: {test_results['repo_count']} repositories found")
                        if test_results.get('repositories'):
                            print("📦 Sample repositories:")
                            for repo in test_results['repositories']:
                                privacy = "private" if repo.get('private') else "public"
                                print(f"   - {repo['name']} ({privacy})")
                        return token
                    else:
                        print("⚠️  Cannot access organization repositories")
                        print("💡 You may need to re-authenticate with proper scopes")
        else:
            print("❌ Not authenticated with GitHub CLI")
        
        # Login with GitHub CLI
        print("\n🔐 Starting GitHub CLI authentication...")
        if self.login_with_gh(['repo', 'read:org']):
            token = self.get_token()
            if token:
                print(f"🧪 Testing access to organization: {org}")
                test_results = self.test_token_access(token, org)
                
                if test_results.get('org_access'):
                    print(f"✅ Success! Found {test_results['repo_count']} repositories")
                    return token
                else:
                    print("❌ Authentication successful but cannot access organization")
                    print("💡 Make sure you're a member of the organization")
        
        return None


def main():
    """Main GitHub CLI auth setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub CLI Authentication Setup")
    parser.add_argument('--org', required=True, help='GitHub organization to test access')
    args = parser.parse_args()
    
    gh_auth = GitHubCLIAuth()
    token = gh_auth.setup_auth(args.org)
    
    if token:
        print(f"\n🎉 Authentication successful!")
        print(f"🔑 Token: {token[:20]}...")
        print("\n💡 You can now run the backup tool with --use-gh-auth:")
        print(f"   python3 backup_org.py --source-org {args.org} --dest-org DEST --use-gh-auth --dry-run")
        return token
    else:
        print("\n❌ Authentication failed")
        return None


if __name__ == '__main__':
    main()
