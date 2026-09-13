"""Connector capability registry: the harness's view of what each
connector can do.

Connectors are first-class integration units, not arbitrary functions.
The capability boundary is enforced by the harness: GitHub is read-only
for mutations, every controlled mutation target supports read-after-write
verification, and all connectors can receive events.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorCapabilities:
    provider: str
    can_read: bool
    can_write: bool
    can_verify: bool
    can_receive_events: bool


CONNECTOR_CAPABILITIES: dict[str, ConnectorCapabilities] = {
    # GitHub is a read-only context source: mutations are never proposed
    # for it and ALLOWED_PROPOSALS keeps its operation set empty.
    "github": ConnectorCapabilities(
        provider="github",
        can_read=True,
        can_write=False,
        can_verify=True,
        can_receive_events=True,
    ),
    "jira": ConnectorCapabilities(
        provider="jira",
        can_read=True,
        can_write=True,
        can_verify=True,
        can_receive_events=True,
    ),
    "slack": ConnectorCapabilities(
        provider="slack",
        can_read=True,
        can_write=True,
        can_verify=True,
        can_receive_events=True,
    ),
    "notion": ConnectorCapabilities(
        provider="notion",
        can_read=True,
        can_write=True,
        can_verify=True,
        can_receive_events=True,
    ),
}


def capabilities_for(provider: str) -> ConnectorCapabilities | None:
    return CONNECTOR_CAPABILITIES.get(provider.lower().strip())


def can_propose_write(provider: str) -> bool:
    caps = capabilities_for(provider)
    return caps is not None and caps.can_write
