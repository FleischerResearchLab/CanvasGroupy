import warnings
import pytest
import pandas as pd
from unittest.mock import MagicMock
from CanvasGroupy.assign import AssignGroup


@pytest.fixture
def mock_services():
    ghg = MagicMock()
    cg = MagicMock()
    return ghg, cg


@pytest.fixture
def loaded_ag(mock_services):
    """AssignGroup with two groups already loaded."""
    ghg, cg = mock_services
    ag = AssignGroup(ghg=ghg, cg=cg)
    df = pd.DataFrame(
        {
            "group_name": ["Group1", "Group1", "Group2"],
            "student_id": ["alice", "bob", "carol"],
        }
    )
    ag.load_groups(df)
    return ag, ghg, cg


class TestLoadGroups:
    def test_load_groups_from_dataframe(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        df = pd.DataFrame(
            {
                "group_name": ["Group1", "Group1", "Group2", "Group2"],
                "student_id": ["alice", "bob", "carol", "dave"],
            }
        )
        ag.load_groups(df)
        assert ag.groups == {
            "Group1": ["alice", "bob"],
            "Group2": ["carol", "dave"],
        }

    def test_load_groups_from_csv(self, mock_services, tmp_path):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        csv_path = tmp_path / "groups.csv"
        csv_path.write_text(
            "group_name,student_id\nGroup1,alice\nGroup1,bob\nGroup2,carol\n"
        )
        ag.load_groups(str(csv_path))
        assert ag.groups == {
            "Group1": ["alice", "bob"],
            "Group2": ["carol"],
        }

    def test_load_groups_rejects_bad_input(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        with pytest.raises(TypeError):
            ag.load_groups(12345)

    def test_load_groups_requires_columns(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        df = pd.DataFrame({"wrong_col": ["a"], "also_wrong": ["b"]})
        with pytest.raises(ValueError, match="group_name"):
            ag.load_groups(df)

    def test_constructor_groups_parameter_auto_loads(self, mock_services):
        ghg, cg = mock_services
        df = pd.DataFrame(
            {
                "group_name": ["Team1", "Team1", "Team2"],
                "student_id": ["alice", "bob", "carol"],
            }
        )
        ag = AssignGroup(ghg=ghg, cg=cg, groups=df)
        assert ag.groups == {
            "Team1": ["alice", "bob"],
            "Team2": ["carol"],
        }

    def test_load_groups_warns_on_numeric_student_ids(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        df = pd.DataFrame(
            {
                "group_name": ["Group1", "Group1"],
                "student_id": ["12345", "67890"],
            }
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ag.load_groups(df)
            assert len(w) == 1
            assert "numeric" in str(w[0].message).lower()
            assert "email prefix" in str(w[0].message).lower()


class TestCreateCanvasGroup:
    def test_calls_assign_canvas_group_for_each_group(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        cg.group_category.name = "Project Groups"
        ag.create_canvas_group()
        assert cg.assign_canvas_group.call_count == 2
        cg.assign_canvas_group.assert_any_call(
            group_name="Group1",
            group_members=["alice", "bob"],
            in_group_category="Project Groups",
        )
        cg.assign_canvas_group.assert_any_call(
            group_name="Group2",
            group_members=["carol"],
            in_group_category="Project Groups",
        )

    def test_applies_suffix_to_group_names(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        cg.group_category.name = "Project Groups"
        ag.create_canvas_group(suffix="_W25")
        cg.assign_canvas_group.assert_any_call(
            group_name="Group1_W25",
            group_members=["alice", "bob"],
            in_group_category="Project Groups",
        )

    def test_uses_explicit_group_category(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        ag.create_canvas_group(in_group_category="Custom Category")
        cg.assign_canvas_group.assert_any_call(
            group_name="Group1",
            group_members=["alice", "bob"],
            in_group_category="Custom Category",
        )

    def test_raises_when_no_groups_loaded(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        with pytest.raises(ValueError, match="No groups loaded"):
            ag.create_canvas_group(in_group_category="Anything")

    def test_works_with_group_category_none_and_explicit_category(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        cg.group_category = None
        ag.create_canvas_group(in_group_category="Explicit Category")
        assert cg.assign_canvas_group.call_count == 2
        cg.assign_canvas_group.assert_any_call(
            group_name="Group1",
            group_members=["alice", "bob"],
            in_group_category="Explicit Category",
        )
        cg.assign_canvas_group.assert_any_call(
            group_name="Group2",
            group_members=["carol"],
            in_group_category="Explicit Category",
        )


class TestCreateGitHubGroup:
    def test_calls_create_group_repo_for_each_group(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        cg.fetch_username_from_quiz.return_value = {
            "alice": "alice_gh",
            "bob": "bob_gh",
            "carol": "carol_gh",
        }
        repos = ag.create_github_group(username_quiz_id=42)
        assert ghg.create_group_repo.call_count == 2
        ghg.create_group_repo.assert_any_call(
            repo_name="Group1",
            collaborators=["alice_gh", "bob_gh"],
            permission="write",
            private=True,
        )
        ghg.create_group_repo.assert_any_call(
            repo_name="Group2",
            collaborators=["carol_gh"],
            permission="write",
            private=True,
        )
        assert len(repos) == 2

    def test_skips_missing_github_usernames(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        # bob has no GitHub username
        cg.fetch_username_from_quiz.return_value = {
            "alice": "alice_gh",
            "carol": "carol_gh",
        }
        ag.create_github_group(username_quiz_id=42)
        ghg.create_group_repo.assert_any_call(
            repo_name="Group1",
            collaborators=["alice_gh"],
            permission="write",
            private=True,
        )

    def test_raises_when_no_groups_loaded(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        with pytest.raises(ValueError, match="No groups loaded"):
            ag.create_github_group(username_quiz_id=42)

    def test_forwards_repo_kwargs_to_create_group_repo(self, loaded_ag):
        ag, ghg, cg = loaded_ag
        cg.fetch_username_from_quiz.return_value = {
            "alice": "alice_gh",
            "bob": "bob_gh",
            "carol": "carol_gh",
        }
        ag.create_github_group(
            username_quiz_id=42,
            repo_template="org/template",
            description="A project repo",
            team_slug="Instructors",
            team_permission="admin",
        )
        ghg.create_group_repo.assert_any_call(
            repo_name="Group1",
            collaborators=["alice_gh", "bob_gh"],
            permission="write",
            private=True,
            repo_template="org/template",
            description="A project repo",
            team_slug="Instructors",
            team_permission="admin",
        )
