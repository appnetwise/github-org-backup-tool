<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# GitHub Organization Repository Backup Tool

This project provides a Python-based solution to backup all repositories from a source GitHub organization and push them to a destination organization.

## Features
- Lists all repositories in source organization
- Clones repositories with full history
- Creates corresponding repositories in destination organization
- Pushes all content to new repositories
- Supports both public and private repositories
- Handles large repositories efficiently

## Requirements
- Python 3.8+
- GitHub Personal Access Tokens for both organizations
- Git installed on the system
- Sufficient disk space for repository clones

## Usage
1. Configure your GitHub tokens in the environment
2. Run the backup script with source and destination organization names
3. Monitor the backup progress

## Checklist Progress
- [x] Verify that the copilot-instructions.md file in the .github directory is created.
- [x] Clarify Project Requirements - GitHub org backup tool with Python
- [x] Scaffold the Project - Created complete Python project structure
- [x] Customize the Project - Implemented full backup functionality with advanced features
- [x] Install Required Extensions - No extensions needed for Python CLI tool
- [x] Compile the Project - Python project ready, dependencies defined
- [x] Create and Run Task - Setup and test scripts created
- [x] Launch the Project - Tool ready for use with comprehensive documentation
- [x] Ensure Documentation is Complete - README and instructions completed
