import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

DATA_PATH = Path(__file__).resolve().parents[2] / "docs" / "baby_behavior"
NEEDS = frozenset({"hunger", "sleepiness", "diaper", "gas", "attachment", "stimulation"})
CRY_KEYS = {"stimulation(부족)": "boredom", "overstimulation": "overstimulation"}


class BehaviorDataError(ValueError):
    """행동 자료의 구조나 참조가 올바르지 않다."""


@dataclass(frozen=True)
class Behavior:
    label: str
    start: float
    end: float


@dataclass(frozen=True)
class Routine:
    start: int
    end: int
    feeds: float
    awake_seconds: float
    diapers: float


@dataclass(frozen=True)
class Source:
    name: str
    url: str


@dataclass(frozen=True)
class Catalog:
    behaviors: dict[str, Behavior]
    routines: tuple[Routine, ...]
    cry_order: tuple[str, ...]
    months: frozenset[int]
    sources: tuple[Source, ...]

    def routine_at(self, month: int) -> Routine:
        return next(row for row in reversed(self.routines) if row.start <= month <= row.end)


def rows(directory: Path, filename: str, *required: str) -> list[dict[str, str]]:
    with (directory / filename).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not set(required).issubset(reader.fieldnames or ()):
            raise BehaviorDataError(f"{filename}에 필수 열이 없습니다.")
        result = list(reader)
        if not result or any(row[key] is None for row in result for key in required):
            raise BehaviorDataError(f"{filename}에 불완전한 행이 있습니다.")
        return result


def midpoint(low: str, high: str | None) -> float:
    return (float(low) + float(high or low)) / 2


def count(text: str) -> float:
    match = re.match(r"(\d+)(?:~(\d+))?", text.rsplit("이후 ", 1)[-1])
    if match is None:
        raise BehaviorDataError("일과 자료의 횟수를 읽을 수 없습니다.")
    low, high = match.groups()
    if int(low) < 1 or (high and int(high) < int(low)):
        raise BehaviorDataError("일과 자료의 횟수 범위를 확인해 주세요.")
    return midpoint(low, high)


def awake_seconds(text: str) -> float:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(시간|분)?~(\d+(?:\.\d+)?)(시간|분)", text)
    if match is None:
        raise BehaviorDataError("일과 자료의 깨어 있는 시간을 읽을 수 없습니다.")
    low, low_unit, high, high_unit = match.groups()
    start = float(low) * (60 if (low_unit or high_unit) == "분" else 3600)
    end = float(high) * (60 if high_unit == "분" else 3600)
    if not 0 < start <= end <= 86400:
        raise BehaviorDataError("일과 자료의 시간 범위를 확인해 주세요.")
    return (start + end) / 2


def load_catalog(directory: Path = DATA_PATH) -> Catalog:
    try:
        return _read_catalog(directory)
    except BehaviorDataError:
        raise
    except (OSError, ValueError, csv.Error):
        raise BehaviorDataError("아기 행동 CSV의 경로와 값 형식을 확인해 주세요.") from None


def _read_catalog(directory: Path) -> Catalog:
    behaviors: dict[str, Behavior] = {}
    for row in rows(directory, "behaviors.csv", "ID", "행동", "시작 월령", "끝 월령", "AI 욕구·신호 매핑"):
        key = row["ID"]
        start, end = float(row["시작 월령"]), float(row["끝 월령"])
        if not re.fullmatch(r"B\d{3}", key) or key in behaviors or not row["행동"].strip():
            raise BehaviorDataError("행동 ID 또는 행동 이름을 확인해 주세요.")
        # 원본에는 영아기 이후에도 지속되는 행동의 범위가 있다.
        if not 0 <= start <= end <= 60:
            raise BehaviorDataError("행동 자료의 월령 범위를 확인해 주세요.")
        behaviors[key] = Behavior(row["행동"], start, end)

    ranges = {
        **dict.fromkeys(NEEDS, "0~1"),
        "stimulation": "-1~1", "mood": "-1~1", "temperature": "-1~1", "illness": "0~1",
        "월령": "on/off",
    }
    variables = set()
    for row in rows(directory, "ai_mapping.csv", "내부 변수", "범위", "관련 행동 ID(행동목록)"):
        if not row["범위"]:
            continue  # 표 뒤의 설계 메모
        key, *_ = row["내부 변수"].split()
        refs = {ref.strip() for ref in row["관련 행동 ID(행동목록)"].split(",")}
        if ranges.get(key) != row["범위"] or key in variables or not refs <= behaviors.keys():
            raise BehaviorDataError("AI 매핑의 변수, 범위 또는 행동 ID를 확인해 주세요.")
        variables.add(key)
    if variables != ranges.keys():
        raise BehaviorDataError("AI 매핑에 필수 변수가 없습니다.")

    routines = []
    for row in rows(directory, "daily_routine.csv", "월령대", "수유 횟수/일", "깨어 있는 시간(한 번)", "젖은 기저귀/일"):
        if not row["수유 횟수/일"]:
            continue  # 표 뒤의 출처 메모
        match = re.fullmatch(r"(\d+)~(\d+)개월", row["월령대"])
        if match is None:
            raise BehaviorDataError("일과 자료의 월령대를 확인해 주세요.")
        start, end = map(int, match.groups())
        if not start < end <= 12 or start != (routines[-1].end if routines else 0):
            raise BehaviorDataError("일과 자료의 월령대는 0~12개월을 순서대로 덮어야 합니다.")
        routines.append(Routine(start, end, count(row["수유 횟수/일"]),
                                awake_seconds(row["깨어 있는 시간(한 번)"]), count(row["젖은 기저귀/일"])))
    if not routines or routines[-1].end != 12:
        raise BehaviorDataError("12개월까지 일과 자료가 필요합니다.")

    cry_order: list[str] = []
    for row in rows(directory, "cry_causes.csv", "원인", "상황 단서(먼저 확인)", "AI 변수"):
        raw = row["AI 변수"]
        if raw in {"", "temperature", "pain/illness", "teething", "colic(이벤트)"}:
            continue
        key = CRY_KEYS.get(raw, raw)
        if key not in (NEEDS - {"stimulation"}) | set(CRY_KEYS.values()) or not row["상황 단서(먼저 확인)"]:
            raise BehaviorDataError("울음 자료의 변수와 상황 단서를 확인해 주세요.")
        if key not in cry_order:
            cry_order.append(key)
    if set(cry_order) != (NEEDS - {"stimulation"}) | set(CRY_KEYS.values()):
        raise BehaviorDataError("울음 자료에 시뮬레이션 변수가 빠져 있습니다.")

    summary = rows(directory, "monthly_summary.csv", "월령(개월)", "소리·언어")
    months = [int(row["월령(개월)"]) for row in summary if not row["월령(개월)"].startswith("출처:")]
    if months != list(range(13)):
        raise BehaviorDataError("월령 요약은 0~12개월을 순서대로 포함해야 합니다.")

    sources = []
    for row in rows(directory, "sources.csv", "약어", "기관·자료", "링크"):
        if not row["링크"]:
            continue
        for url in row["링크"].split(" / "):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or not row["기관·자료"].strip():
                raise BehaviorDataError("자료 출처의 이름과 HTTPS 링크를 확인해 주세요.")
            sources.append(Source(row["기관·자료"], url))
    if not sources:
        raise BehaviorDataError("행동 자료의 출처가 없습니다.")
    return Catalog(behaviors, tuple(routines), tuple(cry_order), frozenset(months), tuple(sources))
