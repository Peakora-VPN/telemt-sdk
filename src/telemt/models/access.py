"""Access-policy response contracts from the Telemt 3.5.17 Rust source (66708d28).

``GET`` and ``PATCH /v1/access/policy`` return the same PolicyState payload
under the standard revision envelope: desired and effective snapshots of the
five public policy fields, the runtime baseline, and publication status.
``changed_paths`` is serde skip-if-none, so GET omits it and PATCH carries it.
"""

from .base import ResponseModel
from .config import RuntimeBaseline


class CidrRateLimit(ResponseModel):
    """Aggregate per-CIDR transport rate in bits per second; 0 means unlimited."""

    up_bps: int
    down_bps: int


class AccessPolicy(ResponseModel):
    """One snapshot (desired or effective) of the five public access-policy fields."""

    user_max_tcp_conns_global_each: int
    user_max_unique_ips_global_each: int
    user_max_unique_ips_mode: str
    user_max_unique_ips_window_secs: int
    cidr_rate_limits: dict[str, CidrRateLimit]


class AccessPolicyData(ResponseModel):
    """Desired/effective policy snapshots with runtime publication status.

    ``changed_paths`` is omitted on GET and lists the edited ``access.*``
    paths on PATCH.
    """

    desired: AccessPolicy
    effective: AccessPolicy
    runtime: RuntimeBaseline
    published_match: bool
    effective_scope: str
    subsystem_convergence: str
    apply_mode: str
    changed_paths: list[str] | None = None
