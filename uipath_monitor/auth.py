from config import Config


def authenticate(cfg: Config) -> str:
    """
    Return the Personal Access Token (PAT) from config as the bearer token.

    Generate a PAT at: cloud.uipath.com → profile icon (top-right) → My Profile
    → Personal Access Tokens → Add new token.

    Required scopes: OR.Jobs, OR.Robots, OR.Folders, OR.Monitoring (or 'All').
    """
    return cfg.pat
