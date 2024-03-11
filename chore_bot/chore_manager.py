import json
from pathlib import Path
from typing import Union, Any

import numpy as np

USERS = "users"
DAILY_CHORES = "daily_chores"
WEEKLY_CHORES = "weekly_chores"


class ChoreManager:
    def __init__(self, members: list[str], config_file: Union[str, Path]) -> None:
        with open(config_file, "r") as f:
            config = json.load(f)

        self.members = members
        self.daily_chores = config[DAILY_CHORES]
        self.weekly_chores = config[WEEKLY_CHORES]

        self.rng = np.random.default_rng()

        self._assignments = {
            DAILY_CHORES: {chore: None for chore in self.daily_chores},
        }
        self._assignments[WEEKLY_CHORES] = {}
        for day, chores in self.weekly_chores.items():
            self._assignments[WEEKLY_CHORES][day] = {chore: None for chore in chores}

        self._inactive_members = set()

    @property
    def inactive_members(self):
        return self._inactive_members

    def add_inactive_member(self, member: str) -> None:
        self._inactive_members.add(member)

    def remove_inactive_member(self, member: str) -> None:
        self._inactive_members.discard(member)

    @property
    def active_members(self):
        return list(set(self.members) - self._inactive_members)

    @property
    def assignments(self):
        for chore, assignee in self._assignments[DAILY_CHORES].items():
            if assignee is None or assignee in self.inactive_members:
                self._assignments[DAILY_CHORES][chore] = self.rng.choice(
                    self.active_members
                )
        for day, chores in self._assignments[WEEKLY_CHORES].items():
            for chore, assignee in chores.items():
                if assignee is None or assignee in self.inactive_members:
                    self._assignments[WEEKLY_CHORES][day][chore] = self.rng.choice(
                        self.active_members
                    )

        return self._assignments

    def mark_as_done(self, member: Any, chore: str = None) -> None:
        if chore is None:
            for chore, assignee in self._assignments[DAILY_CHORES].items():
                if assignee == member:
                    self._assignments[DAILY_CHORES][chore] = None
            for day, chores in self._assignments[WEEKLY_CHORES].items():
                for chore, assignee in chores.items():
                    if assignee == member:
                        self._assignments[WEEKLY_CHORES][day][chore] = None
        else:
            try:
                self._assignments[DAILY_CHORES][chore] = None
            except KeyError:
                for day, chores in self._assignments[WEEKLY_CHORES].items():
                    try:
                        self._assignments[WEEKLY_CHORES][day][chore] = None
                    except KeyError:
                        pass

    def daily_assignments(self) -> dict[str, str]:
        return self.assignments[DAILY_CHORES]

    def weekly_assignments(self, weekday: str) -> dict[str, str]:
        return self.assignments[WEEKLY_CHORES][weekday]


if __name__ == "__main__":
    chore_manager = ChoreManager(
        ["Allison", "Arka", "Priyatham", "Rachel", "Srijal"], "config.json"
    )
    print(chore_manager.daily_assignments())
    print(chore_manager.weekly_assignments("Monday"))
