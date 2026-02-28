# Authentication

CanvasGroupy requires API tokens for both Canvas LMS and GitHub. These are stored in a JSON credentials file.

## Credentials file

Create a `credentials.json` file:

```json
{
    "Canvas Token": "your-canvas-api-token",
    "GitHub Token": "your-github-personal-access-token"
}
```

!!! warning "Keep your credentials safe"
    Never commit `credentials.json` to version control. Add it to your `.gitignore`.

## Canvas API Token

1. Log in to your Canvas instance (e.g., `https://canvas.ucsd.edu`)
2. Go to **Account > Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Give it a purpose (e.g., "CanvasGroupy") and generate
6. Copy the token into your `credentials.json`

## GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Select scopes: `repo`, `admin:org`, `read:org`
4. Generate and copy the token into your `credentials.json`

## Usage

```python
from CanvasGroupy import CanvasGroup, GitHubGroup

# Authenticate Canvas
cg = CanvasGroup(credentials_fp="credentials.json",
                 API_URL="https://canvas.ucsd.edu")

# Authenticate GitHub
ghg = GitHubGroup(credentials_fp="credentials.json", org="MyOrg")
```
