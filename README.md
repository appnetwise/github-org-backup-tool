# GitHub Organization Repository Backup Tool

A comprehensive Python-based solution to backup all repositories from a source GitHub organization and migrate them to a destination organization with full history preservation, metadata, and advanced features.

## 🚀 Features

### Core Functionality
- **Complete Repository Migration**: Clones all repositories with full Git history, branches, and tags
- **Organization-to-Organization Backup**: Seamlessly transfers repositories between GitHub organizations
- **Metadata Preservation**: Maintains repository descriptions, visibility settings, and other metadata
- **Concurrent Processing**: Supports parallel repository processing for faster backups
- **Smart Naming**: Configurable repository prefixes and date stamps for organized backups

### Authentication Methods
- **GitHub CLI Integration**: Seamless authentication using `gh` CLI (recommended)
- **OAuth 2.0 Flow**: Browser-based authentication with PKCE security
- **Personal Access Tokens**: Support for both classic and fine-grained tokens
- **Configuration Files**: Store credentials securely in config files

### Advanced Features
- **Pull Request Handling**: Automatically filters out pull request refs that can't be pushed
- **Large File Support**: Handles repositories with large files and LFS content
- **Error Recovery**: Robust error handling with detailed logging and retry mechanisms
- **Dry Run Mode**: Preview what will be backed up without making changes
- **Selective Backup**: Include/exclude specific repositories
- **Cleanup Tools**: Built-in utilities to manage and clean up backup repositories

## 📋 Requirements

- **Python 3.8+**
- **Git** (command line tool)
- **GitHub CLI** (optional, but recommended): `brew install gh` or see [GitHub CLI installation](https://cli.github.com/)
- **Required Python packages**: `requests` (automatically installed)
- **Sufficient disk space** for temporary repository clones
- **GitHub organization access** with appropriate permissions

## 🔧 Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/appnetwise/github-org-backup-tool.git
   cd github-org-backup-tool
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up GitHub CLI (recommended):**
   ```bash
   # Install GitHub CLI
   brew install gh  # macOS
   # or follow instructions at https://cli.github.com/
   
   # Authenticate with required scopes
   gh auth login --scopes 'repo,read:org,delete_repo'
   ```

## 🚀 Quick Start

### Using GitHub CLI (Recommended)

```bash
# Authenticate with GitHub CLI
gh auth login --scopes 'repo,read:org,delete_repo'

# Dry run to see what would be backed up
python3 backup_org.py --source-org SOURCE_ORG --dest-org DEST_ORG --use-gh-auth --dry-run

# Run the actual backup
python3 backup_org.py --source-org SOURCE_ORG --dest-org DEST_ORG --use-gh-auth
```

### Using OAuth Authentication

```bash
# Set up OAuth (one-time setup)
python3 setup_oauth.py

# Run backup with OAuth
python3 backup_org.py --source-org SOURCE_ORG --dest-org DEST_ORG --use-oauth
```

### Using Personal Access Tokens

```bash
# Run with tokens as arguments
python3 backup_org.py --source-org SOURCE_ORG --dest-org DEST_ORG \
  --source-token YOUR_SOURCE_TOKEN --dest-token YOUR_DEST_TOKEN

# Or set environment variables
export SOURCE_GITHUB_TOKEN="your_source_token"
export DEST_GITHUB_TOKEN="your_dest_token"
python3 backup_org.py --source-org SOURCE_ORG --dest-org DEST_ORG
```

## 📖 Usage Examples

### Basic Backup with Date Prefix
```bash
python3 backup_org.py \
  --source-org mycompany \
  --dest-org mycompany-backup \
  --use-gh-auth \
  --include-date-prefix \
  --repo-prefix "backup-"
```

### Selective Backup
```bash
# Include only specific repositories
python3 backup_org.py \
  --source-org mycompany \
  --dest-org mycompany-backup \
  --use-gh-auth \
  --include-only "repo1,repo2,repo3"

# Exclude specific repositories
python3 backup_org.py \
  --source-org mycompany \
  --dest-org mycompany-backup \
  --use-gh-auth \
  --exclude "temp-repo,old-repo"
```

### Performance Tuning
```bash
# Use more parallel workers for faster backup
python3 backup_org.py \
  --source-org mycompany \
  --dest-org mycompany-backup \
  --use-gh-auth \
  --workers 5

# Use single worker for problematic repositories
python3 backup_org.py \
  --source-org mycompany \
  --dest-org mycompany-backup \
  --use-gh-auth \
  --workers 1
```

## 🛠️ Configuration

### Configuration File (config.json)
```json
{
  "source_org": "mycompany",
  "dest_org": "mycompany-backup",
  "repo_prefix": "backup-",
  "include_date_prefix": true,
  "include_private": true,
  "workers": 3,
  "clone_dir": "./temp_clones",
  "exclude_repos": ["temp-repo", "old-repo"],
  "source_token": "optional_token_here",
  "dest_token": "optional_token_here"
}
```

### Command Line Options
```
--source-org         Source GitHub organization name (required)
--dest-org           Destination GitHub organization name (required)
--use-gh-auth        Use GitHub CLI authentication (recommended)
--use-oauth          Use OAuth 2.0 authentication
--source-token       Source organization token
--dest-token         Destination organization token
--include-private    Include private repositories
--dry-run           Preview mode - show what would be backed up
--exclude           Comma-separated list of repositories to exclude
--include-only      Comma-separated list of repositories to include only
--repo-prefix       Prefix for backup repository names
--include-date-prefix Add current date (YYYYMMDD) as prefix
--workers           Number of parallel workers (default: 3)
--clone-dir         Directory for temporary clones
--config            Configuration file path
```

## 🧹 Cleanup Tools

### Delete Backup Repositories
```bash
# Dry run to see what would be deleted
python3 cleanup_backups.py --org DEST_ORG --use-gh-auth --dry-run

# Delete all backup repositories with default prefix
python3 cleanup_backups.py --org DEST_ORG --use-gh-auth

# Delete repositories with custom prefix
python3 cleanup_backups.py --org DEST_ORG --use-gh-auth --prefix "custom-backup-"
```

## 🔍 Testing and Debugging

### Test Authentication
```bash
# Test GitHub CLI authentication
python3 gh_auth.py --org YOUR_ORG

# Test OAuth setup
python3 oauth_auth.py

# Debug GitHub API access
python3 debug_github.py --org YOUR_ORG --use-gh-auth
```

### Verify Setup
```bash
# Test token permissions and access
python3 test_token.py

# Run setup verification
python3 test_setup.py
```

## 📊 Real-World Usage Example

This tool has been successfully tested with enterprise-scale organization backups:

```bash
# Example backup command:
python3 backup_org.py \
  --source-org source-company \
  --dest-org backup-company \
  --use-gh-auth \
  --workers 1

# Example results:
# ✅ Total repositories: 10
# ✅ Successfully backed up: 10
# ✅ Failed: 0
# ✅ Success rate: 100%
```

**Example backup repositories created:**
- `20250829-backup-web-frontend`
- `20250829-backup-api-service`
- `20250829-backup-terraform-modules`
- `20250829-backup-infrastructure`
- `20250829-backup-mobile-app`
- `20250829-backup-landing-page`
- `20250829-backup-platform-core`
- `20250829-backup-platform-templates`
- `20250829-backup-test-suite`
- `20250829-backup-integration-tests`

## 🚨 Important Notes

### Security Considerations
- **Token Security**: Never commit tokens to version control
- **Scope Requirements**: Ensure tokens have appropriate scopes (`repo`, `read:org`, `delete_repo` for cleanup)
- **Organization Permissions**: Verify you have admin rights to destination organization

### Best Practices
- **Start with Dry Run**: Always use `--dry-run` first to preview changes
- **Single Worker for Issues**: Use `--workers 1` if experiencing concurrency issues
- **Monitor Large Repositories**: Some repositories may take longer due to size or LFS content
- **Backup Verification**: Verify backup integrity by checking a few repositories manually

### Known Limitations
- **Pull Request Refs**: Cannot migrate pull request references (automatically filtered)
- **Large Files**: May receive warnings for files >50MB (still backed up successfully)
- **API Rate Limits**: GitHub API rate limits may affect very large organizations
- **Disk Space**: Temporary clones require sufficient local disk space

## 🐛 Troubleshooting

### Common Issues
1. **403 Forbidden Errors**: Check token scopes and organization permissions
2. **File Path Conflicts**: Use `--workers 1` to resolve concurrency issues
3. **Large File Warnings**: These are warnings, not errors - backup still succeeds
4. **Authentication Failures**: Verify GitHub CLI is authenticated with correct scopes

### Getting Help
- Check the logs for detailed error messages
- Use `--dry-run` to test without making changes
- Verify authentication with test scripts
- Review GitHub token permissions and scopes

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with Python and the GitHub API
- Uses GitHub CLI for seamless authentication
- Supports OAuth 2.0 with PKCE for secure authentication
- Designed for reliability and enterprise-scale repository migrations

---

**Made with ❤️ for reliable GitHub organization backups**

