from collections.abc import Callable
from dataclasses import dataclass, replace
from math import ceil
from random import Random
from time import monotonic, time
from typing import Literal

from app.baby import rules
from app.baby.data import Catalog


@dataclass(frozen=True)
class State:
    started_at: int
    age_months: int = 0
    care_points: int = 0
    hunger: float = 0.60
    sleepiness: float = 0.35
    diaper: float = 0.30
    gas: float = 0.10
    attachment: float = 0.65
    stimulation: float = 0.0
    mood: float = 0.0
    arousal: float = 0.25


@dataclass(frozen=True)
class Reaction:
    kind: Literal["baby_reaction"]
    at: float
    action: rules.Action
    behavior_id: str


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


class BabyEngine:
    def __init__(
        self,
        catalog: Catalog,
        state: State,
        *,
        speed: int = 1,
        rng: Random | None = None,
        clock: Callable[[], float] = monotonic,
        wall_clock: Callable[[], float] = time,
    ) -> None:
        self.catalog = catalog
        self.state = state
        self.speed = speed
        self.rng = rng if rng is not None else Random()
        self.clock = clock
        self.wall_clock = wall_clock
        self.current: rules.Signal | None = None
        self.last_started: dict[str, float] = {}
        self.action_end = 0.0
        self.sleep_signal: rules.Signal | None = None

    def apply_care(self, care: rules.Care) -> None:
        previous = self.state
        changes = rules.CARE_DELTAS[care]
        if care == "sleep":
            early = previous.sleepiness < rules.EARLY_SLEEP_THRESHOLD
            self.sleep_signal = rules.EARLY_SLEEP if early else rules.SLEEP
            if early:
                changes = {"sleepiness": -0.02}
        if care == "feed" and previous.hunger < rules.MIN_EFFECTIVE_CHANGE:
            changes = {"hunger": 0.0}
        values = {key: clamp(getattr(previous, key) + delta) for key, delta in changes.items()}
        if care == "hold":
            values["stimulation"] = previous.stimulation * 0.30
        primary = next(iter(changes))
        relief = abs(values[primary] - getattr(previous, primary))
        if care == "hold":
            relief = max(relief, abs(values["stimulation"] - previous.stimulation))
        self.state = replace(
            previous, **values,
            mood=clamp(previous.mood + 0.35 * relief, -1),
            care_points=previous.care_points + int(relief >= rules.MIN_EFFECTIVE_CHANGE),
        )
        self._grow()

    def _grow(self) -> None:
        elapsed_days = max(0, self.wall_clock() - self.state.started_at) / rules.SECONDS_PER_DAY
        month = self.state.age_months
        while month + 1 in self.catalog.months:
            following = month + 1
            if self.state.care_points < following * rules.POINTS_PER_MONTH:
                break
            if self.speed == 1 and elapsed_days < ceil(rules.PROGRAM_DAYS * following / rules.MAX_MONTH):
                break
            month = following
        if month != self.state.age_months:
            self.state = replace(self.state, age_months=month)

    def _advance_needs(self) -> None:
        s = self.state
        routine = self.catalog.routine_at(s.age_months)
        sleeping = self.current is rules.SLEEP
        self.state = replace(
            s,
            hunger=clamp(s.hunger + self.speed * routine.feeds / rules.SECONDS_PER_DAY),
            diaper=clamp(s.diaper + self.speed * routine.diapers / rules.SECONDS_PER_DAY),
            sleepiness=clamp(s.sleepiness + (0 if sleeping else self.speed / routine.awake_seconds)),
            gas=clamp(s.gas - self.speed / rules.GAS_DECAY_SECONDS),
            attachment=clamp(s.attachment - self.speed / rules.ATTACHMENT_DECAY_SECONDS),
            stimulation=clamp(s.stimulation - self.speed / rules.BOREDOM_SECONDS, -1),
        )
        pressure = max(self._pressures().values())
        self.state = replace(
            self.state,
            mood=clamp(s.mood * rules.MOOD_DECAY + (1 - 2 * pressure) * (1 - rules.MOOD_DECAY), -1),
            arousal=clamp(s.arousal * rules.MOOD_DECAY + pressure * (1 - rules.MOOD_DECAY)),
        )

    def _pressures(self) -> dict[str, float]:
        s = self.state
        return {
            "hunger": s.hunger, "diaper": s.diaper, "gas": s.gas, "sleepiness": s.sleepiness,
            "attachment": 1 - s.attachment, "boredom": max(0.0, -s.stimulation),
            "overstimulation": max(0.0, s.stimulation),
        }

    def _eligible(self, signal: rules.Signal, now: float) -> bool:
        behavior = self.catalog.behaviors[signal.behavior_id]
        return (
            behavior.start <= self.state.age_months <= behavior.end
            and now - self.last_started.get(signal.action.name, float("-inf")) >= rules.REPEAT_SECONDS
        )

    def _choose(self, now: float) -> rules.Signal | None:
        pressures = self._pressures()
        candidates: list[tuple[float, rules.Signal]] = []
        if self.sleep_signal is not None and self._eligible(self.sleep_signal, now):
            candidates.append((2.0, self.sleep_signal))
        for key in self.catalog.cry_order:
            for signal in rules.SIGNALS[key]:
                if pressures[key] >= signal.threshold and self._eligible(signal, now):
                    candidates.append((pressures[key], signal))
                    break
        if not candidates and max(pressures.values()) < 0.55:
            for signal in rules.CALM:
                if self._eligible(signal, now):
                    # 나이가 들며 새로 해금된 행동을 자주 고르되 기존 반응도 남긴다.
                    start = self.catalog.behaviors[signal.behavior_id].start
                    candidates.append((start + self.rng.uniform(0, 4), signal))
        return max(candidates, key=lambda item: item[0])[1] if candidates else None

    def tick(self) -> Reaction | None:
        self._grow()
        now = self.clock()
        if now >= self.action_end:
            self.current = None
        self._advance_needs()
        if self.current is not None:
            return None
        self.current = self._choose(now)
        self.sleep_signal = None
        if self.current is None:
            return None
        signal = self.current
        action = signal.action
        self.action_end = now + action.duration
        self.last_started[action.name] = now
        if signal.reaction:
            return Reaction("baby_reaction", now, action, signal.behavior_id)
        return None
