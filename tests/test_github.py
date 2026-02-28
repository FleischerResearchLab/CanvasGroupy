"""Tests for CanvasGroupy.github — GitHubGroup class."""

import json
import os
import pytest
from unittest.mock import MagicMock, patch, call
from CanvasGroupy.github import GitHubGroup


class TestAuthGitHub:
    def test_auth_loads_token(self, credentials, mock_github_api):
        MockGithub, github_instance, _ = mock_github_api
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        MockGithub.assert_called_once_with("fake-github-token")
        assert ghg.github is not None

    def test_auth_missing_file_raises(self):
        ghg = GitHubGroup(verbosity=0)
        with pytest.raises(FileNotFoundError):
            ghg.auth_github("/nonexistent/path.json")

    def test_set_org(self, credentials, mock_github_api):
        _, github_instance, mock_org = mock_github_api
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")

        github_instance.get_organization.assert_called_once_with("TestOrg")
        assert ghg.org.login == "TestOrg"


class TestRepoOperations:
    def _setup_ghg(self, credentials, mock_github_api):
        _, _, mock_org = mock_github_api
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")
        return ghg, mock_org

    def test_create_blank_repo(self, credentials, mock_github_api):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)
        mock_repo = MagicMock()
        mock_repo.name = "new-repo"
        mock_org.create_repo.return_value = mock_repo

        result = ghg.create_repo("new-repo", private=True, description="test")
        mock_org.create_repo.assert_called_once_with(
            name="new-repo", private=True, description="test"
        )
        assert result.name == "new-repo"

    def test_create_repo_from_template(self, credentials, mock_github_api):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)
        _, github_instance, _ = mock_github_api

        template_repo = MagicMock()
        github_instance.get_repo.return_value = template_repo

        new_repo = MagicMock()
        mock_org.create_repo_from_template.return_value = new_repo

        result = ghg.create_repo("new-repo", repo_template="owner/template")
        mock_org.create_repo_from_template.assert_called_once()
        assert result == new_repo

    def test_get_repo(self, credentials, mock_github_api):
        ghg, _ = self._setup_ghg(credentials, mock_github_api)
        _, github_instance, _ = mock_github_api

        mock_repo = MagicMock()
        github_instance.get_repo.return_value = mock_repo

        result = ghg.get_repo("owner/repo")
        github_instance.get_repo.assert_called_with("owner/repo")
        assert result == mock_repo

    def test_get_repo_falls_back_to_org(self, credentials, mock_github_api):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)
        _, github_instance, _ = mock_github_api

        github_instance.get_repo.side_effect = Exception("Not found")
        org_repo = MagicMock()
        mock_org.get_repo.return_value = org_repo

        result = ghg.get_repo("some-repo")
        assert result == org_repo


class TestCollaborators:
    def test_add_collaborator(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        ghg.add_collaborator(repo, "new-user", "write")
        repo.add_to_collaborators.assert_called_once_with("new-user", "write")

    def test_remove_collaborator(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        ghg.remove_collaborator(repo, "old-user")
        repo.remove_from_collaborators.assert_called_once_with("old-user")

    def test_add_collaborator_handles_failure(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        repo.add_to_collaborators.side_effect = Exception("Permission denied")
        # Should not raise — prints warning and continues
        ghg.add_collaborator(repo, "bad-user", "write")


class TestTeamOperations:
    def test_get_team(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")

        _, _, mock_org = mock_github_api
        mock_team = MagicMock()
        mock_team.name = "instructors"
        mock_org.get_team_by_slug.return_value = mock_team

        result = ghg.get_team("instructors")
        assert result.name == "instructors"

    def test_get_team_raises_without_org(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        # org not set
        with pytest.raises(ValueError):
            ghg.get_team("instructors")

    def test_add_team_to_repo(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")

        _, _, mock_org = mock_github_api
        mock_team = MagicMock()
        mock_org.get_team_by_slug.return_value = mock_team

        repo = MagicMock()
        ghg.add_team(repo, "instructors", "admin")
        mock_team.add_to_repos.assert_called_once_with(repo)
        mock_team.update_team_repository.assert_called_once_with(repo, "admin")


class TestFileOperations:
    def test_rename_files(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        mock_file = MagicMock()
        mock_file.decoded_content = b"file content"
        mock_file.sha = "abc123"
        repo.get_contents.return_value = mock_file

        ghg.rename_files(repo, "old_name.txt", "new_name.txt")
        repo.get_contents.assert_called_once_with("old_name.txt")
        repo.create_file.assert_called_once_with(
            "new_name.txt", "rename files", b"file content"
        )
        repo.delete_file.assert_called_once_with(
            "old_name.txt", "delete old files", "abc123"
        )

    def test_create_feedback_dir(self, credentials, mock_github_api, tmp_path):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        # Create template files
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "feedback.md").write_text("# Feedback\nScore = ...")
        (template_dir / "rubric.md").write_text("# Rubric\n...")

        repo = MagicMock()
        repo.name = "team-alpha"

        dest = str(tmp_path / "feedback")
        ghg.create_feedback_dir(repo, str(template_dir), destination=dest)

        assert os.path.exists(f"{dest}/team-alpha/feedback.md")
        assert os.path.exists(f"{dest}/team-alpha/rubric.md")


class TestIssues:
    def test_create_issue(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        mock_issue = MagicMock()
        repo.create_issue.return_value = mock_issue

        result = ghg.create_issue(repo, "Bug Report", "There is a bug")
        repo.create_issue.assert_called_once_with(
            title="Bug Report", body="There is a bug"
        )
        assert result == mock_issue

    def test_create_issue_from_md(self, credentials, mock_github_api, tmp_path):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        md_file = tmp_path / "feedback.md"
        md_file.write_text("# Checkpoint Feedback\n\nGreat work on the project.")

        repo = MagicMock()
        mock_issue = MagicMock()
        repo.create_issue.return_value = mock_issue

        result = ghg.create_issue_from_md(repo, str(md_file))
        # Title should be first line without "# "
        repo.create_issue.assert_called_once()
        args = repo.create_issue.call_args
        assert args[1]["title"] == "Checkpoint Feedback"

    def test_release_feedback(self, credentials, mock_github_api, tmp_path):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")

        _, _, mock_org = mock_github_api

        # Create feedback structure
        feedback_dir = tmp_path / "feedback"
        (feedback_dir / "team-alpha").mkdir(parents=True)
        (feedback_dir / "team-alpha" / "checkpoint.md").write_text(
            "# Checkpoint Feedback\nScore = 8.5"
        )

        mock_repo = MagicMock()
        mock_org.get_repo.return_value = mock_repo

        ghg.release_feedback("checkpoint.md", feedback_dir=str(feedback_dir))
        mock_org.get_repo.assert_called_with("team-alpha")
        mock_repo.create_issue.assert_called_once()

    def test_release_feedback_skips_missing_repos(
        self, credentials, mock_github_api, tmp_path
    ):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")

        _, _, mock_org = mock_github_api

        # Create feedback structure with two repos
        feedback_dir = tmp_path / "feedback"
        (feedback_dir / "missing-repo").mkdir(parents=True)
        (feedback_dir / "missing-repo" / "checkpoint.md").write_text("# Feedback\n")
        (feedback_dir / "good-repo").mkdir(parents=True)
        (feedback_dir / "good-repo" / "checkpoint.md").write_text("# Feedback\n")

        good_repo = MagicMock()
        good_repo.name = "good-repo"

        def get_repo_side_effect(name):
            if name == "missing-repo":
                raise Exception("Not found")
            return good_repo

        mock_org.get_repo.side_effect = get_repo_side_effect

        # Should not raise; should skip missing-repo and still process good-repo
        ghg.release_feedback("checkpoint.md", feedback_dir=str(feedback_dir))
        good_repo.create_issue.assert_called_once()


class TestResendInvitations:
    def test_resend_invitations(self, credentials, mock_github_api):
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)

        repo = MagicMock()
        invite = MagicMock()
        invite.id = 1
        invite.invitee.login = "pending-user"
        invite.permissions = "write"
        repo.get_pending_invitations.return_value = [invite]

        result = ghg.resend_invitations(repo)
        repo.remove_invitation.assert_called_once_with(1)
        repo.add_to_collaborators.assert_called_once()
        assert len(result) == 1


class TestCreateGroupRepo:
    def _setup_ghg(self, credentials, mock_github_api):
        _, _, mock_org = mock_github_api
        ghg = GitHubGroup(verbosity=0)
        ghg.auth_github(credentials)
        ghg.set_org("TestOrg")
        return ghg, mock_org

    @patch("time.sleep", return_value=None)
    def test_creates_repo_and_adds_collaborators(
        self, mock_sleep, credentials, mock_github_api
    ):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)

        mock_repo = MagicMock()
        mock_repo.name = "team-alpha"
        mock_org.create_repo.return_value = mock_repo

        result = ghg.create_group_repo(
            repo_name="team-alpha",
            collaborators=["user1", "user2"],
            permission="write",
            private=True,
        )
        assert result == mock_repo
        assert mock_repo.add_to_collaborators.call_count == 2

    @patch("time.sleep", return_value=None)
    def test_creates_from_template_with_renames(
        self, mock_sleep, credentials, mock_github_api
    ):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)
        _, github_instance, _ = mock_github_api

        template = MagicMock()
        github_instance.get_repo.return_value = template

        mock_repo = MagicMock()
        mock_repo.name = "team-alpha"
        mock_file = MagicMock()
        mock_file.decoded_content = b"content"
        mock_file.sha = "sha123"
        mock_repo.get_contents.return_value = mock_file
        mock_org.create_repo_from_template.return_value = mock_repo

        result = ghg.create_group_repo(
            repo_name="team-alpha",
            collaborators=["user1"],
            permission="write",
            repo_template="owner/template",
            rename_files={"old.txt": "new.txt"},
        )
        mock_repo.get_contents.assert_called_with("old.txt")
        mock_repo.create_file.assert_called_once()

    @patch("time.sleep", return_value=None)
    def test_adds_team_when_specified(self, mock_sleep, credentials, mock_github_api):
        ghg, mock_org = self._setup_ghg(credentials, mock_github_api)

        mock_repo = MagicMock()
        mock_org.create_repo.return_value = mock_repo

        mock_team = MagicMock()
        mock_org.get_team_by_slug.return_value = mock_team

        ghg.create_group_repo(
            repo_name="team-alpha",
            collaborators=[],
            permission="write",
            team_slug="instructors",
            team_permission="admin",
        )
        mock_team.add_to_repos.assert_called_once_with(mock_repo)
        mock_team.update_team_repository.assert_called_once_with(mock_repo, "admin")
