__all__ = ["bcolors", "Grading"]

from . import *
import github
import canvasapi
from ast import literal_eval


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Grading:
    """Orchestrate grading between GitHub and Canvas LMS.

    Bridges GitHub issue-based grading workflows with Canvas grade
    posting. Parses scores from GitHub issue templates and pushes them
    to the corresponding Canvas assignment for each group member.

    Attributes:
        ghg: An authenticated GitHubGroup instance.
        cg: An authenticated CanvasGroup instance.
    """

    def __init__(
        self,
        ghg: GitHubGroup = None,  # authenticated GitHub object
        cg: CanvasGroup = None,  # authenticated canvas object
    ):
        """Initialize a Grading instance with GitHub and Canvas clients.

        Args:
            ghg: An authenticated GitHubGroup instance for GitHub
                operations.
            cg: An authenticated CanvasGroup instance for Canvas
                operations.
        """
        self.ghg = ghg
        self.cg = cg

    def create_issue_from_md(
        self,
        repo: github.Repository.Repository,  # target repository to create issue
        md_fp: str,  # file path of the feedback markdown file
    ) -> github.Issue.Issue:  # open issue
        """Create a GitHub issue from a markdown file.

        Delegates to the underlying GitHubGroup instance to read the
        markdown file and create an issue in the target repository.

        Args:
            repo: The target GitHub repository.
            md_fp: File path to the feedback markdown file.

        Returns:
            The newly created GitHub issue object.
        """
        return self.ghg.create_issue_from_md(repo, md_fp)

    def fetch_issue(
        self,
        repo: github.Repository.Repository,  # target repository to fetch issue
        component: str,  # the component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
    ) -> github.Issue.Issue:
        """Fetch a specific issue by matching the component name in its title.

        Searches all issues in the repository and returns the first one
        whose title contains the component string (case-insensitive).

        Args:
            repo: The target GitHub repository to search.
            component: The grading component name (e.g., ``"proposal"``,
                ``"checkpoint"``, ``"final"``). Must match a substring
                of the issue title.

        Returns:
            The matching GitHub issue object.

        Raises:
            ValueError: If no issue title contains the component string.
        """
        for issue in list(repo.get_issues()):
            if component.lower() in issue.title.lower():
                return issue
        raise ValueError(f"Issue related to {component} did not found.")

    def parse_score_from_issue(
        self,
        repo: github.Repository.Repository,  # target repository to create issue
        component: str,  # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
    ) -> int:  # the fetched score of that component
        """Parse the numeric score from a GitHub issue grading template.

        Fetches the issue matching the given component and scans its
        body for a line containing ``"Score ="`` to extract the grade.

        Args:
            repo: The target GitHub repository.
            component: The grading component name (e.g., ``"proposal"``,
                ``"checkpoint"``, ``"final"``).

        Returns:
            The parsed integer score from the issue body.

        Raises:
            ValueError: If the issue is not found or no valid
                ``"Score ="`` line is present.
        """
        issue = self.fetch_issue(repo, component)
        body = issue.body
        score = 0
        for line in body.split("\n"):
            if "Score =" in line and "[comment]" not in line:
                score = literal_eval(line.split("=")[1])
                return score
        raise ValueError(
            f"Score Parse Error. please check the score format on github. \n"
            f"Issue URL: {issue.url}"
        )

    def update_canvas_score(
        self,
        group_name: str,  # target group name on a canvas group
        assignment_id,  # assignment id of the related component
        score: float,  # score of that component
        issue: github.Issue.Issue = None,
        post=False,  # whether to post score via api. for testing purposes
    ):
        """Post a score to Canvas for all members of a group.

        Links the assignment, iterates over every member in the
        specified group, and posts the score with an optional comment
        linking to the GitHub issue.

        Args:
            group_name: The Canvas group name whose members should
                receive the grade.
            assignment_id: The Canvas assignment ID for the grading
                component.
            score: The numeric score to post.
            issue: Optional GitHub issue object. If provided, its URL
                is included in the submission comment.
            post: If True, actually post the grade via the Canvas API.
                If False (default), only print what would be posted.

        Raises:
            ValueError: If the CanvasGroup's group category is not set.
        """
        if self.cg.group_category is None:
            raise ValueError("CanvasGroup's group_category not set.")
        members = self.cg.group_to_emails[group_name]
        self.cg.link_assignment(assignment_id)
        for member in members:
            student_id = self.cg.email_to_canvas_id[member]
            text_comment = f"Group: {group_name}"
            if issue is not None:
                text_comment += f"\nView at {issue.url.replace('https://api.github.com/repos', 'https://github.com')}"
            if post:
                self.cg.post_grade(
                    student_id=student_id, grade=score, text_comment=text_comment
                )
            else:
                print(f"{bcolors.WARNING}Post Disable{bcolors.ENDC}")
                print(f"For student: {member}, the score is {score}")
                print(f"Comments: {text_comment}")

    def check_graded(
        self,
        repo: github.Repository.Repository,  # target repository to grade
        component: str,  # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
    ) -> bool:  # Whether the repo is graded.
        """Check if a project component has been graded.

        Parses the score from the GitHub issue template. If the score
        is the Ellipsis sentinel (``...``), the component is considered
        ungraded.

        Args:
            repo: The target GitHub repository.
            component: The grading component name (e.g., ``"proposal"``,
                ``"checkpoint"``, ``"final"``).

        Returns:
            True if the component has a numeric score, False if the
            score is the Ellipsis sentinel.
        """
        score = self.parse_score_from_issue(repo, component)
        if score is ...:
            print(
                f"{bcolors.WARNING}{repo.name}'s {component} Not Graded. {bcolors.ENDC}"
            )
            return False
        print(f"{bcolors.OKGREEN}{repo.name}'s {component} Graded. {bcolors.ENDC}")
        return True

    def grade_project(
        self,
        repo: github.Repository.Repository,  # target repository to grade
        component: str,  # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
        assignment_id: int,  # assignment id that link to that component of the project
        canvas_group_name: dict = None,  # mapping from GitHub repo name to Group name. If not specified, the repository name will be used.
        canvas_group_category: str = None,  # canvas group category (set)
        post: bool = False,  # whether to post score via api. For testing purposes
    ):
        """Grade a project component end-to-end.

        Parses the score from the GitHub issue, maps the repository to
        a Canvas group, checks whether the component is already graded,
        and posts the score to Canvas if it has not been graded yet.

        Args:
            repo: The target GitHub repository to grade.
            component: The grading component name (e.g., ``"proposal"``,
                ``"checkpoint"``, ``"final"``).
            assignment_id: The Canvas assignment ID for this component.
            canvas_group_name: Optional dict mapping GitHub repo names
                to Canvas group names. If None, the repo name is used
                as the group name.
            canvas_group_category: Optional Canvas group category name.
                If provided, it is set before grading.
            post: If True, post the grade via the Canvas API. If False
                (default), only print what would be posted.
        """
        # set the category if you haven't
        if canvas_group_category is not None:
            self.cg.set_group_category(canvas_group_category)
        score = self.parse_score_from_issue(repo, component)
        # create mapping from GitHub repo name to canvas group name
        if canvas_group_name is not None:
            group_name = canvas_group_name[repo.name]
        else:
            group_name = repo.name
        graded = self.check_graded(repo, component)
        if graded:
            return
        issue = self.fetch_issue(repo, component)
        self.update_canvas_score(group_name, assignment_id, score, issue, post)
