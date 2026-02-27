# CanvasGroupy

> Automate project group management across Canvas LMS and GitHub.

[![CI](https://github.com/FleischerResearchLab/CanvasGroupy/actions/workflows/test.yaml/badge.svg)](https://github.com/FleischerResearchLab/CanvasGroupy/actions/workflows/test.yaml)
[![Documentation](https://github.com/FleischerResearchLab/CanvasGroupy/actions/workflows/deploy.yaml/badge.svg)](https://FleischerResearchLab.github.io/CanvasGroupy/)

CanvasGroupy helps instructors manage project groups across **Canvas LMS** and **GitHub**. Create student groups on Canvas, set up GitHub repositories with the right permissions, and automate grading workflows — all from Python.

## Features

- **Canvas Group Management** — Create group categories, assign students to groups, and send notifications via Canvas API
- **GitHub Repository Setup** — Create repos from templates, add collaborators, manage team permissions
- **Group Assignment** — Load group rosters from CSV or DataFrame and sync to Canvas + GitHub
- **Grading Workflow** — Parse scores from GitHub issue templates and post grades back to Canvas
- **Batch Feedback** — Release feedback to all groups via GitHub Issues from markdown templates

## Installation

```bash
pip install CanvasGroupy
```

## Quick Start

### 1. Set up credentials

Create a `credentials.json` file:

```json
{
    "Canvas Token": "your-canvas-api-token",
    "GitHub Token": "your-github-personal-access-token"
}
```

- **Canvas Token**: Generate at `Canvas > Account > Settings > New Access Token`
- **GitHub Token**: Generate at `GitHub > Settings > Developer settings > Personal access tokens`

### 2. Create groups on Canvas

```python
from CanvasGroupy import CanvasGroup

cg = CanvasGroup(credentials_fp="credentials.json",
                 API_URL="https://canvas.ucsd.edu",
                 course_id=12345)

# Create a group category and assign students
cg.create_group_category({"name": "Project Groups"})
cg.assign_canvas_group(
    group_name="Team Alpha",
    group_members=["student1", "student2", "student3"],
    in_group_category="Project Groups"
)
```

### 3. Load groups from CSV and create GitHub repos

```python
from CanvasGroupy import AssignGroup, GitHubGroup, CanvasGroup

ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")
cg = CanvasGroup(credentials_fp="credentials.json",
                 API_URL="https://canvas.ucsd.edu",
                 course_id=12345)

ag = AssignGroup(ghg=ghg, cg=cg)

# Load from CSV (columns: group_name, student_id)
ag.load_groups("groups.csv")

# Create groups on Canvas
ag.create_canvas_group(in_group_category="Project Groups")
```

### 4. Grade projects via GitHub Issues

```python
from CanvasGroupy import Grading, GitHubGroup, CanvasGroup

grading = Grading(ghg=ghg, cg=cg)

repo = ghg.get_repo("MyOrg/team-alpha")
grading.grade_project(
    repo=repo,
    component="checkpoint",
    assignment_id=67890,
    canvas_group_category="Project Groups",
    post=True  # Set False for dry run
)
```

## Documentation

Full documentation: [FleischerResearchLab.github.io/CanvasGroupy](https://FleischerResearchLab.github.io/CanvasGroupy/)

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
