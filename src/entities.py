import dataclasses
import datetime
import json
import logging
import typing

logger_log_set = logging.getLogger("log_day")


class LogPeriod:
    _start_str: str
    _end_str: str
    _task_id: str
    start: datetime.datetime
    end: datetime.datetime
    description: str

    def __init__(self, start: str, end: str, description: str, task_id: typing.Optional[str | int] = None):
        self._start_str = start
        self._end_str = end
        self._task_id = task_id and str(task_id)
        self.description = description

    def __str__(self):
        return f"{self.start}-{self.end} {self.description}"

    @property
    def task_id(self):
        return self._task_id

    def set_date(self, date: datetime.date):
        start_hour, start_minute = self._start_str.split(":")
        self.start = datetime.datetime(
            year=date.year, month=date.month, day=date.day, hour=int(start_hour), minute=int(start_minute)
        )
        end_hour, end_minute = self._end_str.split(":")
        self.end = datetime.datetime(
            year=date.year, month=date.month, day=date.day, hour=int(end_hour), minute=int(end_minute)
        )

    def get_duration(self):
        return self.end - self.start


@dataclasses.dataclass
class LogDay:
    date: datetime.date
    items: typing.List[LogPeriod]

    def __init__(self, date: str, items: typing.List[LogPeriod]):
        if not date.endswith(".2025"):
            date = date + ".2025"
        self.date = datetime.datetime.strptime(date, "%d.%m.%Y").date()

        self.items = []
        for item in items:
            item.set_date(self.date)
            self.items.append(item)

    def __str__(self):
        return f"{self.date}-{self.items}"

    def total_duration(self):
        return datetime.timedelta(seconds=sum(item.get_duration().seconds for item in self.items))


@dataclasses.dataclass
class LogTask:
    pk: str
    description: str


class SlotTime:
    start: datetime.datetime
    duration: datetime.timedelta
    task: typing.Optional[LogTask] = None

    def __init__(
        self,
        start: typing.Optional[datetime.datetime],
        duration: datetime.timedelta,
        task: typing.Optional[LogTask] = None,
    ):
        if start is None:
            start = datetime.time(hour=9)
        self.start = start
        self.duration = duration
        self.task = task

        self._initial_start = self.start

    def set_next_day(self):
        weekday = self.start.weekday()
        add_days = 1
        if weekday == 4:  # Friday
            add_days = 3

        self.start = self.start + datetime.timedelta(days=add_days)

    def get_relocate_duration(self):
        return self.start - self._initial_start

    def set_start(self, start: datetime.datetime):
        self.start = start

    @property
    def end(self):
        return self.start + self.duration

    def __str__(self):
        return f"{self.start.strftime("%H:%M")}-{self.end.strftime("%H:%M")} {self.task}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"

    def insert(self, other: "SlotTime"):
        parts = []
        if self.start < other.start:
            parts.append(SlotTime(self.start, other.start - self.start, None))

        if self.end > other.end:
            parts.append(SlotTime(other.start, other.duration, other.task))
            parts.append(SlotTime(other.end, self.end - other.end, None))
            return parts, None
        if self.end == other.end:
            parts.append(SlotTime(other.start, self.end - other.start, other.task))
            return parts, None
        # Divorce slot
        parts.append(SlotTime(other.start, self.end - other.start, other.task))
        return parts, SlotTime(self.end, other.end - self.end, other.task)


class WorkingDay:
    class WorkingDayFull(Exception):
        pass

    date: datetime.date
    slots: typing.List[SlotTime]

    DEFAULT_DURATION_WORKING_DAY = datetime.timedelta(hours=8)

    def __init__(self, date: datetime.date):
        self.date = date
        start = datetime.datetime(
            year=date.year,
            month=date.month,
            day=date.day,
            hour=8,
        )
        self.slots = [
            SlotTime(start=start, duration=self.DEFAULT_DURATION_WORKING_DAY, task=None),
        ]

    def __str__(self):
        return json.dumps([str(slot) for slot in self.slots], indent=4)

    def total_duration(self):
        return datetime.timedelta(seconds=sum(slot.duration.seconds for slot in self.slots if slot.task))

    def add_slot(self, slot_for_add: SlotTime, can_divorce: bool, any_time=False, any_after=False):
        logger_log_set.debug("NEED %s %s", slot_for_add.start.date(), slot_for_add)
        for i, slot in enumerate(self.slots):
            if slot.task is None:
                logger_log_set.debug("\t try", slot)
                if any_time:
                    logger_log_set.debug("\t\t ANY")
                    slot_for_add.set_start(slot.start)
                    new_slots, slot_for_relocate = slot.insert(slot_for_add)
                    self.slots[i : i + 1] = new_slots
                    return slot_for_relocate

                if any_after:
                    logger_log_set.debug("\t\t ANY after")
                    if slot.start >= slot_for_add.start:
                        slot_for_add.start = slot.start
                        new_slots, slot_for_relocate = slot.insert(slot_for_add)
                        self.slots[i : i + 1] = new_slots
                        return slot_for_relocate

                if slot.start <= slot_for_add.start < slot.end:
                    new_slots, slot_for_relocate = slot.insert(slot_for_add)
                    self.slots[i : i + 1] = new_slots
                    return slot_for_relocate

        total_duration = self.total_duration()

        if total_duration >= self.DEFAULT_DURATION_WORKING_DAY:
            raise self.WorkingDayFull()

        duration_available_for_day = self.DEFAULT_DURATION_WORKING_DAY - total_duration

        if slot_for_add.duration > duration_available_for_day:
            duration_additional = duration_available_for_day
        else:
            duration_additional = slot_for_add.duration

        additional_slot = SlotTime(
            start=self.slots[-1].end,
            duration=duration_additional,
        )
        self.slots.append(additional_slot)
        return self.add_slot(slot_for_add=slot_for_add, can_divorce=can_divorce, any_time=any_time, any_after=any_after)


class WorkingDaySet:
    data: typing.Dict[datetime.date, WorkingDay]

    def __init__(self):
        self.data = {}

    def __iter__(self) -> typing.Iterator[WorkingDay]:
        for date, working_day in sorted(self.data.items()):
            yield working_day

    def add_slot(self, slot_for_add: SlotTime, can_divorce: bool, any_time=False, any_after=False):
        if slot_for_add.get_relocate_duration().days > 5:
            raise Exception("To match relocated")

        date = slot_for_add.start.date()
        if date not in self.data:
            self.data[date] = WorkingDay(date=date)

        working_day = self.data[date]

        try:
            part_for_relocate = working_day.add_slot(slot_for_add, can_divorce, any_time=any_time, any_after=any_after)
            if part_for_relocate:
                logger_log_set.debug("RELOCATE %s" % part_for_relocate)
                self.add_slot(part_for_relocate, can_divorce=True, any_after=True)
        except WorkingDay.WorkingDayFull:
            logger_log_set.debug("WorkingDay is full. Relocating next day: %s" % slot_for_add)
            slot_for_add.set_next_day()
            self.add_slot(slot_for_add, can_divorce=True, any_time=True)
            return

    def total_duration(self):
        total_duration = 0
        for working_day in self.data.values():
            total_duration += working_day.total_duration().seconds
        return total_duration

    def get_logging(self):
        for working_day in self:
            yield LogDay(
                date=working_day.date.strftime("%d.%m.%Y"),
                items=[
                    LogPeriod(slot.start.strftime("%H:%M"), slot.end.strftime("%H:%M"), slot.task.description, task_id=str(slot.task.pk))
                    for slot in working_day.slots
                    if slot.task
                ],
            )
