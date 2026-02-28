# Feedback Templates

CanvasGroupy supports releasing batch feedback to student groups via GitHub Issues created from markdown templates.

## Template format

Feedback templates are markdown files where the first line (starting with `# `) becomes the issue title. Example:

```markdown
# Project Checkpoint Feedback

Total:

## Feedback

| Category          | Full Point | Your Score | Comment |
|-------------------|------------|------------|---------|
| Abstract          | 0.5        |            |         |
| Background        | 0.5        |            |         |
| Problem Statement | 0.5        |            |         |

Score = ...
```

## Create feedback directories

```python
repo = ghg.get_repo("MyOrg/team-alpha")
ghg.create_feedback_dir(
    repo=repo,
    template_fp="feedback_templates/",
    destination="feedback",
)
```

This creates `feedback/<repo-name>/` with copies of each template for grading.

## Release feedback

After filling in the feedback files:

```python
ghg.release_feedback(
    md_filename="checkpoint_feedback.md",
    feedback_dir="feedback",
)
```

This creates a GitHub Issue in each group's repository from the corresponding feedback file.
