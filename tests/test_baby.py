from contextlib import closing
from dataclasses import replace
from random import Random
from shutil import copytree
from sqlite3 import connect

import pytest

from app.baby import rules
from app.baby.data import DATA_PATH, BehaviorDataError, load_catalog
from app.baby.engine import BabyEngine, State
from app.baby.store import BabyStore


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_project_catalog_links_age_ranges_and_routines(catalog):
    assert len(catalog.behaviors) == 196
    assert catalog.months == set(range(13))
    assert catalog.routine_at(0).feeds == 10
    assert catalog.routine_at(0).awake_seconds == 3150
    assert catalog.routine_at(0).diapers == 6
    assert catalog.routine_at(12).feeds == 4
    assert catalog.routine_at(12).awake_seconds == 12600
    assert catalog.cry_order[:3] == ("hunger", "diaper", "gas")
    assert "illness" not in catalog.cry_order


@pytest.mark.parametrize(
    ("filename", "before", "after", "error"),
    [
        ("behaviors.csv", "시작 월령", "다른 열", "필수 열"),
        ("behaviors.csv", ",0,6,수유 1~3시간", ",7,6,수유 1~3시간", "월령 범위"),
        ("ai_mapping.csv", "hunger 배고픔", "unlisted 배고픔", "AI 매핑"),
        ("ai_mapping.csv", "B001, B002", "B999, B002", "행동 ID"),
    ],
)
def test_rejects_invalid_catalog(tmp_path, filename, before, after, error):
    data = tmp_path / "behaviors"
    copytree(DATA_PATH, data)
    file = data / filename
    content = file.read_text(encoding="utf-8")
    assert before in content
    file.write_text(content.replace(before, after, 1), encoding="utf-8")
    with pytest.raises(BehaviorDataError, match=error):
        load_catalog(data)


def test_seeded_actions_emit_reactions_and_respect_cooldown(catalog):
    def run():
        now = 0
        initial = State(0, age_months=6, hunger=0.20)
        engine = BabyEngine(catalog, initial, rng=Random(17), clock=lambda: now, wall_clock=lambda: 0)
        started = []
        reactions = []
        for now in range(1, 30):
            result = engine.tick()
            if engine.current and engine.last_started[engine.current.action.name] == now:
                started.append((now, engine.current.action.name))
            if result:
                reactions.append(result)
        return started, reactions

    started, reactions = run()
    assert (started, reactions) == run()
    assert len(reactions) > 3
    last = {}
    for when, action in started:
        assert when - last.get(action, -100) >= 4
        last[action] = when
    for event in reactions:
        assert event.kind == "baby_reaction"
        behavior = catalog.behaviors[event.behavior_id]
        assert behavior.start <= 6 <= behavior.end


def test_month_requires_points_and_days_and_persists(tmp_path, catalog):
    now = 0
    store = BabyStore(tmp_path / "data" / "app.db")
    state = store.load(now=now)
    engine = BabyEngine(catalog, replace(state, care_points=29), clock=lambda: now, wall_clock=lambda: now)
    engine.tick()
    assert engine.state.age_months == 0

    now = 7 * rules.SECONDS_PER_DAY
    engine.tick()
    assert engine.state.age_months == 2
    engine.apply_care("feed")
    assert engine.state.age_months == 3
    store.save(engine.state)
    assert BabyStore(store.database).load(now=now + 20) == engine.state
    with closing(connect(store.database)) as db:
        assert db.execute("SELECT COUNT(*) FROM baby_state").fetchone() == (1,)
        assert {entry[2] for entry in db.execute("PRAGMA table_info(baby_state)")} == {"INTEGER", "REAL"}


def test_demo_ignores_days_and_accelerates_need_changes(catalog):
    now = 0
    state = State(now, care_points=120)
    normal = BabyEngine(catalog, state, clock=lambda: now, wall_clock=lambda: now)
    demo = BabyEngine(catalog, state, speed=30, clock=lambda: now, wall_clock=lambda: now)
    normal.tick()
    demo.tick()
    assert normal.state.age_months == 0
    assert demo.state.age_months == 12
    assert demo.state.hunger - state.hunger > normal.state.hunger - state.hunger
