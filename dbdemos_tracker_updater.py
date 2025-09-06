#!/usr/bin/env python3
"""
DBDemos Tracker Updater

A script to automatically check and update repositories with the dbdemos tracker.
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse

import git
import requests
from github import Github


class DBDemosTrackerUpdater:
    """Main class for updating repositories with dbdemos tracker."""
    
    def __init__(self, github_token: str):
        """Initialize the updater with GitHub token."""
        self.github_token = github_token
        self.github_client = Github(github_token)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        return logging.getLogger(__name__)
    
    def process_repositories(self, repo_urls: List[str]) -> None:
        """Process multiple repositories."""
        for repo_url in repo_urls:
            try:
                self.logger.info(f"Processing repository: {repo_url}")
                self.process_single_repository(repo_url)
            except Exception as e:
                self.logger.error(f"Failed to process {repo_url}: {str(e)}")
                continue
    
    def get_repositories_from_file(self, file_path: str) -> List[str]:
        """Read repository URLs from a text file."""
        repo_urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        repo_urls.append(line)
            self.logger.info(f"Loaded {len(repo_urls)} repositories from {file_path}")
            return repo_urls
        except Exception as e:
            self.logger.error(f"Failed to read repository file {file_path}: {str(e)}")
            return []
    
    def get_repositories_from_org(self, org_name: str) -> List[str]:
        """Get all repositories from a GitHub organization."""
        try:
            org = self.github_client.get_organization(org_name)
            repos = []
            
            self.logger.info(f"Fetching repositories from organization: {org_name}")
            
            for repo in org.get_repos():
                if not repo.archived and not repo.fork:
                    repos.append(repo.clone_url)
            
            self.logger.info(f"Found {len(repos)} active repositories in organization {org_name}")
            return repos
            
        except Exception as e:
            self.logger.error(f"Failed to fetch repositories from organization {org_name}: {str(e)}")
            return []
    
    def process_single_repository(self, repo_url: str) -> None:
        """Process a single repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clone repository
                repo_path = self.clone_repository(repo_url, temp_dir)
                repo = git.Repo(repo_path)
                
                # Check if tracker is already installed
                has_tracker = self.check_tracker_exists(repo_path)
                
                if has_tracker:
                    self.logger.info(f"DBDemos tracker already exists in {repo_url}")
                    return
                
                # Create feature branch
                branch_name = "feature/add-dbdemos-tracker"
                self.create_feature_branch(repo, branch_name)
                
                # Add tracker dependency and initialization
                changes_made = self.add_tracker_to_repo(repo_path)
                
                if not changes_made:
                    self.logger.warning(f"No changes were needed for {repo_url}")
                    return
                
                # Commit changes
                self.commit_changes(repo, "Add dbdemos tracker\n\nAutomatically add dbdemos-tracker dependency and initialization code.")
                
                # Push branch
                self.push_branch(repo, branch_name)
                
                # Create pull request
                self.create_pull_request(repo_url, branch_name)
                
                self.logger.info(f"Successfully processed {repo_url}")
                
            except Exception as e:
                self.logger.error(f"Error processing {repo_url}: {str(e)}")
                raise
    
    def clone_repository(self, repo_url: str, temp_dir: str) -> str:
        """Clone the repository to a temporary directory."""
        repo_name = os.path.basename(repo_url).replace('.git', '')
        repo_path = os.path.join(temp_dir, repo_name)
        
        self.logger.info(f"Cloning {repo_url} to {repo_path}")
        git.Repo.clone_from(repo_url, repo_path)
        
        return repo_path
    
    def check_tracker_exists(self, repo_path: str) -> bool:
        """Check if dbdemos-tracker is already installed in the repository."""
        # Check dependency files
        dependency_found = self.check_dependency_files(repo_path)
        if dependency_found:
            self.logger.info("Found dbdemos-tracker in dependency files")
            return True
        
        # Check for imports in code
        import_found = self.check_tracker_imports(repo_path)
        if import_found:
            self.logger.info("Found dbdemos-tracker imports in code")
            return True
        
        return False
    
    def check_dependency_files(self, repo_path: str) -> bool:
        """Check various dependency files for dbdemos-tracker."""
        dependency_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'setup.py',
            'pyproject.toml',
            'Pipfile',
            'poetry.lock'
        ]
        
        for dep_file in dependency_files:
            file_path = os.path.join(repo_path, dep_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'dbdemos-tracker' in content:
                            return True
                except Exception as e:
                    self.logger.warning(f"Could not read {dep_file}: {str(e)}")
        
        return False
    
    def check_tracker_imports(self, repo_path: str) -> bool:
        """Check for dbdemos-tracker imports in Python files."""
        for root, dirs, files in os.walk(repo_path):
            # Skip .git and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if re.search(r'from\s+dbdemos_tracker|import\s+dbdemos_tracker', content):
                                return True
                    except Exception as e:
                        self.logger.warning(f"Could not read {file_path}: {str(e)}")
        
        return False
    
    def create_feature_branch(self, repo: git.Repo, branch_name: str) -> None:
        """Create and checkout a new feature branch."""
        try:
            # Check if branch already exists
            if branch_name in [ref.name.split('/')[-1] for ref in repo.refs]:
                self.logger.warning(f"Branch {branch_name} already exists, checking out")
                repo.git.checkout(branch_name)
            else:
                repo.git.checkout('-b', branch_name)
                self.logger.info(f"Created and checked out branch: {branch_name}")
        except Exception as e:
            self.logger.error(f"Failed to create branch {branch_name}: {str(e)}")
            raise
    
    def add_tracker_to_repo(self, repo_path: str) -> bool:
        """Add dbdemos-tracker dependency and initialization to the repository."""
        changes_made = False
        
        # Add dependency
        if self.add_dependency(repo_path):
            changes_made = True
        
        # Add initialization code
        if self.add_initialization(repo_path):
            changes_made = True
        
        return changes_made
    
    def add_dependency(self, repo_path: str) -> bool:
        """Add dbdemos-tracker to the appropriate dependency file."""
        # Check for existing dependency files in order of preference
        dependency_files = [
            ('requirements.txt', self.add_to_requirements),
            ('pyproject.toml', self.add_to_pyproject),
            ('setup.py', self.add_to_setup_py),
            ('Pipfile', self.add_to_pipfile)
        ]
        
        for dep_file, add_func in dependency_files:
            file_path = os.path.join(repo_path, dep_file)
            if os.path.exists(file_path):
                return add_func(file_path)
        
        # If no dependency file exists, create requirements.txt
        req_path = os.path.join(repo_path, 'requirements.txt')
        with open(req_path, 'w', encoding='utf-8') as f:
            f.write('dbdemos-tracker\n')
        self.logger.info("Created requirements.txt with dbdemos-tracker")
        return True
    
    def add_to_requirements(self, file_path: str) -> bool:
        """Add dependency to requirements.txt file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'dbdemos-tracker' not in content:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('dbdemos-tracker\n')
            self.logger.info(f"Added dbdemos-tracker to {file_path}")
            return True
        
        return False
    
    def add_to_pyproject(self, file_path: str) -> bool:
        """Add dependency to pyproject.toml file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'dbdemos-tracker' not in content:
            # Simple approach: add to dependencies if [tool.poetry.dependencies] section exists
            if '[tool.poetry.dependencies]' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == '[tool.poetry.dependencies]':
                        # Insert after the dependencies section header
                        lines.insert(i + 1, 'dbdemos-tracker = "*"')
                        break
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.logger.info(f"Added dbdemos-tracker to {file_path}")
                return True
        
        return False
    
    def add_to_setup_py(self, file_path: str) -> bool:
        """Add dependency to setup.py file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'dbdemos-tracker' not in content:
            # Simple approach: look for install_requires and add the dependency
            install_requires_pattern = r'(install_requires\s*=\s*\[)(.*?)(\])'
            match = re.search(install_requires_pattern, content, re.DOTALL)
            
            if match:
                before, deps, after = match.groups()
                if deps.strip():
                    new_deps = f"{deps},\n        'dbdemos-tracker'"
                else:
                    new_deps = "\n        'dbdemos-tracker'\n    "
                
                new_content = content.replace(match.group(0), f"{before}{new_deps}{after}")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.logger.info(f"Added dbdemos-tracker to {file_path}")
                return True
        
        return False
    
    def add_to_pipfile(self, file_path: str) -> bool:
        """Add dependency to Pipfile."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'dbdemos-tracker' not in content:
            # Add to [packages] section
            if '[packages]' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == '[packages]':
                        lines.insert(i + 1, 'dbdemos-tracker = "*"')
                        break
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                self.logger.info(f"Added dbdemos-tracker to {file_path}")
                return True
        
        return False
    
    def add_initialization(self, repo_path: str) -> bool:
        """Add initialization code to the main entry point."""
        # Look for common entry points
        entry_points = ['main.py', 'app.py', '__main__.py', 'run.py']
        
        # Also check for any Python file in the root
        root_python_files = [f for f in os.listdir(repo_path) 
                           if f.endswith('.py') and not f.startswith('setup')]
        
        all_candidates = entry_points + root_python_files
        
        for entry_file in all_candidates:
            file_path = os.path.join(repo_path, entry_file)
            if os.path.exists(file_path):
                return self.add_tracker_init_to_file(file_path)
        
        # If no obvious entry point, look for the largest Python file
        largest_file = None
        largest_size = 0
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        if size > largest_size:
                            largest_size = size
                            largest_file = file_path
                    except Exception:
                        continue
        
        if largest_file:
            self.logger.info(f"Adding initialization to largest Python file: {largest_file}")
            return self.add_tracker_init_to_file(largest_file)
        
        # Last resort: create a new main.py
        main_path = os.path.join(repo_path, 'main.py')
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write('''"""Main entry point with dbdemos tracker initialization."""

import dbdemos_tracker

def main():
    """Main function."""
    dbdemos_tracker.initialize()
    print("Application started with dbdemos tracker")

if __name__ == "__main__":
    main()
''')
        self.logger.info("Created new main.py with dbdemos tracker initialization")
        return True
    
    def add_tracker_init_to_file(self, file_path: str) -> bool:
        """Add tracker initialization code to a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if already has the import
            if 'import dbdemos_tracker' in content or 'from dbdemos_tracker' in content:
                return False
            
            lines = content.split('\n')
            
            # Find the right place to add the import (after other imports)
            import_line_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_line_idx = i + 1
            
            # Add the import
            lines.insert(import_line_idx, 'import dbdemos_tracker')
            
            # Find where to add initialization (look for if __name__ == "__main__" or main function)
            init_added = False
            
            # Look for if __name__ == "__main__"
            for i, line in enumerate(lines):
                if '__name__' in line and '__main__' in line:
                    # Add initialization at the beginning of the main block
                    j = i + 1
                    while j < len(lines) and (lines[j].strip() == '' or lines[j].startswith(' ') or lines[j].startswith('\t')):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            lines.insert(j, '    dbdemos_tracker.initialize()')
                            init_added = True
                            break
                        j += 1
                    break
            
            # If no __main__ block, look for main function
            if not init_added:
                for i, line in enumerate(lines):
                    if re.match(r'def\s+main\s*\(', line.strip()):
                        # Add initialization at the beginning of main function
                        j = i + 1
                        while j < len(lines) and (lines[j].strip() == '' or lines[j].strip().startswith('#')):
                            j += 1
                        if j < len(lines):
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            lines.insert(j, ' ' * indent + 'dbdemos_tracker.initialize()')
                            init_added = True
                        break
            
            # If still not added, add at the end of the file
            if not init_added:
                lines.append('')
                lines.append('# Initialize dbdemos tracker')
                lines.append('dbdemos_tracker.initialize()')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            self.logger.info(f"Added dbdemos tracker initialization to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add initialization to {file_path}: {str(e)}")
            return False
    
    def commit_changes(self, repo: git.Repo, commit_message: str) -> None:
        """Commit changes to the repository."""
        try:
            # Add all changes
            repo.git.add('.')
            
            # Check if there are any changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                self.logger.info("No changes to commit")
                return
            
            # Commit changes
            repo.index.commit(commit_message)
            self.logger.info(f"Committed changes: {commit_message}")
            
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {str(e)}")
            raise
    
    def push_branch(self, repo: git.Repo, branch_name: str) -> None:
        """Push the feature branch to remote repository."""
        try:
            # Get the origin remote
            origin = repo.remote('origin')
            
            # Push the branch
            origin.push(refspec=f'{branch_name}:{branch_name}')
            self.logger.info(f"Pushed branch {branch_name} to origin")
            
        except Exception as e:
            self.logger.error(f"Failed to push branch {branch_name}: {str(e)}")
            raise
    
    def create_pull_request(self, repo_url: str, branch_name: str) -> None:
        """Create a pull request for the changes."""
        try:
            # Parse repository info from URL
            parsed_url = urlparse(repo_url)
            repo_path = parsed_url.path.strip('/').replace('.git', '')
            owner, repo_name = repo_path.split('/')[:2]
            
            # Get repository object
            github_repo = self.github_client.get_repo(f"{owner}/{repo_name}")
            
            # Get default branch
            default_branch = github_repo.default_branch
            
            # Create pull request
            pr_title = "Add dbdemos tracker"
            pr_body = """## Summary

This PR automatically adds the dbdemos-tracker dependency and initialization code to the project.

## Changes Made

- ✅ Added `dbdemos-tracker` dependency to the project's dependency file
- ✅ Added initialization code to automatically start tracking when the application runs

## About dbdemos-tracker

The [dbdemos-tracker](https://github.com/databricks-field-eng/dbdemos-tracker) is a utility for tracking demo usage and analytics in Databricks applications.

This change ensures that demo tracking is properly configured and will start automatically when the application runs.

---
*This PR was created automatically by the dbdemos-tracker-updater script.*
"""
            
            pr = github_repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=default_branch
            )
            
            self.logger.info(f"Created pull request: {pr.html_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {str(e)}")
            raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Automatically check and update repositories with dbdemos tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process specific repositories
  export GITHUB_TOKEN=your_token_here
  python %(prog)s https://github.com/user/repo1 https://github.com/user/repo2

  # Process repositories from a file
  export GITHUB_TOKEN=your_token_here
  python %(prog)s --from-file repos.txt

  # Process all repositories in an organization
  export GITHUB_TOKEN=your_token_here
  python %(prog)s --from-org my-organization
        """
    )
    
    # Create mutually exclusive group for input methods
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        'repositories',
        nargs='*',
        help='Git repository URLs to process'
    )
    input_group.add_argument(
        '--from-file',
        metavar='FILE',
        help='Read repository URLs from a text file (one URL per line, # for comments)'
    )
    input_group.add_argument(
        '--from-org',
        metavar='ORG',
        help='Process all repositories from a GitHub organization (excludes forks and archived repos)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate that at least one input method is provided
    if not args.repositories and not args.from_file and not args.from_org:
        parser.error("Must specify repositories, --from-file, or --from-org")
    
    # Get GitHub token from environment variable
    try:
        github_token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        print("ERROR: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        print("Please set it with: export GITHUB_TOKEN=your_token_here", file=sys.stderr)
        return 1
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize updater
    updater = DBDemosTrackerUpdater(github_token)
    
    # Determine repository source and get URLs
    repo_urls = []
    
    if args.repositories:
        repo_urls = args.repositories
    elif args.from_file:
        repo_urls = updater.get_repositories_from_file(args.from_file)
    elif args.from_org:
        repo_urls = updater.get_repositories_from_org(args.from_org)
    
    if not repo_urls:
        logging.error("No repositories found to process")
        return 1
    
    # Process repositories
    updater.process_repositories(repo_urls)
    return 0


if __name__ == "__main__":
    sys.exit(main())