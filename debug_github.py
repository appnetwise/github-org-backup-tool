#!/usr/bin/env python3
"""
Debug script to test GitHub API access
"""

import json
import requests
import sys


def test_github_access():
    """Test GitHub API access with the configured tokens and organization."""
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    source_org = config.get('source_org')
    source_token = config.get('source_token', '').strip()
    
    if not source_org or not source_token:
        print("❌ Missing source_org or source_token in config.json")
        return False
    
    print(f"🔍 Testing access to organization: {source_org}")
    print(f"🔑 Token starts with: {source_token[:12]}...")
    
    # Test authentication
    headers = {
        'Authorization': f'token {source_token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'GitHub-Org-Backup-Debug/1.0'
    }
    
    print("\n1️⃣ Testing authentication...")
    try:
        auth_response = requests.get('https://api.github.com/user', headers=headers)
        print(f"   Status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            user_data = auth_response.json()
            print(f"   ✅ Authenticated as: {user_data.get('login')}")
            print(f"   Account type: {user_data.get('type')}")
        else:
            print(f"   ❌ Authentication failed: {auth_response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    print(f"\n2️⃣ Testing organization access for: {source_org}")
    try:
        org_response = requests.get(f'https://api.github.com/orgs/{source_org}', headers=headers)
        print(f"   Status: {org_response.status_code}")
        
        if org_response.status_code == 200:
            org_data = org_response.json()
            print(f"   ✅ Organization found: {org_data.get('name', org_data.get('login'))}")
            print(f"   Public repos: {org_data.get('public_repos', 'unknown')}")
        elif org_response.status_code == 404:
            print(f"   ❌ Organization '{source_org}' not found or not accessible")
            print("   💡 Check if:")
            print("      - Organization name is spelled correctly")
            print("      - Your token has access to this organization")
            print("      - Organization exists and is accessible")
            return False
        else:
            print(f"   ❌ Organization access failed: {org_response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Organization access error: {e}")
        return False
    
    print(f"\n3️⃣ Testing repository listing for: {source_org}")
    try:
        # Test public repos first
        repos_url = f'https://api.github.com/orgs/{source_org}/repos'
        params = {'type': 'public', 'per_page': 10}
        
        repos_response = requests.get(repos_url, headers=headers, params=params)
        print(f"   Public repos status: {repos_response.status_code}")
        
        if repos_response.status_code == 200:
            public_repos = repos_response.json()
            print(f"   ✅ Found {len(public_repos)} public repositories")
            for repo in public_repos[:3]:  # Show first 3
                print(f"      - {repo['name']} ({repo['visibility']})")
            if len(public_repos) > 3:
                print(f"      ... and {len(public_repos) - 3} more")
        else:
            print(f"   ❌ Public repos access failed: {repos_response.text}")
        
        # Test all repos (including private)
        params['type'] = 'all'
        all_repos_response = requests.get(repos_url, headers=headers, params=params)
        print(f"   All repos status: {all_repos_response.status_code}")
        
        if all_repos_response.status_code == 200:
            all_repos = all_repos_response.json()
            print(f"   ✅ Found {len(all_repos)} total repositories (public + private)")
            
            private_count = sum(1 for repo in all_repos if repo.get('private', False))
            public_count = len(all_repos) - private_count
            print(f"      - Public: {public_count}")
            print(f"      - Private: {private_count}")
            
            if len(all_repos) > 0:
                print("   📋 Sample repositories:")
                for repo in all_repos[:5]:
                    visibility = "private" if repo.get('private') else "public"
                    print(f"      - {repo['name']} ({visibility})")
            
        elif all_repos_response.status_code == 403:
            print("   ⚠️  Access to private repos denied (check token permissions)")
        else:
            print(f"   ❌ All repos access failed: {all_repos_response.text}")
            
    except Exception as e:
        print(f"   ❌ Repository listing error: {e}")
        return False
    
    print(f"\n4️⃣ Checking token permissions...")
    try:
        # Check token scopes
        scopes = auth_response.headers.get('X-OAuth-Scopes', '').split(', ')
        print(f"   Token scopes: {scopes}")
        
        required_scopes = ['repo'] if config.get('include_private') else ['public_repo']
        missing_scopes = [scope for scope in required_scopes if scope not in scopes]
        
        if missing_scopes:
            print(f"   ⚠️  Missing required scopes: {missing_scopes}")
            print("   💡 Your token may need additional permissions")
        else:
            print("   ✅ Token has required permissions")
            
    except Exception as e:
        print(f"   ❌ Error checking permissions: {e}")
    
    print(f"\n🎉 Diagnosis complete!")
    return True


if __name__ == '__main__':
    print("🔧 GitHub Organization Backup - Debug Tool")
    print("=" * 50)
    
    success = test_github_access()
    
    if success:
        print("\n✅ No obvious issues found. Try running the backup again.")
        print("\n💡 If you're still having issues:")
        print("   - Try with --dry-run first")
        print("   - Check that the organization name is exactly correct")
        print("   - Ensure your token has the right permissions")
    else:
        print("\n❌ Issues found. Please fix the above problems and try again.")
    
    sys.exit(0 if success else 1)
