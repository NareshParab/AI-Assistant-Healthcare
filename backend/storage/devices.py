"""Device registration and pairing-code business logic.

D25/PRIV-1640: only a hash of any secret (device token, pairing code) is
ever persisted -- never the raw value. Raw values are generated with
`secrets` (cryptographically strong) and returned to the caller exactly
once, at creation time; they cannot be recovered from storage afterward.

Every function that needs "now" accepts it as an optional parameter
(defaulting to the real current time) so callers -- specifically tests --
can inject a fixed clock instead of sleeping (per this task's test
requirements).
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# D22: pairing code is 6 characters. Alphabet excludes visually ambiguous
# characters (0/O, 1/I/L) since a human reads this code off a TV screen and
# types it on a phone.
_PAIRING_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_PAIRING_CODE_LENGTH = 6

# Resolved 2026-09-29, contract section 3.1 (SS10 decision 3): 15 minutes
# for real use. The contract separately mentions "a longer-lived demo code"
# but defines no client-facing mechanism (request field or endpoint) to ask
# for one -- the request body is stated as genuinely empty. This constant is
# therefore the ONLY code path implemented; a demo deployment gets a longer
# TTL via this environment variable at the deployment level, not via any new
# API surface the contract does not define.
_DEFAULT_PAIRING_CODE_TTL_SECONDS = 15 * 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso_string(dt: datetime) -> str:
    """Serialize with an explicit "Z" UTC suffix, matching the contract's
    timestamp convention (section 1). Public: callers (e.g. the API layer)
    use this to format response fields, so there is one place that defines
    "what does an ISO-8601 UTC timestamp look like in this system."
    """

    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_iso = to_iso_string  # internal alias, unchanged call sites below


def _hash(raw_value: str) -> str:
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RegisteredDevice:
    device_token: str  # raw token -- returned to the caller once, never stored
    issued_at: datetime


@dataclass(frozen=True)
class PairingCode:
    pairing_code: str  # raw code -- returned to the caller once, never stored
    expires_at: datetime


def register_device(conn: sqlite3.Connection, *, now: datetime | None = None) -> RegisteredDevice:
    """Issue a new device token (contract: POST /v1/devices/register)."""

    now = now or _utc_now()
    device_id = str(uuid.uuid4())
    raw_token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO devices (device_id, token_hash, issued_at) VALUES (?, ?, ?)",
        (device_id, _hash(raw_token), _iso(now)),
    )
    conn.commit()
    return RegisteredDevice(device_token=raw_token, issued_at=now)


def verify_device_token(conn: sqlite3.Connection, raw_token: str) -> str | None:
    """Return the device_id if `raw_token` is a valid, known device token, else None."""

    if not raw_token:
        return None
    row = conn.execute(
        "SELECT device_id FROM devices WHERE token_hash = ?",
        (_hash(raw_token),),
    ).fetchone()
    return row[0] if row else None


def create_pairing_code(
    conn: sqlite3.Connection,
    *,
    device_id: str,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
) -> PairingCode:
    """Create a pairing code for an already-authenticated device
    (contract: POST /v1/devices/pairing-code). Caller must have already
    verified the device token via verify_device_token / require_device_token.
    """

    now = now or _utc_now()
    ttl = ttl_seconds if ttl_seconds is not None else _DEFAULT_PAIRING_CODE_TTL_SECONDS
    expires_at = now + timedelta(seconds=ttl)

    # Bounded retry on the (very unlikely) event of a code collision with
    # another still-active code -- simpler than a uniqueness constraint
    # violation surfacing as an unhandled error.
    for _ in range(5):
        raw_code = "".join(
            secrets.choice(_PAIRING_CODE_ALPHABET) for _ in range(_PAIRING_CODE_LENGTH)
        )
        code_hash = _hash(raw_code)
        existing = conn.execute(
            "SELECT 1 FROM pairing_codes WHERE code_hash = ?", (code_hash,)
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO pairing_codes (code_hash, device_id, created_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (code_hash, device_id, _iso(now), _iso(expires_at)),
            )
            conn.commit()
            return PairingCode(pairing_code=raw_code, expires_at=expires_at)

    raise RuntimeError("could not generate a unique pairing code after 5 attempts")


def resolve_pairing_code_device(
    conn: sqlite3.Connection, raw_code: str, *, now: datetime | None = None
) -> str | None:
    """Return the owning device_id if `raw_code` exists and has not expired
    as of `now`, else None. The single definition of pairing-code validity.

    Lookup is by SHA-256 hash of the presented value (as for device tokens),
    so the raw code is never compared character-by-character.
    """

    if not raw_code:
        return None
    now = now or _utc_now()
    # Contract 1.0 (v1.2.0): case-insensitive. Issued codes are upper-case; a
    # phone keyboard may lowercase what the user types. Normalizing here, the
    # single place every pairing-code lookup goes through, covers all callers.
    row = conn.execute(
        "SELECT device_id, expires_at FROM pairing_codes WHERE code_hash = ?",
        (_hash(raw_code.upper()),),
    ).fetchone()
    if row is None:
        return None
    expires_at = datetime.strptime(row[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return row[0] if now < expires_at else None


def is_pairing_code_valid(
    conn: sqlite3.Connection, raw_code: str, *, now: datetime | None = None
) -> bool:
    """True if `raw_code` exists and has not expired as of `now`."""

    return resolve_pairing_code_device(conn, raw_code, now=now) is not None
