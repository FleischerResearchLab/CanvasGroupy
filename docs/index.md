# CanvasGroupy

> Automate project group management across Canvas LMS and GitHub.

CanvasGroupy helps instructors manage project groups across **Canvas LMS** and **GitHub**. Create student groups on Canvas, set up GitHub repositories with the right permissions, and automate grading workflows — all from Python.

## Features

- **Canvas Group Management** — Create group categories, assign students to groups, send notifications
- **GitHub Repository Setup** — Create repos from templates, add collaborators, manage team permissions
- **Group Assignment** — Load group rosters from CSV or DataFrame and sync to Canvas + GitHub
- **Grading Workflow** — Parse scores from GitHub issue templates and post grades back to Canvas
- **Batch Feedback** — Release feedback to all groups via GitHub Issues from markdown templates

## Quick Start

```bash
pip install CanvasGroupy
```

```python
from CanvasGroupy import CanvasGroup, GitHubGroup, AssignGroup

# Authenticate
cg = CanvasGroup(credentials_fp="credentials.json", course_id=12345)
ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")

# Load groups and create on Canvas
ag = AssignGroup(ghg=ghg, cg=cg)
ag.load_groups("groups.csv")
ag.create_canvas_group(in_group_category="Project Groups")
```

See the [Getting Started](getting-started/installation.md) guide for full setup instructions.
