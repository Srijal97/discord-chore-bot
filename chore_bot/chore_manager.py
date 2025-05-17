# chore_manager.py

import json
from pathlib import Path
from typing import Union, Any
import datetime

DAILY_CHORES = "daily_chores"
WEEKLY_CHORES = "weekly_chores"


class ChoreManager:
    def __init__(
        self,
        members: list[str],
        config_file: Union[str, Path],
        state_file: Union[str, Path] = "state.json",
    ) -> None:
        # load chore lists from config.json
        cfg = json.loads(Path(config_file).read_text())
        self.members = members
        self.daily_chores = cfg[DAILY_CHORES]
        self.weekly_chores = cfg[WEEKLY_CHORES]

        # current assignments in memory
        self._assignments = {
            DAILY_CHORES: {c: None for c in self.daily_chores},
            WEEKLY_CHORES: {
                day: {c: None for c in chores} for day, chores in self.weekly_chores.items()
            },
        }

        # persistent state file
        self.state_file = Path(state_file)
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            self.pointers = data.get("pointers", {})
            self._inactive = set(data.get("inactive_members", []))
        else:
            # initialize pointers so that next pick is index 0 for everyone
            self.pointers = {
                "daily": {c: -1 for c in self.daily_chores},
                "weekly": {
                    day: {c: -1 for c in chores}
                    for day, chores in self.weekly_chores.items()
                },
            }
            self._inactive = set()
            self._save_state()

    def _save_state(self):
        self.state_file.write_text(
            json.dumps(
                {
                    "pointers": self.pointers,
                    "inactive_members": list(self._inactive),
                },
                indent=2,
            )
        )

    @property
    def inactive_members(self) -> set[str]:
        return self._inactive

    def add_inactive_member(self, member: str) -> None:
        self._inactive.add(member)
        self._save_state()

    def remove_inactive_member(self, member: str) -> None:
        self._inactive.discard(member)
        self._save_state()

    @property
    def active_members(self) -> list[str]:
        return [m for m in self.members if m not in self._inactive]

    def _find_next_idx(self, last: int) -> int:
        n = len(self.members)
        for step in range(1, n + 1):
            idx = (last + step) % n
            if self.members[idx] not in self._inactive:
                return idx
        raise RuntimeError("No active members available")

    def _get_next(self, kind: str, key: str, chore: str | None = None) -> str:
        if kind == DAILY_CHORES:
            last = self.pointers["daily"][key]
            nxt = self._find_next_idx(last)
            self.pointers["daily"][key] = nxt
            self._save_state()
            return self.members[nxt]

        # weekly
        last = self.pointers["weekly"][key][chore]  # type: ignore[arg-type]
        nxt = self._find_next_idx(last)
        self.pointers["weekly"][key][chore] = nxt
        self._save_state()
        return self.members[nxt]

    @property
    def assignments(self) -> dict:
        # fill missing or inactive slots
        # daily
        for chore, assignee in self._assignments[DAILY_CHORES].items():
            if assignee is None or assignee in self._inactive:
                self._assignments[DAILY_CHORES][chore] = self._get_next(DAILY_CHORES, chore)

        # weekly
        for day, chores in self._assignments[WEEKLY_CHORES].items():
            for chore, assignee in chores.items():
                if assignee is None or assignee in self._inactive:
                    self._assignments[WEEKLY_CHORES][day][chore] = self._get_next(
                        WEEKLY_CHORES, day, chore
                    )

        return self._assignments

    def daily_assignments(self) -> dict[str, str]:
        return self.assignments[DAILY_CHORES]

    def weekly_assignments(self, weekday: str) -> dict[str, str]:
        return self.assignments[WEEKLY_CHORES].get(weekday, {})

    @property
    def visible_assignments(self) -> dict[int, str]:
        # map 1..N to chore names
        vis: dict[int, str] = {}
        idx = 1
        for c in self.daily_chores:
            vis[idx] = c
            idx += 1
        today = datetime.datetime.now().strftime("%A")
        for c in self.weekly_chores.get(today, []):
            vis[idx] = c
            idx += 1
        return vis

    def mark_as_done(self, member: str, chore: str | int | None = None) -> bool:
        # if called with no chore, clear all chores for this member
        if chore is None:
            for c, a in list(self._assignments[DAILY_CHORES].items()):
                if a == member:
                    self._assignments[DAILY_CHORES][c] = None
            for d, chores in self._assignments[WEEKLY_CHORES].items():
                for c, a in list(chores.items()):
                    if a == member:
                        self._assignments[WEEKLY_CHORES][d][c] = None
            return True

        # if a number was passed, translate to chore name
        if isinstance(chore, int):
            try:
                chore = self.visible_assignments[chore]
            except KeyError:
                return False

        # now chore is a string
        if chore in self._assignments[DAILY_CHORES]:
            self._assignments[DAILY_CHORES][chore] = None
            return True

        for d, chores in self._assignments[WEEKLY_CHORES].items():
            if chore in chores:
                self._assignments[WEEKLY_CHORES][d][chore] = None
                return True

        return False


if __name__ == "__main__":
    members = ["Ajinkya", "Mavvi", "Anish", "Luca", "Srijal"]
    mgr = ChoreManager(members, "config.json")
    print("Daily:", mgr.daily_assignments())
    print("Monday:", mgr.weekly_assignments("Monday"))
