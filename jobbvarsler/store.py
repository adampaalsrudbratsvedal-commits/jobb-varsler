"""Lokal tilstand: når vi sist sjekket, hvilke e-poster som er vurdert, og funnene."""

import json
import os
import time

from .config import PROCESSED_RETENTION_DAYS, STATE_FILE


def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    else:
        state = {}
    state.setdefault("last_check", None)
    state.setdefault("processed", {})  # message id -> mottatt-tidspunkt (epoch)
    state.setdefault("findings", [])
    state.setdefault("overrides", {})  # message id -> {company, category, hidden}
    return state


def set_override(message_id: str, **changes) -> bool:
    """Retter bedrift/kategori eller skjuler et funn. False hvis funnet ikke finnes."""
    state = load_state()
    if not any(f["id"] == message_id for f in state["findings"]):
        return False
    override = state["overrides"].setdefault(message_id, {})
    override.update({k: v for k, v in changes.items() if v is not None})
    save_state(state)
    return True


def save_state(state: dict) -> None:
    cutoff = time.time() - PROCESSED_RETENTION_DAYS * 86400
    state["processed"] = {mid: ts for mid, ts in state["processed"].items() if ts >= cutoff}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Skriv til temp-fil og bytt atomisk, så MCP-serveren og bakgrunnsjobben ikke leser en halv fil.
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE_FILE)
