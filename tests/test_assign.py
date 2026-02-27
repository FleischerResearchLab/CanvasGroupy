import pytest
import pandas as pd
from unittest.mock import MagicMock
from CanvasGroupy.assign import AssignGroup


@pytest.fixture
def mock_services():
    ghg = MagicMock()
    cg = MagicMock()
    return ghg, cg


class TestAssignGroupFromDataFrame:
    def test_load_groups_from_dataframe(self, mock_services):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        df = pd.DataFrame({
            "group_name": ["Group1", "Group1", "Group2", "Group2"],
            "student_id": ["alice", "bob", "carol", "dave"],
        })
        ag.load_groups(df)
        assert ag.groups == {
            "Group1": ["alice", "bob"],
            "Group2": ["carol", "dave"],
        }

    def test_load_groups_from_csv(self, mock_services, tmp_path):
        ghg, cg = mock_services
        ag = AssignGroup(ghg=ghg, cg=cg)
        csv_path = tmp_path / "groups.csv"
        csv_path.write_text("group_name,student_id\nGroup1,alice\nGroup1,bob\nGroup2,carol\n")
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
