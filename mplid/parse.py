"""Small, explicit parsers for the text formats used by id-mpl.com.

The site mixes Indonesian number formatting (``2,044,010`` thousands and
``2,54`` decimals), Indonesian month names and ``H:MM`` game durations. All
conversion rules live here so the source modules stay readable.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}

_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def squash(value: str | None) -> str:
    """Collapse whitespace (including nbsp) and trim."""
    if not value:
        return ""
    value = value.replace("\xa0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def to_int(value: str | None) -> int | None:
    """``'2,044,010'`` -> 2044010, ``'878'`` -> 878, ``''`` -> None."""
    if value is None:
        return None
    digits = re.sub(r"[^0-9-]", "", value)
    if digits in ("", "-"):
        return None
    return int(digits)


def to_float(value: str | None) -> float | None:
    """Parse Indonesian or plain decimals: ``'2,54'`` -> 2.54, ``'2.044.010'`` -> 2044010.0."""
    if value is None:
        return None
    text = squash(value).replace(" ", "")
    if not text or text in {"-", "N/A"}:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = f"{head.replace(',', '')}.{tail}" if len(tail) in (1, 2) else text.replace(",", "")
    else:
        # dot may be a thousands separator when grouped in threes
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def to_ratio(value: str | None) -> float | None:
    """``'63%'`` -> 0.63 (fraction, not percent)."""
    if not value or "%" not in value:
        return None
    number = to_float(value.replace("%", ""))
    return None if number is None else round(number / 100.0, 4)


def parse_duration(value: str | None) -> int | None:
    """``'16:51'`` -> 1011 seconds."""
    if not value:
        return None
    match = _TIME_RE.search(value)
    if not match:
        return None
    minutes, seconds = int(match.group(1)), int(match.group(2))
    if seconds > 59:
        return None
    return minutes * 60 + seconds


def parse_time(value: str | None) -> str:
    """``'13:00'`` -> ``'13:00'`` (WIB, UTC+7), empty when absent."""
    match = _TIME_RE.search(value or "")
    if not match:
        return ""
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def parse_indonesian_date(value: str | None) -> str:
    """``'Rabu, 4 November 2026'`` -> ``'2026-11-04'``."""
    if not value:
        return ""
    match = _DATE_RE.search(value)
    if not match:
        return ""
    day, month_name, year = match.groups()
    month = MONTHS.get(month_name.lower())
    if not month:
        return ""
    return dt.date(int(year), month, int(day)).isoformat()


def split_record(value: str | None) -> tuple[int | None, int | None]:
    """``'12 - 4'`` -> ``(12, 4)``."""
    if not value:
        return None, None
    numbers = re.findall(r"\d+", value)
    if len(numbers) < 2:
        return (int(numbers[0]) if numbers else None), None
    return int(numbers[0]), int(numbers[1])


def slugify(value: str) -> str:
    text = strip_accents(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def first_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None
