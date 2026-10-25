from dataclasses import dataclass, field

SERVER_ALIAS = "carteira"

STATUSES = ("registered", "updated", "skipped_present", "skipped_absent", "failed")


@dataclass
class ClientRegistration:
    command: str
    args: list[str]
    env: dict[str, str]
    name: str = SERVER_ALIAS


@dataclass
class RegisterOutcome:
    client_id: str
    status: str
    message: str


@dataclass
class InstallerSession:
    wallet_id: str
    outcomes: list[RegisterOutcome] = field(default_factory=list)
    requested: set[str] = field(default_factory=set)
