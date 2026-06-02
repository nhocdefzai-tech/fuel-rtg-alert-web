from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any


def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_rtg_name(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    match = re.match(r"^RTG\s*0?(\d{1,2})$", text)
    if not match:
        return text
    return f"RTG {int(match.group(1)):02d}"


def clean_visit(value: Any) -> str:
    return str(value or "").strip().upper()


def parse_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return default


def parse_int(value: Any, default: int = 0) -> int:
    number = parse_float(value, None)
    return int(number) if number is not None else default


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def datetime_to_input(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%dT%H:%M") if value else ""


def dt_iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="minutes") if value else None
