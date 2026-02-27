# Quick Start

This guide walks through the core workflow: loading groups, creating them on Canvas, and setting up GitHub repositories.

## Prerequisites

- [Install CanvasGroupy](installation.md)
- [Set up authentication](authentication.md)
- A CSV file with group assignments (columns: `group_name`, `student_id`)

## Step 1: Prepare your group roster

Create a CSV file `groups.csv`:

```csv
group_name,student_id
Team_Alpha,student1
Team_Alpha,student2
Team_Alpha,student3
Team_Beta,student4
Team_Beta,student5
Team_Beta,student6
```

The `student_id` column should contain Canvas SIS Login IDs (email prefix before `@`).

## Step 2: Create groups on Canvas

```python
from CanvasGroupy import CanvasGroup, GitHubGroup, AssignGroup

# Authenticate and select course
cg = CanvasGroup(credentials_fp="credentials.json",
                 API_URL="https://canvas.ucsd.edu",
                 course_id=12345)

# Create a group category
cg.create_group_category({"name": "Project Groups"})

# Load groups and assign
ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")
ag = AssignGroup(ghg=ghg, cg=cg)
ag.load_groups("groups.csv")
ag.create_canvas_group(in_group_category="Project Groups")
```

## Step 3: Create GitHub repositories

```python
# Fetch GitHub usernames from a Canvas quiz
ag.create_github_group(username_quiz_id=67890)
```

## Next steps

- [Canvas Groups Tutorial](../tutorials/canvas-groups.md) — detailed Canvas group management
- [GitHub Repos Tutorial](../tutorials/github-repos.md) — repo templates, permissions, teams
- [Grading Workflow](../tutorials/grading.md) — automate grading between GitHub and Canvas
