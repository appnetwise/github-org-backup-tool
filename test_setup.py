#!/usr/bin/env python3
"""
Test script for GitHub Organization Backup Tool
"""

import os
import sys
import subprocess
import importlib.util


def test_python_version():
    """Test if Python version is 3.8+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python version check passed")
        return True
    else:
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
        return False


def test_git_installation():
    """Test if Git is installed"""
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git installation check passed")
            return True
        else:
            print("❌ Git not found")
            return False
    except FileNotFoundError:
        print("❌ Git not found")
        return False


def test_dependencies():
    """Test if required dependencies are installed"""
    required_packages = ['requests', 'urllib3']
    missing_packages = []
    
    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing_packages.append(package)
    
    if not missing_packages:
        print("✅ All required dependencies are installed")
        return True
    else:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False


def test_script_syntax():
    """Test if the main script has valid syntax"""
    try:
        with open('backup_org.py', 'r') as f:
            code = f.read()
        compile(code, 'backup_org.py', 'exec')
        print("✅ Main script syntax check passed")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in backup_org.py: {e}")
        return False
    except FileNotFoundError:
        print("❌ backup_org.py not found")
        return False


def test_help_command():
    """Test if the help command works"""
    try:
        result = subprocess.run([sys.executable, 'backup_org.py', '--help'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and '--source-org' in result.stdout:
            print("✅ Help command works correctly")
            return True
        else:
            print("❌ Help command failed")
            return False
    except Exception as e:
        print(f"❌ Error running help command: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Running GitHub Organization Backup Tool Tests\n")
    
    tests = [
        ("Python Version", test_python_version),
        ("Git Installation", test_git_installation),
        ("Dependencies", test_dependencies),
        ("Script Syntax", test_script_syntax),
        ("Help Command", test_help_command),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The tool is ready to use.")
        print("\nQuick start:")
        print("1. Set your GitHub tokens:")
        print("   export SOURCE_GITHUB_TOKEN='your_source_token'")
        print("   export DEST_GITHUB_TOKEN='your_dest_token'")
        print("2. Run a dry-run:")
        print("   python3 backup_org.py --source-org SOURCE --dest-org DEST --dry-run")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues before using the tool.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
