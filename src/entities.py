import dataclasses
import typing


@dataclasses.dataclass
class LogPeriod:
    start: str
    end: str
    description: str

    def __str__(self):
        return f"{self.start}-{self.end} {self.description}"


@dataclasses.dataclass
class LogDay:
    date: str
    items: typing.List[LogPeriod]

    def __str__(self):
        return f"{self.date}-{self.items}"
