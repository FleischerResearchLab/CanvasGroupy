"""Shared test fixtures for CanvasGroupy test suite."""

import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Credential fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def credentials(tmp_path):
    """Create a temporary credentials.json and return its path."""
    creds = {"Canvas Token": "fake-canvas-token", "GitHub Token": "fake-github-token"}
    fp = tmp_path / "credentials.json"
    fp.write_text(json.dumps(creds))
    return str(fp)


@pytest.fixture
def bad_credentials(tmp_path):
    """Create a credentials.json missing required keys."""
    fp = tmp_path / "credentials.json"
    fp.write_text(json.dumps({"wrong_key": "value"}))
    return str(fp)


# ---------------------------------------------------------------------------
# Canvas mock fixtures
# ---------------------------------------------------------------------------

def _make_mock_user(email_prefix, canvas_id, short_name=None):
    """Helper to create a mock Canvas user object."""
    user = MagicMock()
    user.email = f"{email_prefix}@ucsd.edu"
    user.id = canvas_id
    user.short_name = short_name or email_prefix.title()
    return user


@pytest.fixture
def mock_canvas_users():
    """Three mock students."""
    return [
        _make_mock_user("alice", 101, "Alice Smith"),
        _make_mock_user("bob", 102, "Bob Jones"),
        _make_mock_user("carol", 103, "Carol Lee"),
    ]


@pytest.fixture
def mock_course(mock_canvas_users):
    """Mock Canvas course with students pre-loaded."""
    course = MagicMock()
    course.name = "Test Course"
    course.id = 99999
    course.get_users.return_value = mock_canvas_users
    return course


@pytest.fixture
def mock_group_category():
    """Mock Canvas group category with one group."""
    cat = MagicMock()
    cat.name = "Project Groups"

    group = MagicMock()
    group.name = "Team_Alpha"
    member = MagicMock()
    member.login_id = "alice"
    group.get_users.return_value = [member]

    cat.get_groups.return_value = [group]
    return cat


@pytest.fixture
def mock_canvas_api(mock_course, mock_group_category):
    """Patch canvasapi.Canvas and return (MockCanvas, canvas_instance, mock_course)."""
    with patch("CanvasGroupy.canvas.Canvas") as MockCanvas:
        canvas_instance = MagicMock()
        MockCanvas.return_value = canvas_instance
        canvas_instance.get_activity_stream_summary.return_value = {}
        canvas_instance.get_course.return_value = mock_course
        mock_course.get_group_categories.return_value = [mock_group_category]
        yield MockCanvas, canvas_instance, mock_course


# ---------------------------------------------------------------------------
# GitHub mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_github_api():
    """Patch PyGithub's Github class and return (MockGithub, github_instance, mock_org)."""
    with patch("CanvasGroupy.github.Github") as MockGithub:
        github_instance = MagicMock()
        MockGithub.return_value = github_instance

        mock_user = MagicMock()
        mock_user.login = "test-user"
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_user.get_repos.return_value = [mock_repo]
        github_instance.get_user.return_value = mock_user

        mock_org = MagicMock()
        mock_org.login = "TestOrg"
        github_instance.get_organization.return_value = mock_org

        yield MockGithub, github_instance, mock_org


# ---------------------------------------------------------------------------
# Grading fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_issue():
    """Mock GitHub issue with a parseable score."""
    issue = MagicMock()
    issue.title = "Project Checkpoint Feedback"
    issue.body = (
        "# Project Checkpoint Feedback\n\n"
        "## Feedback\n\n"
        "| Category | Score |\n"
        "|----------|-------|\n\n"
        "[comment]: # (Score = ...)\n"
        "Score = 8.5\n"
    )
    issue.url = "https://api.github.com/repos/TestOrg/team-alpha/issues/1"
    return issue


@pytest.fixture
def mock_ungraded_issue():
    """Mock GitHub issue with an ungraded (Ellipsis) score."""
    issue = MagicMock()
    issue.title = "Project Checkpoint Feedback"
    issue.body = (
        "# Project Checkpoint Feedback\n\n"
        "[comment]: # (Score = ...)\n"
        "Score = ...\n"
    )
    issue.url = "https://api.github.com/repos/TestOrg/team-alpha/issues/1"
    return issue
