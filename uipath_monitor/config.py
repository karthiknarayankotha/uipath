import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    account_name: str
    tenant_name: str
    pat: str
    teams_webhook_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    report_to_emails: list[str]
    report_from_email: str
    lookback_hours: int = 24

    @property
    def base_url(self) -> str:
        return f"https://cloud.uipath.com/{self.account_name}/{self.tenant_name}/orchestrator_"


def load_config() -> Config:
    required = [
        "UIPATH_ACCOUNT_NAME",
        "UIPATH_TENANT_NAME",
        "UIPATH_PAT",
        "TEAMS_WEBHOOK_URL",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "REPORT_TO_EMAILS",
        "REPORT_FROM_EMAIL",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        account_name=os.environ["UIPATH_ACCOUNT_NAME"],
        tenant_name=os.environ["UIPATH_TENANT_NAME"],
        pat=os.environ["UIPATH_PAT"],
        teams_webhook_url=os.environ["TEAMS_WEBHOOK_URL"],
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.environ["SMTP_PORT"]),
        smtp_user=os.environ["SMTP_USER"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        report_to_emails=[e.strip() for e in os.environ["REPORT_TO_EMAILS"].split(",")],
        report_from_email=os.environ["REPORT_FROM_EMAIL"],
        lookback_hours=int(os.getenv("LOOKBACK_HOURS", "24")),
    )
