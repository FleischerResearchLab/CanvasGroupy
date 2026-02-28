"""Tests for CanvasGroupy.grading — Grading class."""

import pytest
from unittest.mock import MagicMock, patch
from CanvasGroupy.grading import Grading


class TestFetchIssue:
    def test_finds_issue_by_component(self, mock_issue):
        repo = MagicMock()
        repo.get_issues.return_value = [mock_issue]

        grading = Grading()
        result = grading.fetch_issue(repo, "checkpoint")
        assert result == mock_issue

    def test_case_insensitive_match(self, mock_issue):
        repo = MagicMock()
        repo.get_issues.return_value = [mock_issue]

        grading = Grading()
        result = grading.fetch_issue(repo, "CHECKPOINT")
        assert result == mock_issue

    def test_raises_when_not_found(self):
        repo = MagicMock()
        repo.get_issues.return_value = []

        grading = Grading()
        with pytest.raises(ValueError, match="did not found"):
            grading.fetch_issue(repo, "nonexistent")


class TestParseScore:
    def test_parses_numeric_score(self, mock_issue):
        repo = MagicMock()
        repo.get_issues.return_value = [mock_issue]

        grading = Grading()
        score = grading.parse_score_from_issue(repo, "checkpoint")
        assert score == 8.5

    def test_ignores_comment_lines(self):
        """Score lines with [comment] should be skipped."""
        issue = MagicMock()
        issue.title = "Checkpoint Feedback"
        issue.body = (
            "[comment]: # (Score = ...)\n"
            "Score = 9.0\n"
        )
        repo = MagicMock()
        repo.get_issues.return_value = [issue]

        grading = Grading()
        score = grading.parse_score_from_issue(repo, "checkpoint")
        assert score == 9.0

    def test_raises_on_missing_score(self):
        issue = MagicMock()
        issue.title = "Checkpoint Feedback"
        issue.body = "No score here\nJust feedback"
        issue.url = "https://example.com"
        repo = MagicMock()
        repo.get_issues.return_value = [issue]

        grading = Grading()
        with pytest.raises(ValueError, match="Score Parse Error"):
            grading.parse_score_from_issue(repo, "checkpoint")


class TestCheckGraded:
    def test_graded_returns_true(self, mock_issue):
        repo = MagicMock()
        repo.get_issues.return_value = [mock_issue]

        grading = Grading()
        assert grading.check_graded(repo, "checkpoint") is True

    def test_ungraded_returns_false(self, mock_ungraded_issue):
        repo = MagicMock()
        repo.get_issues.return_value = [mock_ungraded_issue]

        grading = Grading()
        assert grading.check_graded(repo, "checkpoint") is False


class TestUpdateCanvasScore:
    def test_posts_grade_to_all_members(self, mock_issue):
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"Team_Alpha": ["alice", "bob"]}
        cg.email_to_canvas_id = {"alice": 101, "bob": 102}

        grading = Grading(cg=cg)
        grading.update_canvas_score(
            group_name="Team_Alpha",
            assignment_id=42,
            score=8.5,
            issue=mock_issue,
            post=True,
        )
        cg.link_assignment.assert_called_once_with(42)
        assert cg.post_grade.call_count == 2

    def test_dry_run_does_not_post(self, capsys):
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"Team_Alpha": ["alice"]}
        cg.email_to_canvas_id = {"alice": 101}

        grading = Grading(cg=cg)
        grading.update_canvas_score(
            group_name="Team_Alpha",
            assignment_id=42,
            score=8.5,
            post=False,
        )
        cg.post_grade.assert_not_called()
        captured = capsys.readouterr()
        assert "Post Disable" in captured.out

    def test_includes_issue_url_in_comment(self, mock_issue):
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"Team_Alpha": ["alice"]}
        cg.email_to_canvas_id = {"alice": 101}

        grading = Grading(cg=cg)
        grading.update_canvas_score(
            group_name="Team_Alpha",
            assignment_id=42,
            score=8.5,
            issue=mock_issue,
            post=True,
        )
        # Verify the comment includes the GitHub URL (not API URL)
        call_args = cg.post_grade.call_args
        assert "github.com" in call_args[1]["text_comment"]


class TestGradeProject:
    def test_full_grading_workflow(self, mock_ungraded_issue):
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"team-alpha": ["alice"]}
        cg.email_to_canvas_id = {"alice": 101}

        repo = MagicMock()
        repo.name = "team-alpha"
        repo.get_issues.return_value = [mock_ungraded_issue]

        grading = Grading(cg=cg)
        grading.grade_project(
            repo=repo,
            component="checkpoint",
            assignment_id=42,
            post=True,
        )
        cg.link_assignment.assert_called_once_with(42)

    def test_skips_already_graded(self, mock_issue):
        """check_graded returns True -> grade_project returns early."""
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"team-alpha": ["alice"]}

        repo = MagicMock()
        repo.name = "team-alpha"
        repo.get_issues.return_value = [mock_issue]

        grading = Grading(cg=cg)
        # check_graded will return True since score is 8.5 (not Ellipsis)
        grading.grade_project(
            repo=repo,
            component="checkpoint",
            assignment_id=42,
            post=True,
        )
        # Should return early without posting
        cg.link_assignment.assert_not_called()

    def test_uses_canvas_group_name_mapping(self, mock_ungraded_issue):
        cg = MagicMock()
        cg.group_category = MagicMock()
        cg.group_to_emails = {"Canvas Team Alpha": ["alice"]}
        cg.email_to_canvas_id = {"alice": 101}

        repo = MagicMock()
        repo.name = "github-team-alpha"
        repo.get_issues.return_value = [mock_ungraded_issue]

        grading = Grading(cg=cg)
        grading.grade_project(
            repo=repo,
            component="checkpoint",
            assignment_id=42,
            canvas_group_name={"github-team-alpha": "Canvas Team Alpha"},
            post=True,
        )
        cg.link_assignment.assert_called_once_with(42)

    def test_sets_group_category_if_provided(self, mock_ungraded_issue):
        cg = MagicMock()
        cg.group_category = None
        cg.group_to_emails = {"team-alpha": ["alice"]}
        cg.email_to_canvas_id = {"alice": 101}

        # Simulate set_group_category actually setting the attribute
        def _set_gc(name):
            cg.group_category = MagicMock(name=name)
        cg.set_group_category.side_effect = _set_gc

        repo = MagicMock()
        repo.name = "team-alpha"
        repo.get_issues.return_value = [mock_ungraded_issue]

        grading = Grading(cg=cg)
        grading.grade_project(
            repo=repo,
            component="checkpoint",
            assignment_id=42,
            canvas_group_category="Project Groups",
            post=True,
        )
        cg.set_group_category.assert_called_once_with("Project Groups")
