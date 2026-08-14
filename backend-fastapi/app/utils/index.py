DURATION_UNIT_TO_MS = {
    "millisecond": 1,
    "second": 1000,
    "minute": 60 * 1000,
    "hour": 60 * 60 * 1000,
    "day": 24 * 60 * 60 * 1000,
    "week": 7 * 24 * 60 * 60 * 1000,
    "month": 30 * 24 * 60 * 60 * 1000,  # Approximation
    "year": 365 * 24 * 60 * 60 * 1000,   # Approximation
}


def createHttpError(message, status): 
    error = Exception(message)
    error.status = status
    return error

def parseDurationToMilliseconds(duration_str: str) -> int:
    """
    Chuyển chuỗi thời lượng (ví dụ "2 hours", "30 minutes") sang số milliseconds.
    """
    parts = duration_str.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid duration format: {duration_str}")

    try:
        value = float(parts[0])
    except ValueError:
        raise ValueError(f"Invalid number in duration: {parts[0]}")

    unit = parts[1].lower()
    if unit not in DURATION_UNIT_TO_MS:
        raise ValueError(f"Unknown duration unit: {unit}")

    return int(value * DURATION_UNIT_TO_MS[unit])

