# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/04_project_grading.ipynb.

# %% auto 0
__all__ = ['bcolors', 'Grading']

# %% ../nbs/api/04_project_grading.ipynb 3
from . import *
import github
import canvasapi
from ast import literal_eval

# %% ../nbs/api/04_project_grading.ipynb 4
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

# %% ../nbs/api/04_project_grading.ipynb 5
class Grading:
    def __init__(self,
                 ghg:GitHubGroup=None, # authenticated GitHub object
                 cg:CanvasGroup=None, # authenticated canvas object
                ):
        self.ghg = ghg
        self.cg = cg

    def create_issue_from_md(self,
                              repo:github.Repository.Repository, # target repository to create issue
                              md_fp: str # file path of the feedback markdown file
                              ) -> github.Issue.Issue: # open issue
        "Create GitHub issue from markdown file."
        return self.ghg.create_issue_from_md(repo, md_fp)

    def fetch_issue(self,
                    repo:github.Repository.Repository, # target repository to fetch issue
                    component:str, # the component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
                    ) -> github.Issue.Issue:
        "Fetch the issue on GitHub repo and choose related one"
        for issue in list(repo.get_issues()):
            if component.lower() in issue.title.lower():
                return issue
        raise ValueError(f"Issue related to {component} did not found.")

    def parse_score_from_issue(self,
                               repo:github.Repository.Repository, # target repository to create issue
                               component:str, # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
                               ) -> int: # the fetched score of that component
        "parse score from the template issue"
        issue = self.fetch_issue(repo, component)
        body = issue.body
        score = 0
        for line in body.split("\n"):
            if "Score =" in line and "[comment]" not in line:
                score = literal_eval(line.split("=")[1])
                return score
        raise ValueError(f"Score Parse Error. please check the score format on github. \n"
                         f"Issue URL: {issue.url}")

    def update_canvas_score(self,
                            group_name:str, # target group name on a canvas group
                            assignment_id, # assignment id of the related component
                            score:float, # score of that component
                            issue:github.Issue.Issue=None,
                            post=False, # whether to post score via api. for testing purposes
                            ):
        "Post score to canvas"
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
                    student_id=student_id,
                    grade=score,
                    text_comment=text_comment
                )
            else:
                print(f"{bcolors.WARNING}Post Disable{bcolors.ENDC}")
                print(f"For student: {member}, the score is {score}")
                print(f"Comments: {text_comment}")

    def check_graded(self,
                     repo:github.Repository.Repository, # target repository to grade
                     component:str, # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
                    ) -> bool: # Whether the repo is graded.
        "Check whether a component for a group project is graded"
        score = self.parse_score_from_issue(repo, component)
        if score is ...:
            print(f"{bcolors.WARNING}{repo.name}'s {component} Not Graded. {bcolors.ENDC}")
            return False
        print(f"{bcolors.OKGREEN}{repo.name}'s {component} Graded. {bcolors.ENDC}")
        return True

    def grade_project(self,
                      repo:github.Repository.Repository, # target repository to grade
                      component:str, # The component of the project grading, let it be proposal/checkpoint/final. Need to match the issue's title
                      assignment_id:int, # assignment id that link to that component of the project
                      canvas_group_name:dict=None, # mapping from GitHub repo name to Group name. If not specified, the repository name will be used.
                      canvas_group_category:str=None, # canvas group category (set)
                      post:bool=False, # whether to post score via api. For testing purposes
                      ):
        "grade github project components"
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


