"""Tests for CanvasGroupy.canvas — CanvasGroup class."""

import json
import pytest
from unittest.mock import MagicMock, patch, call
from CanvasGroupy.canvas import CanvasGroup


class TestAuthCanvas:
    def test_auth_loads_token_and_creates_canvas(self, credentials, mock_canvas_api):
        MockCanvas, canvas_instance, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)

        MockCanvas.assert_called_once_with(
            "https://canvas.ucsd.edu", "fake-canvas-token"
        )
        canvas_instance.get_activity_stream_summary.assert_called_once()
        assert cg.API_KEY == "fake-canvas-token"

    def test_auth_with_missing_file_raises(self):
        cg = CanvasGroup(verbosity=0)
        with pytest.raises(FileNotFoundError):
            cg.auth_canvas("/nonexistent/path.json")

    def test_auth_with_bad_keys_raises(self, bad_credentials):
        cg = CanvasGroup(verbosity=0)
        with patch("CanvasGroupy.canvas.Canvas"):
            with pytest.raises(KeyError):
                cg.auth_canvas(bad_credentials)

    def test_custom_api_url(self, credentials):
        with patch("CanvasGroupy.canvas.Canvas") as MockCanvas:
            MockCanvas.return_value = MagicMock()
            cg = CanvasGroup(API_URL="https://custom.canvas.edu", verbosity=0)
            cg.auth_canvas(credentials)
            MockCanvas.assert_called_once_with(
                "https://custom.canvas.edu", "fake-canvas-token"
            )


class TestSetCourse:
    def test_set_course_fetches_students(self, credentials, mock_canvas_api):
        _, canvas_instance, mock_course = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)

        canvas_instance.get_course.assert_called_once_with(99999)
        mock_course.get_users.assert_called_once_with(enrollment_type=["student"])
        assert cg.email_to_canvas_id["alice"] == 101
        assert cg.canvas_id_to_email[101] == "alice"
        assert cg.email_to_name["alice"] == "Alice Smith"
        assert len(cg.email_to_canvas_id) == 3

    def test_set_course_skips_users_without_email(self, credentials):
        with patch("CanvasGroupy.canvas.Canvas") as MockCanvas:
            canvas_instance = MagicMock()
            MockCanvas.return_value = canvas_instance
            canvas_instance.get_activity_stream_summary.return_value = {}

            # One user has no email attribute
            good_user = MagicMock()
            good_user.email = "alice@ucsd.edu"
            good_user.id = 101
            good_user.short_name = "Alice"

            bad_user = MagicMock(spec=[])  # no email attribute
            bad_user.short_name = "Ghost"

            mock_course = MagicMock()
            mock_course.get_users.return_value = [good_user, bad_user]
            canvas_instance.get_course.return_value = mock_course

            cg = CanvasGroup(verbosity=0)
            cg.auth_canvas(credentials)
            cg.set_course(99999)
            assert len(cg.email_to_canvas_id) == 1


class TestGetEmailByName:
    def test_finds_by_first_name(self, credentials, mock_canvas_api):
        _, _, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)
        assert cg.get_email_by_name("alice") == "alice"

    def test_case_insensitive(self, credentials, mock_canvas_api):
        _, _, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)
        assert cg.get_email_by_name("ALICE") == "alice"

    def test_raises_on_not_found(self, credentials, mock_canvas_api):
        _, _, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)
        with pytest.raises(ValueError, match="Not Found"):
            cg.get_email_by_name("nobody")


class TestGroupOperations:
    def _setup_cg(self, credentials, mock_canvas_api):
        """Helper: return a fully-initialized CanvasGroup."""
        _, _, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)
        return cg

    def test_get_group_categories(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        cats = cg.get_group_categories()
        assert "Project Groups" in cats

    def test_set_group_category(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        result = cg.set_group_category("Project Groups")
        assert result.name == "Project Groups"
        assert "Team_Alpha" in cg.group_to_emails

    def test_set_group_category_raises_on_missing(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        with pytest.raises(KeyError):
            cg.set_group_category("Nonexistent Category")

    def test_get_groups_after_set(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        cg.set_group_category("Project Groups")
        groups = cg.get_groups()
        assert isinstance(groups, dict)
        assert "Team_Alpha" in groups

    def test_get_groups_raises_without_category(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        with pytest.raises(ValueError):
            cg.get_groups()

    def test_create_group_category(self, credentials, mock_canvas_api):
        _, _, mock_course = mock_canvas_api
        new_cat = MagicMock()
        new_cat.name = "New Category"
        mock_course.create_group_category.return_value = new_cat

        cg = self._setup_cg(credentials, mock_canvas_api)
        result = cg.create_group_category({"name": "New Category"})
        mock_course.create_group_category.assert_called_once_with(name="New Category")
        assert result.name == "New Category"

    def test_create_group(self, credentials, mock_canvas_api, mock_group_category):
        cg = self._setup_cg(credentials, mock_canvas_api)
        cg.set_group_category("Project Groups")

        new_group = MagicMock()
        new_group.name = "Team_Beta"
        mock_group_category.create_group.return_value = new_group

        result = cg.create_group({"name": "Team_Beta"})
        assert result.name == "Team_Beta"

    def test_create_group_raises_without_category(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        with pytest.raises(ValueError):
            cg.create_group({"name": "Team_Beta"})

    def test_join_canvas_group(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        group = MagicMock()
        unsuccessful = cg.join_canvas_group(group, ["alice", "bob"])
        assert group.create_membership.call_count == 2
        assert unsuccessful == []

    def test_join_canvas_group_returns_failures(self, credentials, mock_canvas_api):
        cg = self._setup_cg(credentials, mock_canvas_api)
        group = MagicMock()
        unsuccessful = cg.join_canvas_group(group, ["alice", "nonexistent_student"])
        assert "nonexistent_student" in unsuccessful

    def test_assign_canvas_group_creates_and_joins(
        self, credentials, mock_canvas_api, mock_group_category
    ):
        cg = self._setup_cg(credentials, mock_canvas_api)

        new_group = MagicMock()
        mock_group_category.create_group.return_value = new_group

        result_group, unsuccessful = cg.assign_canvas_group(
            group_name="Team_Beta",
            group_members=["alice", "bob"],
            in_group_category="Project Groups",
        )
        assert result_group == new_group
        assert new_group.create_membership.call_count == 2


class TestGradePosting:
    def _setup_cg_with_assignment(self, credentials, mock_canvas_api):
        _, _, mock_course = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)

        mock_assignment = MagicMock()
        mock_assignment.name = "Homework 1"
        mock_course.get_assignment.return_value = mock_assignment

        cg.link_assignment(42)
        return cg, mock_assignment

    def test_link_assignment(self, credentials, mock_canvas_api):
        _, _, mock_course = mock_canvas_api
        mock_assignment = MagicMock()
        mock_assignment.name = "Homework 1"
        mock_course.get_assignment.return_value = mock_assignment

        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)
        result = cg.link_assignment(42)

        mock_course.get_assignment.assert_called_once_with(42)
        assert result.name == "Homework 1"

    def test_post_grade(self, credentials, mock_canvas_api):
        cg, mock_assignment = self._setup_cg_with_assignment(
            credentials, mock_canvas_api
        )

        mock_submission = MagicMock()
        mock_submission.score = 0  # different from new grade
        mock_assignment.get_submission.return_value = mock_submission

        cg.post_grade(student_id=101, grade=95.0, text_comment="Great work")
        mock_submission.edit.assert_called_once_with(
            submission={"posted_grade": 95.0},
            comment={"text_comment": "Great work"},
        )

    def test_post_grade_skips_same_score(self, credentials, mock_canvas_api):
        cg, mock_assignment = self._setup_cg_with_assignment(
            credentials, mock_canvas_api
        )

        mock_submission = MagicMock()
        mock_submission.score = 95.0  # same as new grade
        mock_assignment.get_submission.return_value = mock_submission

        result = cg.post_grade(student_id=101, grade=95.0)
        mock_submission.edit.assert_not_called()
        assert result is None

    def test_post_grade_force_overrides_skip(self, credentials, mock_canvas_api):
        cg, mock_assignment = self._setup_cg_with_assignment(
            credentials, mock_canvas_api
        )

        mock_submission = MagicMock()
        mock_submission.score = 95.0  # same score, but force=True
        mock_assignment.get_submission.return_value = mock_submission

        cg.post_grade(student_id=101, grade=95.0, force=True)
        mock_submission.edit.assert_called_once()


class TestConversation:
    def test_create_conversation(self, credentials, mock_canvas_api):
        _, canvas_instance, _ = mock_canvas_api
        cg = CanvasGroup(verbosity=0)
        cg.auth_canvas(credentials)
        cg.set_course(99999)

        cg.create_conversation(
            recipients=101,
            subject="Test Subject",
            body="Test Body",
        )
        canvas_instance.create_conversation.assert_called_once_with(
            [101],
            body="Test Body",
            subject="Test Subject",
            context_code="course_99999",
        )
