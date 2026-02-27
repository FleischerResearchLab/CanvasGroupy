__all__ = ["AssignGroup"]

import os
import pandas as pd
from . import GitHubGroup, CanvasGroup


class AssignGroup:
    """Orchestrate group creation across Canvas LMS and GitHub.

    Accepts group assignments as a CSV file path or pandas DataFrame
    with columns ``group_name`` and ``student_id``, then creates
    corresponding groups on Canvas and/or GitHub.

    Args:
        ghg: Authenticated GitHubGroup instance.
        cg: Authenticated CanvasGroup instance.
        groups: Optional CSV path or DataFrame to load immediately.
    """

    def __init__(
        self,
        ghg: GitHubGroup,
        cg: CanvasGroup,
        groups=None,
    ):
        self.cg = cg
        self.ghg = ghg
        self.groups: dict[str, list[str]] = {}

        if groups is not None:
            self.load_groups(groups)

    def load_groups(self, source) -> dict[str, list[str]]:
        """Load group assignments from a CSV file path or DataFrame.

        The input must have columns ``group_name`` and ``student_id``.

        Args:
            source: A file path (str) to a CSV or a pandas DataFrame.

        Returns:
            Dictionary mapping group names to lists of student IDs.

        Raises:
            TypeError: If source is not a str or DataFrame.
            ValueError: If required columns are missing.
        """
        if isinstance(source, str):
            source = pd.read_csv(source)
        if not isinstance(source, pd.DataFrame):
            raise TypeError(
                f"Expected a file path (str) or DataFrame, got {type(source).__name__}"
            )
        for col in ("group_name", "student_id"):
            if col not in source.columns:
                raise ValueError(
                    f"Missing required column: '{col}'. "
                    f"Got columns: {list(source.columns)}"
                )
        self.groups = (
            source.groupby("group_name")["student_id"]
            .apply(list)
            .to_dict()
        )
        return self.groups

    def create_canvas_group(
        self,
        in_group_category: str = "",
        suffix: str = "",
    ):
        """Create Canvas groups from loaded group assignments.

        Args:
            in_group_category: Canvas group category name. Falls back to
                the category already set on the CanvasGroup instance.
            suffix: Suffix to append to each group name.

        Raises:
            ValueError: If no groups are loaded or no group category is set.
        """
        if not self.groups:
            raise ValueError(
                "No groups loaded. Call load_groups() first."
            )
        if self.cg.group_category is None and in_group_category == "":
            raise ValueError(
                "Specify in_group_category or set it on the CanvasGroup instance."
            )
        if in_group_category == "":
            in_group_category = self.cg.group_category.name
        for group_name, members in self.groups.items():
            self.cg.assign_canvas_group(
                group_name=f"{group_name}{suffix}",
                group_members=members,
                in_group_category=in_group_category,
            )

    def create_github_group(
        self,
        username_quiz_id: int,
    ):
        """Create GitHub repositories for each group.

        Fetches GitHub usernames from a Canvas quiz, then creates
        a repository per group with appropriate collaborators.

        Args:
            username_quiz_id: Canvas quiz ID where students submitted
                their GitHub usernames.
        """
        if not self.groups:
            raise ValueError(
                "No groups loaded. Call load_groups() first."
            )
        github_usernames = self.cg.fetch_username_from_quiz(username_quiz_id)
        repos = []
        for group_name, members in self.groups.items():
            group_git_usernames = []
            for email in members:
                try:
                    group_git_usernames.append(github_usernames[email])
                except KeyError:
                    print(f"{email}'s GitHub Username not found")
            repo = self.ghg.create_group_repo(
                repo_name=group_name,
                collaborators=group_git_usernames,
                permission="write",
                private=True,
            )
            repos.append(repo)
        return repos
