#!/usr/bin/env python3
"""
Quick OAuth setup for GitHub Organization Backup Tool
"""

import sys
from oauth_auth import main as oauth_main

if __name__ == '__main__':
    print("🚀 GitHub OAuth Setup for Organization Backup Tool")
    print("=" * 60)
    
    token = oauth_main()
    
    if token:
        print("\n✅ OAuth setup complete!")
        print(f"🔑 Your token: {token[:20]}...")
        print("\n🎯 Next steps:")
        print("1. Run the backup tool with --use-oauth flag:")
        print("   python3 backup_org.py --source-org SOURCE --dest-org DEST --use-oauth --dry-run")
        print("2. The tool will automatically use your OAuth token")
    else:
        print("\n❌ OAuth setup failed")
        sys.exit(1)
