# Canvas Group Management

This tutorial covers creating and managing groups on Canvas LMS.

## Initialize and authenticate

```python
from CanvasGroupy import CanvasGroup

cg = CanvasGroup(
    credentials_fp="credentials.json",
    API_URL="https://canvas.ucsd.edu",
    course_id=12345,
)
```

## Create a group category

Group categories (called "Group Sets" in Canvas UI) organize groups:

```python
cg.create_group_category({"name": "Final Project Groups"})
```

## Assign students to groups

```python
cg.assign_canvas_group(
    group_name="Team Alpha",
    group_members=["student1", "student2", "student3"],
    in_group_category="Final Project Groups",
)
```

## View existing groups

```python
# List all group categories
categories = cg.get_group_categories()

# Set and view groups in a category
cg.set_group_category("Final Project Groups")
groups = cg.get_groups()
# Returns: {"Team Alpha": ["student1", "student2", ...], ...}
```

## Send notifications

```python
student_canvas_id = cg.email_to_canvas_id["student1"]
cg.create_conversation(
    recipients=student_canvas_id,
    subject="Welcome to your project group",
    body="You have been assigned to Team Alpha.",
)
```
