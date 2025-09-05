# DBDemos Tracker Updater

A Python script to automatically check and update repositories with the [dbdemos tracker](https://github.com/databricks-field-eng/dbdemos-tracker).

## Features

- Automatically detects if dbdemos-tracker is already installed in a repository
- Supports multiple Python dependency formats (requirements.txt, pyproject.toml, setup.py, Pipfile)
- Adds tracker initialization code to the main entry point
- Creates feature branches and pull requests automatically
- Comprehensive error handling and logging

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd dbdemos-tracker-reviewer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up GitHub authentication:
   - Create a GitHub Personal Access Token with repository permissions
   - Export it as an environment variable or use the `--github-token` parameter

## Usage

The script supports three different ways to specify repositories:

### 1. Direct Repository URLs

```bash
python dbdemos_tracker_updater.py --github-token YOUR_TOKEN https://github.com/user/repo1 https://github.com/user/repo2
```

### 2. From a Text File

Create a text file with repository URLs (one per line):

```bash
# repos.txt
https://github.com/user/repo1
https://github.com/user/repo2
# This is a comment - lines starting with # are ignored
https://github.com/user/repo3
```

Then run:

```bash
python dbdemos_tracker_updater.py --github-token YOUR_TOKEN --from-file repos.txt
```

### 3. From a GitHub Organization

Process all repositories in an organization (excludes forks and archived repositories):

```bash
python dbdemos_tracker_updater.py --github-token YOUR_TOKEN --from-org my-organization
```

### Additional Options

#### With Environment Variable

```bash
export GITHUB_TOKEN=your_token_here
python dbdemos_tracker_updater.py --github-token $GITHUB_TOKEN --from-org my-organization
```

#### Verbose Logging

```bash
python dbdemos_tracker_updater.py --github-token YOUR_TOKEN --verbose --from-file repos.txt
```

#### Help

```bash
python dbdemos_tracker_updater.py --help
```

## How It Works

For each repository provided:

1. **Clone**: Clones the repository to a temporary directory
2. **Detect**: Checks if dbdemos-tracker is already installed by:
   - Scanning dependency files (requirements.txt, setup.py, pyproject.toml, etc.)
   - Looking for import statements in Python files
3. **Skip or Update**: If tracker exists, skips the repo. Otherwise:
   - Creates a feature branch `feature/add-dbdemos-tracker`
   - Adds dbdemos-tracker to the appropriate dependency file
   - Adds initialization code to the main entry point
   - Commits changes with descriptive message
   - Pushes the branch to the remote repository
   - Creates a pull request with detailed description

## Supported Dependency Formats

- `requirements.txt`
- `pyproject.toml` (Poetry)
- `setup.py`
- `Pipfile` (Pipenv)

## Entry Point Detection

The script looks for these files in order of preference:
1. `main.py`
2. `app.py` 
3. `__main__.py`
4. `run.py`
5. Any `.py` file in the root directory
6. Falls back to the largest Python file in the repository
7. Creates `main.py` if no suitable entry point is found

## Error Handling

- Gracefully handles repositories that don't exist or are inaccessible
- Skips repositories where tracker is already installed
- Continues processing other repositories if one fails
- Provides detailed error messages and logs

## Requirements

- Python 3.7+
- Git installed and accessible from command line
- GitHub Personal Access Token with repository permissions
- Write access to the target repositories

## GitHub Token Permissions

Your GitHub token needs the following permissions:
- `repo` (Full control of private repositories)
- `public_repo` (Access public repositories) 

## Example Output

```
2024-01-15 10:30:01 - INFO - Processing repository: https://github.com/user/example-repo
2024-01-15 10:30:02 - INFO - Cloning https://github.com/user/example-repo to /tmp/tmpxyz/example-repo
2024-01-15 10:30:05 - INFO - Created and checked out branch: feature/add-dbdemos-tracker
2024-01-15 10:30:05 - INFO - Added dbdemos-tracker to requirements.txt
2024-01-15 10:30:05 - INFO - Added dbdemos tracker initialization to main.py
2024-01-15 10:30:06 - INFO - Committed changes: Add dbdemos tracker
2024-01-15 10:30:07 - INFO - Pushed branch feature/add-dbdemos-tracker to origin
2024-01-15 10:30:08 - INFO - Created pull request: https://github.com/user/example-repo/pull/123
2024-01-15 10:30:08 - INFO - Successfully processed https://github.com/user/example-repo
```

## License

This project is licensed under the MIT License.
