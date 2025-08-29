#!/usr/bin/env python3
"""
Quick token test script
"""

import requests
import sys

def test_token_scopes():
    # Read token from input
    print("🔑 Please test your new token:")
    token = input("Enter your GitHub token: ").strip()
    
    if not token:
        print("❌ No token provided")
        return False
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Test authentication and get scopes
    response = requests.get('https://api.github.com/user', headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return False
    
    scopes = response.headers.get('X-OAuth-Scopes', '').split(', ')
    print(f"✅ Token scopes: {scopes}")
    
    # Test repository access
    repos_response = requests.get(
        'https://api.github.com/orgs/Memcrypt-io/repos', 
        headers=headers,
        params={'type': 'all', 'per_page': 10}
    )
    
    if repos_response.status_code == 200:
        repos = repos_response.json()
        print(f"✅ Found {len(repos)} repositories!")
        for repo in repos[:3]:
            print(f"   - {repo['name']}")
        return True
    else:
        print(f"❌ Repository access failed: {repos_response.status_code}")
        return False

if __name__ == '__main__':
    test_token_scopes()
