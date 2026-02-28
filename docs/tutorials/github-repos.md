# GitHub Repository Setup

This tutorial covers creating and managing GitHub repositories for project groups.

## Initialize and authenticate

```python
from CanvasGroupy import GitHubGroup

ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")
```

## Create a repository

```python
# Empty repository
repo = ghg.create_repo("team-alpha-project", private=True)

# From a template
repo = ghg.create_repo(
    "team-alpha-project",
    repo_template="MyOrg/project-template",
    private=True,
    description="Final project repository for Team Alpha",
)
```

## Create a group repository with collaborators

```python
repo = ghg.create_group_repo(
    repo_name="team-alpha",
    collaborators=["github_user1", "github_user2"],
    permission="write",
    repo_template="MyOrg/project-template",
    private=True,
    description="Team Alpha Project Repository",
    rename_files={
        "Checkpoint_groupXXX.ipynb": "Checkpoint_team-alpha.ipynb",
        "FinalProject_groupXXX.ipynb": "FinalProject_team-alpha.ipynb",
    },
    team_slug="instructors",
    team_permission="admin",
)
```

## Manage collaborators

```python
repo = ghg.get_repo("MyOrg/team-alpha")

# Add
ghg.add_collaborator(repo, "new_student", "write")

# Remove
ghg.remove_collaborator(repo, "dropped_student")

# Resend pending invitations
ghg.resend_invitations(repo)
```

## Manage teams

```python
ghg.add_team(repo, team_slug="graders", permission="push")
```
