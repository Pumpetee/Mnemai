"""Which assistant sees what.

Each client (an assistant or tool) gets a set of allowed scopes and a set of denied tags.
Stored in <vault>/.mnema/clients.json so the owner can edit it by hand or in the app.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .vault import Vault
from .fsutil import read_json, write_json

ALL_SCOPES = ["profile", "rules", "projects", "cards", "people", "decisions", "inbox", "notes"]


@dataclass
class Client:
    id: str
    name: str
    enabled: bool = True
    scopes: list = field(default_factory=lambda: list(ALL_SCOPES))
    deny_tags: list = field(default_factory=list)
    can_write: bool = True
    # Where it may write. Reading and writing are separate: an outside assistant may drop a fact
    # into the inbox for the owner to sort, but must not rewrite rules or decisions.
    write_scopes: list = field(default_factory=lambda: ["inbox"])
    via: str = ""  # how it connects: mcp, hook, api
    layout: int = 2  # memory layout version the scopes were set for

    def __post_init__(self):
        from .vault import norm_tag

        self.deny_tags = list(dict.fromkeys(norm_tag(t) for t in (self.deny_tags or []) if norm_tag(t)))

    def allows(self, scope: str) -> bool:
        return self.enabled and scope in self.scopes

    def may_write(self, scope: str) -> bool:
        return self.enabled and self.can_write and scope in self.write_scopes


DEFAULT_CLIENTS = [
    # The model on this computer (built-in or Ollama): nothing leaves the machine, so it sees everything by default.
    Client("local", "На этом компьютере", write_scopes=["inbox"], via="local"),
    Client(
        "claude",
        "Claude и Claude Code",
        write_scopes=["inbox", "decisions", "projects", "cards", "people", "rules"],
        via="mcp",
    ),
    # Nothing is cut out by default: money, health and private are hidden from an AI only when the owner ticks it
    # (decided 23.10.2026). Every AI may drop new facts into the inbox, the owner sorts them.
    Client("chatgpt", "ChatGPT", scopes=["profile", "rules", "projects", "cards", "decisions"], via="api"),
    Client("opencode", "OpenCode Go", scopes=["profile", "rules", "projects", "cards", "decisions"], via="api"),
    Client("gemini", "Gemini", scopes=["profile", "rules", "cards"], via="api"),
    Client("openrouter", "OpenRouter", scopes=["profile", "rules", "projects", "cards", "decisions"], via="api"),
    Client("deepseek", "DeepSeek", scopes=["profile", "rules", "projects", "cards", "decisions"], via="api"),
    Client("yandex", "YandexGPT", scopes=["profile", "rules", "projects", "cards", "decisions"], via="api"),
    Client("cursor", "Cursor", scopes=["rules", "projects"], via="mcp"),
]


def _file(vault: Vault):
    return vault.service / "clients.json"


def load_clients(vault: Vault) -> dict[str, Client]:
    f = _file(vault)
    if not f.exists():
        return {c.id: Client(**asdict(c)) for c in DEFAULT_CLIENTS}
    data = read_json(f, None)
    if not isinstance(data, list):  # unreadable: the safe defaults, never «everyone sees everything»
        return {c.id: Client(**asdict(c)) for c in DEFAULT_CLIENTS}
    out = {}
    for item in data:
        known = {k: v for k, v in item.items() if k in Client.__dataclass_fields__}
        c = Client(**known)
        if item.get("layout", 1) < 2:  # topic cards came later: once, they follow the profile
            if "profile" in c.scopes and "cards" not in c.scopes:
                c.scopes.append("cards")
            if "projects" in c.write_scopes and "cards" not in c.write_scopes:
                c.write_scopes.append("cards")
        out[c.id] = c
    for d in DEFAULT_CLIENTS:  # a client added in a later version gets its own defaults
        if d.id not in out:
            out[d.id] = Client(**asdict(d))
    return {d.id: out.pop(d.id) for d in DEFAULT_CLIENTS} | out


def save_clients(vault: Vault, clients: dict[str, Client]) -> None:
    f = _file(vault)
    f.parent.mkdir(parents=True, exist_ok=True)
    write_json(f, [asdict(c) for c in clients.values()], indent=2)


def get_client(vault: Vault, client_id: str) -> Client:
    clients = load_clients(vault)
    if client_id in clients:
        return clients[client_id]
    # Unknown client: safest default — profile and rules only, read-only, private hidden.
    return Client(
        client_id,
        client_id,
        scopes=["profile", "rules"],
        deny_tags=["money", "health", "private"],
        can_write=False,
        write_scopes=[],
    )
