__all__ = ['bcolors', 'GitHubGroup']

from github import Github
import github
import json
import time
import os
import glob
from pprint import pprint

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class GitHubGroup:
    """Manage GitHub organization repositories, teams, and collaborators.

    Provides methods to authenticate with GitHub, create repositories
    (blank or from templates), manage collaborators and teams, create
    issues, and release feedback to student groups.

    Attributes:
        github: Authenticated PyGithub client.
        org: The target GitHub organization object.
        verbosity: Controls output verbosity (0 = silent, 1 = print status).
    """

    def __init__(self,
                 credentials_fp="", # the file path to the credential json
                 org="", # the organization name
                 verbosity=1 # Controls the verbosity: 0=silent, 1=print status
                ):
        """Initialize a GitHubGroup instance and optionally authenticate.

        Args:
            credentials_fp: Path to the JSON credentials file containing
                a ``"GitHub Token"`` key.
            org: The GitHub organization name to target.
            verbosity: Controls output verbosity (0 = silent, 1 = print
                status).
        """
        self.github = None
        self.org = None
        self.verbosity = verbosity

        if credentials_fp != "":
            self.auth_github(credentials_fp)
        if org != "":
            self.set_org(org)

    def auth_github(self,
                    credentials_fp: str # the personal access token generated at GitHub Settings
                   ):
        """Authenticate with GitHub using a credentials file.

        Reads the GitHub personal access token from the JSON credentials
        file and initializes the PyGithub client. Verifies the token by
        fetching the authenticated user's repositories.

        Args:
            credentials_fp: Path to the JSON file containing a
                ``"GitHub Token"`` key.

        Raises:
            FileNotFoundError: If the credentials file does not exist.
            github.GithubException: If the token is invalid.
        """
        with open(credentials_fp, "r") as f:
            token = json.load(f)["GitHub Token"]
        self.github = Github(token)
        # check authorization
        _ = self.github.get_user().get_repos()[0]
        if self.verbosity != 0:
            print(f"Successfully Authenticated. "
                  f"GitHub account: {bcolors.OKGREEN} {self.github.get_user().login} {bcolors.ENDC}")

    def set_org(self,
                org: str # the target organization name
               ):
        """Set the target GitHub organization.

        Retrieves the organization object by name and stores it for
        subsequent repository and team operations.

        Args:
            org: The GitHub organization login name.

        Raises:
            github.UnknownObjectException: If the organization does not
                exist.
        """
        self.org = self.github.get_organization(org)
        if self.verbosity != 0:
            print(f"Target Organization Set: {bcolors.OKGREEN} {self.org.login} {bcolors.ENDC}")

    def create_repo(self,
                    repo_name: str, # repository name
                    repo_template="", # template repository that new repo will use. If empty string, an empty repo will be created. Put in the format of "<owner>/<repo>"
                    private=True, # visibility of the created repository
                    description="", # description for the GitHub repository
                    personal_account=False, # create repos in personal GitHub account
                    ) -> github.Repository.Repository:
        """Create a repository, either blank or from a template.

        Creates a new repository under the target organization (or
        personal account). If ``repo_template`` is provided, the new
        repository is created from that template.

        Args:
            repo_name: Name for the new repository.
            repo_template: Full name of the template repository in
                ``"owner/repo"`` format. If empty, a blank repo is
                created.
            private: Whether the repository should be private.
            description: Description for the repository.
            personal_account: If True, create under the authenticated
                user's personal account instead of the organization.

        Returns:
            The newly created GitHub repository object.

        Raises:
            ValueError: If the organization is not set and
                ``personal_account`` is True.
        """
        if self.org is None and personal_account:
            raise ValueError("Organization is not set")
        if personal_account:
            parent = self.github.get_user()
        else:
            parent = self.org
        if repo_template == "":
            return parent.create_repo(
                name=repo_name,
                private=private,
                description=description
            )
        # create from template
        return parent.create_repo_from_template(
            name=repo_name,
            repo=self.get_repo(repo_template),
            private=private,
            description=description,
        )

    def get_repo(self,
                 repo_full_name: str # full name of the target repository
                ) -> github.Repository.Repository:
        """Get a repository by its full name.

        Attempts to fetch the repository directly by full name. If that
        fails, falls back to searching within the organization.

        Args:
            repo_full_name: Full name of the repository (e.g.,
                ``"owner/repo"``).

        Returns:
            The GitHub repository object.

        Raises:
            github.UnknownObjectException: If the repository cannot be
                found.
        """
        try:
            return self.github.get_repo(repo_full_name)
        except Exception:
            return self.org.get_repo(repo_full_name)

    def get_org_repo(self,
                     repo_full_name: str # full name of the target repository
                    ) -> github.Repository.Repository:
        """Get a repository within the target organization.

        Args:
            repo_full_name: Name of the repository within the
                organization.

        Returns:
            The GitHub repository object.

        Raises:
            github.UnknownObjectException: If the repository is not
                found in the organization.
        """
        return self.org.get_repo(repo_full_name)


    def get_team(self,
                 team_slug:str # team slug of the team
                ) -> github.Team.Team:
        """Get a team by its slug within the target organization.

        Args:
            team_slug: The URL-friendly slug of the team.

        Returns:
            The GitHub team object.

        Raises:
            ValueError: If the organization has not been set.
            github.UnknownObjectException: If the team slug is not found.
        """
        if self.org is None:
            raise ValueError("The organization has not been set. Please set it via g.set_org")
        return self.org.get_team_by_slug(team_slug)

    def rename_files(self,
                     repo: github.Repository.Repository, # the repository that we want to rename file
                     og_filename: str, # old file name
                     new_filename: str # new file name
                    ):
        """Rename a file in a repository by creating a copy and deleting the original.

        This performs a rename by committing the file content under the
        new name and then deleting the old file in separate commits.

        Args:
            repo: The repository containing the file.
            og_filename: The current file path in the repository.
            new_filename: The desired new file path.
        """
        file = repo.get_contents(og_filename)
        repo.create_file(new_filename, "rename files", file.decoded_content)
        repo.delete_file(og_filename, "delete old files", file.sha)
        if self.verbosity != 0:
            print(f"File Successfully Renamed from "
                  f" {bcolors.OKCYAN} {og_filename} {bcolors.ENDC} "
                  f" to {bcolors.OKGREEN} {new_filename} {bcolors.ENDC}")

    def add_collaborator(self,
                          repo: github.Repository.Repository, # target repository
                          collaborator:str, # GitHub username of the collaborator
                          permission:str # `pull`, `push` or `admin`
                         ):
        """Add a collaborator to a repository with the specified permission.

        Args:
            repo: The target GitHub repository.
            collaborator: GitHub username of the collaborator to add.
            permission: Permission level -- ``"pull"``, ``"push"``, or
                ``"admin"``.
        """
        try:
            repo.add_to_collaborators(collaborator, permission)
        except Exception as e:
            print(f"{bcolors.WARNING}Add Failed for {collaborator}{bcolors.ENDC}")
        if self.verbosity != 0:
            print(f"Added Collaborator: {bcolors.OKGREEN} {collaborator} {bcolors.ENDC}"
                  f" to: {bcolors.OKGREEN} {repo.name} {bcolors.ENDC} with "
                  f"permission: {bcolors.OKGREEN} {permission} {bcolors.ENDC}")

    def remove_collaborator(self,
                            repo: github.Repository.Repository, # target repository
                            collaborator:str, # GitHub username of the collaborator
                           ):
        """Remove a collaborator from a repository.

        Args:
            repo: The target GitHub repository.
            collaborator: GitHub username of the collaborator to remove.
        """
        repo.remove_from_collaborators(collaborator)

    def resend_invitations(self,
                          repo: github.Repository.Repository, # target repository
                         ) -> [github.NamedUser.NamedUser]: # list of re-invited user
        """Resend pending collaboration invitations for a repository.

        Revokes each pending invitation and re-invites the user with
        the same permissions, effectively resending the email.

        Args:
            repo: The target GitHub repository.

        Returns:
            A list of user objects whose invitations were resent.
        """
        pendings = list(repo.get_pending_invitations())
        users = [p.invitee for p in pendings]
        if self.verbosity != 0:
            print("The list of pending invitation:")
            pprint(users)
        for p in pendings:
            repo.remove_invitation(p.id)
            if self.verbosity != 0:
                print(f"{bcolors.WARNING}{bcolors.UNDERLINE}{p.invitee.login}{bcolors.ENDC} {bcolors.FAIL}Invite Revoked {bcolors.ENDC}")
            self.add_collaborator(repo, p.invitee.login, p.permissions)
            if self.verbosity != 0:
                print(f"{bcolors.OKGREEN} Invite Resent to {p.invitee.login} {bcolors.ENDC}")
        return users

    def resent_invitations_team_repos(self,
                                      team_slug: str # team slug (name) under the org
                                     ):
        """Resend pending invitations for all repositories under a team.

        Iterates over every repository associated with the team and
        resends any pending collaboration invitations.

        Args:
            team_slug: The URL-friendly slug of the team whose repos
                should have invitations resent.
        """
        team = self.get_team(team_slug)
        repos = team.get_repos()
        for repo in repos:
            if self.verbosity != 0:
                print(f"Repository {bcolors.OKCYAN} {repo.name} {bcolors.ENDC}:")
            try:
                _ = self.resend_invitations(repo)
            except Exception as e:
                print(f"{bcolors.WARNING}Make sure to have proper rights to the target repo{bcolors.ENDC}\n")
                print(e)

    def add_team(self,
                  repo: github.Repository.Repository, # target repository
                  team_slug: str, # team slug (name)
                  permission:str # `pull`, `push` or `admin`
                 ):
        """Add a team to a repository with the specified permission.

        Args:
            repo: The target GitHub repository.
            team_slug: The URL-friendly slug of the team to add.
            permission: Permission level -- ``"pull"``, ``"push"``, or
                ``"admin"``.
        """
        team = self.get_team(team_slug)
        team.add_to_repos(repo)
        team.update_team_repository(repo, permission)
        if self.verbosity != 0:
            print(f"Team {bcolors.OKGREEN} {team.name} {bcolors.ENDC} "
                  f"added to {bcolors.OKGREEN} {repo.name} {bcolors.ENDC} "
                  f"with permission {bcolors.OKGREEN} {permission} {bcolors.ENDC}")

    def create_feedback_dir(self,
                            repo: github.Repository.Repository, # target repository
                            template_fp: str,
                            destination="feedback" # directory path of the template file.
                           ):
        """Create a local feedback directory populated from template files.

        Copies all files from the template directory into a
        repo-specific subdirectory under the destination path.

        Args:
            repo: The target repository (used for naming the
                subdirectory).
            template_fp: Path to the directory containing template files.
            destination: Base directory where feedback subdirectories
                are created.
        """
        os.makedirs(destination, exist_ok=True)
        os.makedirs(f"{destination}/{repo.name}", exist_ok=True)
        files = glob.glob(f"{template_fp}/*")
        for file in files:
            head = os.path.split(file)[1]
            with open(file, "r") as f:
                file = f.read()
            with open(f"{destination}/{repo.name}/{head}", "w+") as f:
                f.write(file)
            if self.verbosity != 0:
                print(f"File {bcolors.OKGREEN}{head}{bcolors.ENDC} "
                      f"created at {bcolors.OKGREEN}{destination}/{repo.name}{bcolors.ENDC}"
                     )

    def create_issue(self,
                     repo: github.Repository.Repository, # target repository
                     title: str, # title of the issue,
                     content: str # content of the issue
                    ) -> github.Issue.Issue: # open issue
        """Create a GitHub issue in the target repository.

        Args:
            repo: The target GitHub repository.
            title: Title of the issue.
            content: Body content of the issue (supports Markdown).

        Returns:
            The newly created GitHub issue object.
        """
        issue = repo.create_issue(title=title, body=content)
        if self.verbosity != 0:
            print(f"In the repo: {bcolors.OKGREEN}{repo.name}{bcolors.ENDC},")
            print(f"Issue {bcolors.OKGREEN}{title}{bcolors.ENDC} Created!")
        return issue

    def create_issue_from_md(self,
                             repo: github.Repository.Repository, # target repository,
                             md_fp: str # file path of the feedback markdown file
                            ) -> github.Issue.Issue: # open issue
        """Create a GitHub issue from a markdown file.

        Reads the markdown file, uses the first line (without the ``#``
        prefix) as the issue title, and the full file content as the
        issue body.

        Args:
            repo: The target GitHub repository.
            md_fp: File path to the feedback markdown file.

        Returns:
            The newly created GitHub issue object.
        """
        md = ""
        with open(md_fp, "r") as f:
            md = f.read()
        title = md.split("\n")[0][2:]
        content = md
        return self.create_issue(repo, title, content)

    def release_feedback(self,
                         md_filename: str, # feedback markdown file name
                         feedback_dir="feedback", # feedback directory contains the markdown files
                        ):
        """Release feedback via GitHub issues to all groups.

        Iterates over every subdirectory in the feedback directory,
        treats each subdirectory name as a repository name within the
        organization, and creates an issue from the specified markdown
        file.

        Args:
            md_filename: Name of the markdown file within each repo's
                feedback subdirectory (e.g., ``"checkpoint.md"``).
            feedback_dir: Path to the base feedback directory containing
                per-repo subdirectories.
        """
        repo_names = os.listdir(feedback_dir)
        for repo_name in repo_names:
            if repo_name == ".DS_Store":
                continue
            try:
                repo = self.org.get_repo(repo_name)
            except Exception:
                print(f"Repo: {bcolors.WARNING}{repo_name} NOT FOUND!{bcolors.ENDC}")
            self.create_issue_from_md(repo, os.path.join(feedback_dir, repo_name, md_filename))

    def create_group_repo(self,
                          repo_name: str, # group repository name
                          collaborators: [str], # list of collaborators GitHub id
                          permission: str, # the permission of collaborators. `pull`, `push` or `admin`
                          rename_files=dict(), # dictionary of files renames {<og_name>:<new_name>}
                          repo_template="", # If empty string, an empty repo will be created. Put in the format of "<owner>/<repo>"
                          private=True, # visibility of the created repository
                          description="", # description for the GitHub repository
                          team_slug="", # team slug, add to this repo
                          team_permission="", # team permission to this repository `pull`, `push` or `admin`
                          feedback_dir=False, # whether to create a feedback directory for each repository created
                          feedback_template_fp="", # the directory of the feedback template
                         ) -> github.Repository.Repository: # created repository
        """Create a group repository with collaborators and team permissions.

        Creates a repository (optionally from a template), renames files
        if specified, adds collaborators, assigns a team, and optionally
        creates a local feedback directory.

        Args:
            repo_name: Name for the new group repository.
            collaborators: List of GitHub usernames to add as
                collaborators.
            permission: Permission level for collaborators --
                ``"pull"``, ``"push"``, or ``"admin"``.
            rename_files: Dictionary mapping old filenames to new
                filenames for renaming after creation.
            repo_template: Full name of the template repository in
                ``"owner/repo"`` format. If empty, a blank repo is
                created.
            private: Whether the repository should be private.
            description: Description for the repository.
            team_slug: Team slug to add to the repository. If empty,
                no team is added.
            team_permission: Permission level for the team --
                ``"pull"``, ``"push"``, or ``"admin"``.
            feedback_dir: If True, create a local feedback directory
                for this repository.
            feedback_template_fp: Path to the feedback template
                directory. Required when ``feedback_dir`` is True.

        Returns:
            The newly created GitHub repository object.

        Raises:
            ValueError: If ``feedback_dir`` is True but
                ``feedback_template_fp`` is empty.
        """
        repo = self.create_repo(repo_name, repo_template, private, description)
        if self.verbosity != 0:
            print(f"Repo {bcolors.OKGREEN} {repo.name} {bcolors.ENDC} Created... Wait for 3 sec to updates")
        time.sleep(3)
        for og_name, new_name in rename_files.items():
            self.rename_files(repo, og_name, new_name)
        for collaborator in collaborators:
            self.add_collaborator(repo, collaborator, permission)
        if team_slug != "":
            self.add_team(repo, team_slug, team_permission)
        if self.verbosity != 0:
            print(f"Group Repo: {bcolors.OKGREEN} {repo_name} {bcolors.ENDC} successfuly created!")
            print(f"Repo URL: https://github.com/{self.org.login}/{repo_name}")
        if feedback_dir:
            if feedback_template_fp == "":
                raise ValueError("You have to specify the template files.")
            self.create_feedback_dir(repo, template_fp=feedback_template_fp)
        return repo
