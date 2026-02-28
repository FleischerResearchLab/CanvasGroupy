__all__ = ["bcolors", "CanvasGroup"]

from canvasapi import Canvas
from github import Github
import canvasapi
import json
import requests
import time
import sys
import numpy as np
import pandas as pd
from io import StringIO


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


class CanvasGroup:
    """Manage Canvas LMS group operations including roster, grading, and messaging.

    Provides methods to authenticate with the Canvas API, manage courses and
    group categories, create and populate groups, post grades, and send
    messages to students.

    Attributes:
        API_URL: The Canvas instance base URL.
        canvas: Authenticated Canvas API client.
        course: The currently selected Canvas course.
        group_category: The active group category (group set).
        users: List of enrolled students in the course.
        assignment: The currently linked assignment for grading.
        verbosity: Controls output verbosity (0 = silent, 1 = print all).
    """

    def __init__(
        self,
        credentials_fp="",  # credential file path. See docs/getting-started/authentication.md for the template.
        API_URL="https://canvas.ucsd.edu",  # the domain name of canvas
        course_id="",  # Course ID, can be found in the course url
        group_category="",  # target group category (set) of interests
        verbosity=1,  # Controls the verbosity: 0 = Silent, 1 = print all messages
    ):
        """Initialize a CanvasGroup instance and optionally authenticate and configure.

        Args:
            credentials_fp: Path to the credentials JSON file containing API
                tokens. See the template at the project repository.
            API_URL: The Canvas instance base URL (e.g., ``https://canvas.ucsd.edu``).
            course_id: The Canvas course ID, found in the course URL.
            group_category: Name of the target group category (group set).
            verbosity: Controls output verbosity (0 = silent, 1 = print all).
        """
        self.API_URL = API_URL
        self.canvas = None
        self.course = None
        self.group_category = None
        self.group_categories = None
        self.groups = None
        self.users = None
        self.email_to_canvas_id = None
        self.canvas_id_to_email = None
        self.email_to_name = None
        self.API_KEY = None
        self.github = None
        self.credentials_fp = None
        self.groups = None
        self.group_to_emails = None
        self.assignment = None
        self.verbosity = verbosity

        # initialize by the input parameter
        if credentials_fp != "":
            self.auth_canvas(credentials_fp)
        if course_id != "":
            self.set_course(course_id)
            self.get_group_categories()
        if group_category != "":
            self.set_group_category(group_category)

    def auth_canvas(
        self, credentials_fp: str  # the Authenticator key generated from canvas
    ):
        """Authenticate with the Canvas API using a credentials file.

        Reads the Canvas API token from the JSON credentials file and
        initializes the Canvas API client. Verifies the token by fetching
        the activity stream summary.

        Args:
            credentials_fp: Path to the JSON file containing a
                ``"Canvas Token"`` key.

        Raises:
            FileNotFoundError: If the credentials file does not exist.
            canvasapi.exceptions.InvalidAccessToken: If the token is invalid.
        """
        self.credentials_fp = credentials_fp
        with open(credentials_fp, "r") as f:
            credentials = json.load(f)
        self.API_KEY = credentials["Canvas Token"]
        self.canvas = Canvas(self.API_URL, self.API_KEY)
        # test authorization
        _ = self.canvas.get_activity_stream_summary()
        if self.verbosity != 0:
            print(f"{bcolors.OKGREEN}Authorization Successful!{bcolors.ENDC}")

    def set_course(self, course_id: int):  # the course id of the target course
        """Set the target course and fetch the student roster.

        Retrieves the course by ID, fetches all enrolled students, and
        builds lookup dictionaries mapping emails to Canvas IDs and names.

        Args:
            course_id: The numeric Canvas course ID.

        Raises:
            canvasapi.exceptions.ResourceDoesNotExist: If the course ID is
                invalid.
        """
        self.course = self.canvas.get_course(course_id)
        if self.verbosity != 0:
            print(f"Course Set: {bcolors.OKGREEN} {self.course.name} {bcolors.ENDC}")
            print(f"Getting List of Users... This might take a while...")
        self.users = list(self.course.get_users(enrollment_type=["student"]))
        if self.verbosity != 0:
            print(
                f"Users Fetch Complete! The course has {bcolors.OKBLUE}{len(self.users)}{bcolors.ENDC} students."
            )
        self.email_to_canvas_id = {}
        self.canvas_id_to_email = {}
        self.email_to_name = {}
        for u in self.users:
            try:
                self.email_to_canvas_id[u.email.split("@")[0]] = u.id
                self.canvas_id_to_email[u.id] = u.email.split("@")[0]
                self.email_to_name[u.email.split("@")[0]] = u.short_name
            except Exception:
                if self.verbosity != 0:
                    print(
                        f"{bcolors.WARNING}Failed to Parse email and id"
                        f" for {bcolors.UNDERLINE}{u.short_name}{bcolors.ENDC}{bcolors.ENDC}"
                    )

    def link_assignment(
        self, assignment_id: int  # assignment id, found at the url of assignmnet tab
    ) -> canvasapi.assignment.Assignment:  # target assignment
        """Link a Canvas assignment for grading.

        Fetches the assignment by ID and stores it for subsequent grading
        operations such as ``post_grade``.

        Args:
            assignment_id: The Canvas assignment ID, found in the
                assignment URL.

        Returns:
            The linked Canvas assignment object.

        Raises:
            canvasapi.exceptions.ResourceDoesNotExist: If the assignment ID
                is invalid.
        """
        assignment = self.course.get_assignment(assignment_id)
        if self.verbosity != 0:
            print(f"Assignment {bcolors.OKGREEN+assignment.name+bcolors.ENDC} Link!")
        self.assignment = assignment
        return assignment

    def post_grade(
        self,
        student_id: int,  # canvas student id of student. found in self.email_to_canvas_id
        grade: float,  # grade of that assignment
        text_comment="",  # text comment of the submission. Can feed
        force=False,  # whether force to post grade for all students. If False (default), it will skip post for the same score.
    ) -> canvasapi.submission.Submission:  # created submission
        """Post a grade and optional comment to the linked Canvas assignment.

        Submits a grade for a specific student on the currently linked
        assignment. If ``force`` is False and the existing score matches
        the new grade, the submission is skipped.

        Args:
            student_id: The Canvas user ID of the student, obtainable
                from ``self.email_to_canvas_id``.
            grade: The numeric grade to post.
            text_comment: An optional text comment to attach to the
                submission.
            force: If False (default), skip posting when the existing
                score already matches ``grade``.

        Returns:
            The updated submission object, or None if the post was
            skipped.
        """
        submission = self.assignment.get_submission(student_id)
        if not force and submission.score == grade:
            if self.verbosity != 0:
                print(
                    f"Grade for {bcolors.OKGREEN+self.canvas_id_to_email[student_id]+bcolors.ENDC} did not change.\n"
                    f"{bcolors.OKCYAN}Skipped{bcolors.ENDC}.\n"
                )
            return
        edited = submission.edit(
            submission={"posted_grade": grade}, comment={"text_comment": text_comment}
        )
        if self.verbosity != 0:
            print(
                f"Grade for {bcolors.OKGREEN+self.canvas_id_to_email[student_id]+bcolors.ENDC} Posted!"
            )
        return edited

    def get_email_by_name(
        self, name_fussy: str  # search by first name or last name of a student
    ) -> str:  # email of a search student
        """Look up a student's email prefix by a partial name match.

        Performs a case-insensitive substring search against all student
        names in the roster and returns the first matching email prefix.

        Args:
            name_fussy: A partial or full student name to search for
                (first name, last name, or substring).

        Returns:
            The email prefix (SIS Login ID) of the first matching student.

        Raises:
            ValueError: If no student name contains the search string.
        """
        name_fussy = name_fussy.lower()
        for email, name in self.email_to_name.items():
            if name_fussy in name.lower():
                return email
        raise ValueError(f"Name {name_fussy} Not Found.")

    def set_group_category(
        self, category_name: str  # the target group category
    ) -> canvasapi.group.GroupCategory:  # target group category object
        """Set the active group category and fetch its groups.

        Selects a group category (group set) by name and retrieves all
        groups and their member email lists within that category.

        Args:
            category_name: The exact name of the group category to
                activate.

        Returns:
            The selected group category object.

        Raises:
            KeyError: If ``category_name`` does not match any existing
                group category in the course.
        """
        _ = self.get_group_categories()
        try:
            self.group_category = self.group_categories[category_name]
        except KeyError:
            raise KeyError(
                f"{category_name} did not found in the group categories. "
                f"Try to create one with CanvasGroup.create_group_category"
            )
        if self.verbosity != 0:
            print(f"Setting Group Category... ")
        self.groups = list(self.group_category.get_groups())
        self.group_to_emails = {
            group.name: [u.login_id for u in list(group.get_users())]
            for group in self.groups
        }
        if self.verbosity != 0:
            print(f"Group Category: {bcolors.OKGREEN+category_name+bcolors.ENDC} Set!")
        return self.group_category

    def get_groups(
        self,
        category_name="",  # the target group category. If not provided, will look for self.group_category
    ) -> dict:  # {group_name: [student_emails]}
        """Get groups and their members in the current or specified category.

        Returns a dictionary mapping group names to lists of member email
        prefixes. If ``category_name`` is provided, the category is set
        first.

        Args:
            category_name: Optional group category name. If empty, uses
                the currently active group category.

        Returns:
            A dict mapping group names to lists of student email prefixes.

        Raises:
            ValueError: If no group category is set and ``category_name``
                is empty.
        """
        if category_name != "":
            self.set_group_category(category_name)
            return self.group_to_emails
        if self.group_category is None:
            raise ValueError("Group Category is not set")
        return self.group_to_emails

    def get_course(self):
        """Get the current course object.

        Returns:
            The currently selected Canvas course object, or None if no
            course has been set.
        """
        return self.course

    def get_group_categories(self) -> dict:  # return a name / group category object
        """List all group categories (group sets) in the current course.

        Fetches every group category from the Canvas course and caches
        them in ``self.group_categories``.

        Returns:
            A dict mapping category names to their GroupCategory objects.
        """
        categories = list(self.course.get_group_categories())
        self.group_categories = {cat.name: cat for cat in categories}
        return {cat.name: cat for cat in categories}

    def create_group_category(
        self,
        params: dict,  # the parameter of canvas group category API @ [this link](https://canvas.instructure.com/doc/api/group_categories.html#method.group_categories.create)
    ) -> canvasapi.group.GroupCategory:  # the generated group category object
        """Create a new group category (group set) in the current course.

        Args:
            params: A dictionary of parameters for the Canvas group
                category API. See the Canvas API documentation for
                ``group_categories.create``.

        Returns:
            The newly created group category object.
        """
        self.group_category = self.course.create_group_category(**params)
        return self.group_category

    def create_group(
        self,
        params: dict,  # the parameter of canvas group create API at [this link](https://canvas.instructure.com/doc/api/groups.html#method.groups.create)
    ) -> canvasapi.group.Group:  # the generated target group object
        """Create a group under the currently active group category.

        Args:
            params: A dictionary of parameters for the Canvas group
                creation API, which must include a ``"name"`` key. See
                the Canvas API documentation for ``groups.create``.

        Returns:
            The newly created group object.

        Raises:
            ValueError: If no group category has been set or created.
        """
        if self.group_category is None:
            raise ValueError(
                "Have you specified or create a group category (group set)?"
            )
        group = self.group_category.create_group(**params)
        if self.verbosity != 0:
            print(
                f"In Group Set: {bcolors.OKBLUE+self.group_category.name+bcolors.ENDC},"
            )
            print(f"Group {bcolors.OKGREEN+params['name']+bcolors.ENDC} Created!")
        return group

    def join_canvas_group(
        self,
        group: canvasapi.group.Group,  # the group that students will join
        group_members: [
            str
        ],  # list of group member's SIS Login (email prefix, before the @.)
    ) -> [str]:  # list of unsuccessful join
        """Add students to a Canvas group by their email prefixes.

        Iterates over the provided member list and creates a group
        membership for each student. Students whose email prefixes are
        not found in the roster are collected and returned.

        Args:
            group: The Canvas group object to add members to.
            group_members: List of student SIS Login IDs (email prefixes,
                the part before the ``@``).

        Returns:
            A list of email prefixes for students who could not be added.
        """
        unsuccessful_join = []
        for group_member in group_members:
            try:
                canvas_id = self.email_to_canvas_id[group_member]
                group.create_membership(canvas_id)
                if self.verbosity != 0:
                    print(
                        f"Member {bcolors.OKGREEN}{group_member}{bcolors.ENDC} Joined group {bcolors.OKGREEN}{group.name}{bcolors.ENDC}"
                    )
            except KeyError as e:
                unsuccessful_join.append(group_member)
                print(
                    f"Error adding student {bcolors.WARNING+group_member+bcolors.ENDC} \n into group {group.name}"
                )
                print(e)
        return unsuccessful_join

    def fetch_username_from_quiz(
        self,
        quiz_id: int,  # quiz id of the username quiz
        col_index=7,  # canvas quiz generated csv's question field column index
    ) -> dict:  # {SIS Login ID: github username} dictionary
        """Extract GitHub usernames from a Canvas quiz student analysis.

        Downloads the student analysis report for the specified quiz,
        parses the CSV, and builds a mapping from student email prefixes
        to their submitted GitHub usernames.

        Args:
            quiz_id: The Canvas quiz ID containing GitHub username
                submissions.
            col_index: The zero-based column index in the generated CSV
                that contains the GitHub username question response.

        Returns:
            A dict mapping student email prefixes (SIS Login IDs) to
            their submitted GitHub usernames.
        """
        header = {"Authorization": "Bearer " + self.API_KEY}
        quiz = self.course.get_quiz(quiz_id)
        if self.verbosity != 0:
            print(
                f"Quiz: {bcolors.OKGREEN+quiz.title+bcolors.ENDC} "
                f"fetch! \nGenerating Student Analaysis..."
            )
        report = quiz.create_report("student_analysis")
        progress_url = report.progress_url
        completed = False
        while not completed:
            status = requests.get(progress_url, headers=header).json()
            if self.verbosity != 0:
                self._progress(status["completion"])
                time.sleep(0.1)
            if status["completion"] == 100:
                completed = True
        if self.verbosity != 0:
            print(f"\n{bcolors.OKGREEN}Report Generated!{bcolors.ENDC}")
        # use requests to download the file
        file_url = quiz.create_report("student_analysis").file["url"]
        response = requests.get(file_url, headers=header)
        file = StringIO(response.content.decode())
        # use pandas to parse the response csv
        df = pd.read_csv(file, delimiter=",")
        col = list(df.columns)
        # rename column
        if self.verbosity != 0:
            print(
                f"The Question asked is {bcolors.OKBLUE}{col[col_index]}{bcolors.ENDC}. \n"
                f"Make sure this is the correct question where you asked student for their GitHub id.\n"
                f"If you need to change the index of columns, change the col_index argument of this call."
            )
        col[col_index] = "GitHub Username"
        df.columns = col
        small = df[["id", "GitHub Username"]].copy()
        small["email"] = small["id"].apply(lambda x: self.canvas_id_to_email[x])
        small = small[["email", "GitHub Username"]].set_index("email")
        return small.to_dict()["GitHub Username"]

    def _check_single_github_username(
        self,
        email: str,  # Student email
        github_username: str,  # student input we want to test
    ) -> bool:  # whether the username is valid
        "Check a single GitHub username on GitHub"
        if self.credentials_fp is None:
            raise ValueError("Credentials not set. Set it via self.auth_canvas")
        if self.github is None:
            # if the GitHub object has not been initialized
            with open(self.credentials_fp, "r") as f:
                credentials = json.load(f)
            github_token = credentials["GitHub Token"]
            self.github = Github(github_token)
        try:
            self.github.get_user(github_username)
        except Exception as e:
            print(
                f"User: {bcolors.WARNING+github_username+bcolors.ENDC} Not Found on GitHub"
            )
            return False
        return True

    def check_github_usernames(
        self,
        github_usernames: dict,  # {email: github username} of student inputs, generated from self.fetch_username_from_quiz
        send_canvas_email=False,  # whether send a reminder for students who have an invalid GitHub username
        send_undone_reminder=False,  # send quiz undone reminder using canvas email
        quiz_url="",  # include a quiz url in the conversation for student to quickly complete the quiz.
    ) -> dict:  # {email: github username} of unreasonable GitHub id
        """Batch validate GitHub usernames and optionally notify students.

        Checks each GitHub username against the GitHub API. Optionally
        sends Canvas messages to students with invalid usernames and to
        students who have not yet submitted the quiz.

        Args:
            github_usernames: A dict mapping email prefixes to GitHub
                usernames, typically from ``fetch_username_from_quiz``.
            send_canvas_email: If True, send a Canvas notification to
                students with invalid GitHub usernames.
            send_undone_reminder: If True, send a Canvas reminder to
                students who have not submitted the quiz.
            quiz_url: URL of the quiz to include in reminder messages.

        Returns:
            A dict of email prefixes to GitHub usernames that could not
            be validated on GitHub.
        """
        unsuccessful = {}
        for email, github_username in github_usernames.items():
            valid = self._check_single_github_username(email, github_username)
            if not valid:
                unsuccessful[email] = github_username
                if send_canvas_email:
                    self.create_conversation(
                        self.email_to_canvas_id[email],
                        subject="Unidentifiable GitHub Username",
                        body=(
                            f"Hi {email}, \n Your GitHub Username: {github_username} "
                            f"is unidentifiable on github.com. \n Please complete the quiz GitHub Username Quiz again.\n"
                            f"{quiz_url} \n"
                            f"Thank You."
                        ),
                    )
                    if self.verbosity != 0:
                        print(f"{bcolors.OKGREEN}Notification Sent!{bcolors.ENDC}")
        if send_undone_reminder:
            submitted = github_usernames.keys()
            for email in self.email_to_canvas_id.keys():
                if email not in submitted:
                    if self.verbosity != 0:
                        print(
                            f"Student {bcolors.WARNING}{email}{bcolors.ENDC} did not"
                            f" submit their github username."
                        )
                    # means student did not submit the quiz
                    if send_canvas_email:
                        self.create_conversation(
                            self.email_to_canvas_id[email],
                            subject="GitHub Username Quiz Not Completed",
                            body=(
                                f"Hi {email}, \n You did not complete the GitHub Quiz."
                                f"\n Please complete the quiz GitHub Username Quiz ASAP\n"
                                f"{quiz_url} \n"
                                f"Thank You."
                            ),
                        )
                        if self.verbosity != 0:
                            print(f"{bcolors.OKGREEN}Notification Sent!{bcolors.ENDC}")
        return unsuccessful

    def _progress(self, percentage: int):  # percentage of the progress
        sys.stdout.write("\r")
        # the exact output you're looking for:
        sys.stdout.write("[%-20s] %d%%" % ("=" * int(percentage // 5), percentage))
        sys.stdout.flush()

    def assign_canvas_group(
        self,
        group_name: str,  # group name, display on canvas
        group_members: [str],  # list of group member's SIS Login
        in_group_category: str,  # specify which group category the group belongs to
    ) -> (canvasapi.group.Group, [str]):  # list of unsuccessful join
        """Create a Canvas group and assign members to it.

        Sets the group category, creates a new group, and adds the
        specified students as members.

        Args:
            group_name: Display name for the new group on Canvas.
            group_members: List of student SIS Login IDs (email prefixes).
            in_group_category: Name of the group category (group set)
                the new group belongs to.

        Returns:
            A tuple of (created group object, list of email prefixes
            for students who could not be added).
        """
        self.set_group_category(in_group_category)
        group = self.create_group({"name": group_name})
        unsuccessful_join = self.join_canvas_group(group, group_members)
        if self.verbosity != 0:
            print(f"Group {bcolors.OKGREEN+group_name+bcolors.ENDC} created!")
        return group, unsuccessful_join

    def create_conversation(
        self,
        recipients: int,  #  recipient ids. These may be user ids or course/group ids prefixed with 'course_' or 'group_' respectively.
        subject: str,  # subject of the conversation
        body: str,  # The message to be sent
    ) -> canvasapi.conversation.Conversation:  # created conversation
        """Send a Canvas message (conversation) to a student.

        Creates a new conversation in the context of the current course.

        Args:
            recipients: Recipient Canvas user ID, or a course/group ID
                prefixed with ``'course_'`` or ``'group_'``.
            subject: Subject line of the conversation.
            body: The message body text.

        Returns:
            The created Canvas conversation object.
        """
        conv = self.canvas.create_conversation(
            [recipients],
            body=body,
            subject=subject,
            context_code=f"course_{self.course.id}",
        )
        return conv
