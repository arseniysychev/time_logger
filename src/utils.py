import typing

from entities import LogDay, LogTask, SlotTime, WorkingDaySet


def double_time(input_log_days: typing.List[LogDay], skip_task: str) -> typing.Iterable[LogDay]:
    data = WorkingDaySet()

    for log_day in input_log_days:
        for log_period in log_day.items:
            if log_period.task_id == skip_task:
                data.add_slot(
                    slot_for_add=SlotTime(
                        start=log_period.start,
                        duration=log_period.end - log_period.start,
                        task=LogTask(pk=log_period.task_id, description=log_period.description),
                    ),
                    can_divorce=False,
                )

    for log_day in input_log_days:
        for log_period in log_day.items:
            if log_period.task_id == skip_task:
                continue

            data.add_slot(
                slot_for_add=SlotTime(
                    start=log_period.start,
                    duration=(log_period.end - log_period.start) * 2,
                    task=LogTask(pk=log_period.task_id, description=log_period.description),
                ),
                can_divorce=True,
                any_after=True,
            )

    return data.get_logging()
