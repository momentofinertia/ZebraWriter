from datetime import datetime

import pytest

from thermal_app.domain.enums import PrintJobStatus
from thermal_app.domain.errors import InvalidJobTransitionError
from thermal_app.domain.models import PrintJob


def make_job() -> PrintJob:
    now = datetime.now().astimezone()
    return PrintJob("job", now, now, "printer", "paper", "test.page", "test")


def test_valid_job_lifecycle_ends_at_submitted() -> None:
    job = make_job()
    for status in (
        PrintJobStatus.RENDERING,
        PrintJobStatus.READY,
        PrintJobStatus.SUBMITTING,
        PrintJobStatus.SUBMITTED,
    ):
        job.transition_to(status)
    assert job.status is PrintJobStatus.SUBMITTED


def test_spooler_submitted_job_cannot_move_back_to_ready() -> None:
    job = make_job()
    job.transition_to(PrintJobStatus.RENDERING)
    job.transition_to(PrintJobStatus.READY)
    job.transition_to(PrintJobStatus.SUBMITTING)
    job.transition_to(PrintJobStatus.SUBMITTED)
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(PrintJobStatus.READY)
