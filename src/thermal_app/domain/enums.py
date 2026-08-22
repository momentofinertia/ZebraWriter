from enum import StrEnum


class MediaTracking(StrEnum):
    CONTINUOUS = "continuous"
    GAP = "gap"
    BLACK_MARK = "black_mark"


class LengthMode(StrEnum):
    CONTINUOUS = "continuous"
    FIXED = "fixed"


class Orientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PrintJobStatus(StrEnum):
    CREATED = "created"
    RENDERING = "rendering"
    READY = "ready"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    FAILED = "failed"
    CANCELLED = "cancelled"
