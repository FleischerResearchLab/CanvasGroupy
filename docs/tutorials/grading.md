# Grading Workflow

Automate grading between GitHub Issues and Canvas assignments.

## Overview

The grading workflow:

1. Instructors/TAs fill in score templates in GitHub Issues
2. CanvasGroupy parses scores from issue markdown
3. Scores are posted back to Canvas assignments

## Setup

```python
from CanvasGroupy import Grading, GitHubGroup, CanvasGroup

ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")
cg = CanvasGroup(
    credentials_fp="credentials.json",
    API_URL="https://canvas.ucsd.edu",
    course_id=12345,
    group_category="Final Project Groups",
)
grading = Grading(ghg=ghg, cg=cg)
```

## Create feedback issues from templates

```python
repo = ghg.get_repo("MyOrg/team-alpha")
grading.create_issue_from_md(repo, "feedback/checkpoint_feedback.md")
```

## Grade a project component

```python
# Dry run (prints scores without posting)
grading.grade_project(
    repo=repo,
    component="checkpoint",
    assignment_id=67890,
    canvas_group_category="Final Project Groups",
    post=False,
)

# Post grades to Canvas
grading.grade_project(
    repo=repo,
    component="checkpoint",
    assignment_id=67890,
    canvas_group_category="Final Project Groups",
    post=True,
)
```

## Score format in GitHub Issues

In the issue body, scores are parsed from lines like:

```
Score = 8.5
```

Lines with `[comment]` are ignored. The `Grading` class looks for the first `Score = <value>` line that isn't a comment.
