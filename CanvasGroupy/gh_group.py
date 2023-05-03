# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/02_gh_group_creation.ipynb.

# %% auto 0
__all__ = ['bcolors', 'GitHubGroup']

# %% ../nbs/api/02_gh_group_creation.ipynb 3
from github import Github
import github
import json
import time
import os
import glob
from pprint import pprint

# %% ../nbs/api/02_gh_group_creation.ipynb 4
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

# %% ../nbs/api/02_gh_group_creation.ipynb 5
class GitHubGroup:
    def __init__(self,
                 credentials_fp="", # the file path to the credential json
                 org="", # the organization name
                 verbosity=0 # Controls the verbosity: 0=slient, 1=print status
                ):
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
        "Authenticate GitHub account with the provided credentials"
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
        "Set the target organization for repo creation"
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
        "Create a repository, either blank, or from a template"
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
        # create from templatez
        return parent.create_repo_from_template(
            name=repo_name,
            repo=self.get_repo(repo_template),
            private=private,
            description=description,
        )
    
    def get_repo(self,
                 repo_full_name: str # full name of the target repository
                ) -> github.Repository.Repository:
        "To get a repository by its name"
        return self.github.get_repo(repo_full_name)
    
    def get_org_repo(self,
                     repo_full_name: str # full name of the target repository
                    ) -> github.Repository.Repository:
        "Get a repository within the target organization"
        return self.org.get_repo(repo_full_name)

    
    def get_team(self,
                 team_slug:str # team slug of the team
                ) -> github.Team.Team:
        "Get the team inside the target organization"
        if self.org is None:
            raise ValueError("The organization has not been set. Please set it via g.set_org")
        return self.org.get_team_by_slug(team_slug)
    
    def rename_files(self,
                     repo: github.Repository.Repository, # the repository that we want to rename file
                     og_filename: str, # old file name
                     new_filename: str # new file name
                    ):
        "Rename the file by delete the old file and commit the new file"
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
        "Add collaborator to the repository with specified permission"
        repo.add_to_collaborators(collaborator, permission)
        if self.verbosity != 0:
            print(f"Added Collaborator: {bcolors.OKGREEN} {collaborator} {bcolors.ENDC}"
                  f" to: {bcolors.OKGREEN} {repo.name} {bcolors.ENDC} with "
                  f"permission: {bcolors.OKGREEN} {permission} {bcolors.ENDC}")
    
    def remove_collaborator(self,
                            repo: github.Repository.Repository, # target repository
                            collaborator:str, # GitHub username of the collaborator
                           ):
        "Remove collaborator privilages from the repository"
        repo.remove_from_collaborators(collaborator)
        
    def resend_invitations(self,
                          repo: github.Repository.Repository, # target repository
                         ) -> [github.NamedUser.NamedUser]: # list of re-invited user
        "Resent Invitation to invitee who did not accept the invitation"
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
        "For all repository under that team, Resent invitation to invitee who did not accept the inivtation"
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
        "Add team to the repository with specified permission"
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
        "Create feedback direcotry on local machine"
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
        "Create GitHub issue to the target repository"
        issue = repo.create_issue(title=title, body=content)
        if self.verbosity != 0:
            print(f"In the repo: {bcolors.OKGREEN}{repo.name}{bcolors.ENDC},")
            print(f"Issue {bcolors.OKGREEN}{title}{bcolors.ENDC} Created!")
        return issue
    
    def create_issue_from_md(self,
                             repo: github.Repository.Repository, # target repository,
                             md_fp: str # file path of the feedback markdown file
                            ) -> github.Issue.Issue: # open issue
        "Create GitHub issue from markdown file."
        md = ""
        with open(md_fp, "r") as f:
            md = f.read()
        title = md.split("\n")[0][1:]
        content = md
        return self.create_issue(repo, title, content)
    
    def release_feedback(self,
                         md_filename: str, # feedback markdown file name
                         feedback_dir="feedback", # feedback directory contains the markdown files
                        ):
        "Release feedback via GitHub issue from all the feedbacks in the feedback directory"
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
        "Create a Group Repository"
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
        if feedback_dir:
            if feedback_template_fp == "":
                raise ValueError("You have to specify the template files.")
            self.create_feedback_dir(repo, template_fp=feedback_template_fp)
        return repo

