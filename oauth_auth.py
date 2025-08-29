#!/usr/bin/env python3
"""
OAuth Authentication Module for GitHub Organization Backup Tool
"""

import base64
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Dict, Optional

import requests


class GitHubOAuth:
    """GitHub OAuth authentication handler."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_port: int = 8080):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_port = redirect_port
        self.redirect_uri = f"http://localhost:{redirect_port}/callback"
        self.access_token = None
        self.auth_code = None
        self.state = None
        
    def generate_pkce_params(self) -> Dict[str, str]:
        """Generate PKCE parameters for secure OAuth flow."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return {
            'code_verifier': code_verifier,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
    
    def get_authorization_url(self, scopes: list) -> tuple:
        """Generate authorization URL and state."""
        self.state = secrets.token_urlsafe(32)
        pkce_params = self.generate_pkce_params()
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'state': self.state,
            'response_type': 'code',
            'code_challenge': pkce_params['code_challenge'],
            'code_challenge_method': pkce_params['code_challenge_method']
        }
        
        auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        return auth_url, pkce_params['code_verifier']
    
    def start_callback_server(self) -> HTTPServer:
        """Start local server to handle OAuth callback."""
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def __init__(self, oauth_instance, *args, **kwargs):
                self.oauth_instance = oauth_instance
                super().__init__(*args, **kwargs)
                
            def do_GET(self):
                parsed_path = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_path.query)
                
                if parsed_path.path == '/callback':
                    if 'code' in query_params and 'state' in query_params:
                        received_state = query_params['state'][0]
                        if received_state == self.oauth_instance.state:
                            self.oauth_instance.auth_code = query_params['code'][0]
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            
                            success_html = """
                            <html>
                            <head><title>GitHub OAuth Success</title></head>
                            <body>
                                <h2>✅ Authentication Successful!</h2>
                                <p>You can close this window and return to the terminal.</p>
                                <script>setTimeout(function(){ window.close(); }, 3000);</script>
                            </body>
                            </html>
                            """
                            self.wfile.write(success_html.encode())
                        else:
                            self.send_error(400, "Invalid state parameter")
                    elif 'error' in query_params:
                        error = query_params['error'][0]
                        self.send_error(400, f"OAuth error: {error}")
                    else:
                        self.send_error(400, "Missing required parameters")
                else:
                    self.send_error(404, "Not found")
                    
            def log_message(self, format, *args):
                # Suppress server logs
                pass
        
        def handler_factory(oauth_instance):
            def handler(*args, **kwargs):
                return CallbackHandler(oauth_instance, *args, **kwargs)
            return handler
        
        server = HTTPServer(('localhost', self.redirect_port), handler_factory(self))
        return server
    
    def exchange_code_for_token(self, auth_code: str, code_verifier: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        token_url = "https://github.com/login/oauth/access_token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier
        }
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            
            if 'access_token' in token_data:
                self.access_token = token_data['access_token']
                return self.access_token
            else:
                print(f"❌ Token exchange failed: {token_data}")
                return None
                
        except Exception as e:
            print(f"❌ Error exchanging code for token: {e}")
            return None
    
    def authenticate(self, scopes: list = None) -> Optional[str]:
        """Perform complete OAuth authentication flow."""
        if scopes is None:
            scopes = ['repo', 'read:org']
        
        print("🔐 Starting GitHub OAuth authentication...")
        print(f"📋 Requesting scopes: {', '.join(scopes)}")
        
        # Generate authorization URL
        auth_url, code_verifier = self.get_authorization_url(scopes)
        
        # Start callback server
        print(f"🌐 Starting local server on port {self.redirect_port}...")
        server = self.start_callback_server()
        
        def run_server():
            server.serve_forever()
        
        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Open browser for authorization
        print(f"🚀 Opening browser for GitHub authorization...")
        print(f"📎 If browser doesn't open automatically, visit: {auth_url}")
        
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print(f"Please manually open: {auth_url}")
        
        # Wait for callback
        print("⏳ Waiting for authorization callback...")
        timeout = 300  # 5 minutes timeout
        start_time = time.time()
        
        while self.auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(1)
        
        server.shutdown()
        
        if self.auth_code is None:
            print("❌ OAuth authentication timed out or was cancelled")
            return None
        
        # Exchange code for token
        print("🔄 Exchanging authorization code for access token...")
        token = self.exchange_code_for_token(self.auth_code, code_verifier)
        
        if token:
            print("✅ OAuth authentication successful!")
            return token
        else:
            print("❌ Failed to get access token")
            return None
    
    def test_token(self, token: str) -> bool:
        """Test if the token works and display user info."""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            response = requests.get('https://api.github.com/user', headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            print(f"🎉 Authenticated as: {user_data['login']}")
            print(f"👤 Account type: {user_data.get('type', 'User')}")
            
            # Check token scopes
            scopes = response.headers.get('X-OAuth-Scopes', '').split(', ')
            print(f"🎯 Token scopes: {scopes}")
            
            return True
            
        except Exception as e:
            print(f"❌ Token test failed: {e}")
            return False


def setup_github_app():
    """Guide user through GitHub App setup."""
    print("📱 To use OAuth authentication, you need a GitHub OAuth App.")
    print("📋 Follow these steps:")
    print()
    print("1️⃣ Go to: https://github.com/settings/applications/new")
    print("2️⃣ Fill in the form:")
    print("   • Application name: 'GitHub Org Backup Tool'")
    print("   • Homepage URL: 'http://localhost:8080'")
    print("   • Authorization callback URL: 'http://localhost:8080/callback'")
    print("3️⃣ Click 'Register application'")
    print("4️⃣ Copy the Client ID and Client Secret")
    print()
    
    client_id = input("Enter your GitHub OAuth App Client ID: ").strip()
    client_secret = input("Enter your GitHub OAuth App Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID and Client Secret are required")
        return None, None
    
    return client_id, client_secret


def save_oauth_config(client_id: str, client_secret: str, access_token: str):
    """Save OAuth configuration to file."""
    oauth_config = {
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': access_token
    }
    
    with open('oauth_config.json', 'w') as f:
        json.dump(oauth_config, f, indent=2)
    
    print("💾 OAuth configuration saved to oauth_config.json")


def load_oauth_config() -> Optional[Dict]:
    """Load OAuth configuration from file."""
    try:
        with open('oauth_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def main():
    """Main OAuth setup function."""
    print("🔐 GitHub OAuth Authentication Setup")
    print("=" * 50)
    
    # Check if OAuth config already exists
    existing_config = load_oauth_config()
    if existing_config and existing_config.get('access_token'):
        print("🔍 Found existing OAuth configuration...")
        
        oauth = GitHubOAuth(
            existing_config['client_id'],
            existing_config['client_secret']
        )
        
        if oauth.test_token(existing_config['access_token']):
            print("✅ Existing token is valid!")
            choice = input("Use existing token? (y/n): ").lower().strip()
            if choice == 'y':
                return existing_config['access_token']
    
    # Setup new OAuth
    client_id, client_secret = setup_github_app()
    if not client_id or not client_secret:
        return None
    
    oauth = GitHubOAuth(client_id, client_secret)
    access_token = oauth.authenticate(['repo', 'read:org'])
    
    if access_token:
        save_oauth_config(client_id, client_secret, access_token)
        return access_token
    
    return None


if __name__ == '__main__':
    token = main()
    if token:
        print(f"\n🎉 Success! Your OAuth token: {token[:20]}...")
        print("💡 You can now use this token in your backup tool")
    else:
        print("\n❌ OAuth setup failed")
        sys.exit(1)
