from dataclasses import dataclass
from typing import Literal

Care = Literal["feed", "burp", "diaper", "sleep", "hold"]
SECONDS_PER_DAY = 86_400
REPEAT_SECONDS = 4
SAVE_SECONDS = 30
POINTS_PER_MONTH = 10
PROGRAM_DAYS = 28
MAX_MONTH = 12
MIN_EFFECTIVE_CHANGE = 0.05
EARLY_SLEEP_THRESHOLD = 0.30
ATTACHMENT_DECAY_SECONDS = 10_800
BOREDOM_SECONDS = 7_200
GAS_DECAY_SECONDS = 3_600
MOOD_DECAY = 0.98

# 포인트는 가상 아기의 월령 진행에만 사용한다.
CARE_DELTAS: dict[Care, dict[str, float]] = {
    "feed": {"hunger": -0.65, "gas": 0.24},
    "burp": {"gas": -0.60},
    "diaper": {"diaper": -0.85},
    "sleep": {"sleepiness": -0.70},
    "hold": {"attachment": 0.55},
}


@dataclass(frozen=True)
class Action:
    name: str
    face: str
    sound: str | None = None
    duration: int = 2


@dataclass(frozen=True)
class Signal:
    rule: str
    behavior_id: str
    action: Action
    emotion: str
    threshold: float = 0.0
    reaction: bool = False


NEUTRAL = Action("neutral", "neutral")
SIGNALS = {
    "hunger": (
        Signal("hunger_cry", "B054", Action("cry", "cry"), "울음", 0.85),
        Signal("hunger_fuss", "B002", Action("fuss", "cry"), "칭얼", 0.70),
        Signal("hunger_mouth", "B001", Action("mouth", "curious"), "호기심", 0.50),
        Signal("hunger_cue", "B054", Action("fuss", "cry"), "칭얼", 0.65),
    ),
    "diaper": (Signal("diaper_fuss", "B055", Action("fuss", "cry"), "칭얼", 0.62),),
    "gas": (
        Signal("gas_legs", "B022", Action("fuss", "cry"), "칭얼", 0.60),
        Signal("gas_fuss", "B055", Action("fuss", "cry"), "칭얼", 0.65),
    ),
    "sleepiness": (
        Signal("overtired", "B041", Action("fuss", "cry"), "칭얼", 0.90),
        Signal("yawn", "B040", Action("yawn", "sleep"), "졸림", 0.55),
    ),
    "attachment": (Signal("want_hold", "B058", Action("cry", "cry"), "울음", 0.72),),
    "boredom": (Signal("boredom", "B160", Action("look_around", "curious"), "호기심", 0.55),),
    "overstimulation": (
        Signal("look_away", "B159", Action("look_away", "surprise"), "놀람", 0.70),
    ),
}
SLEEP = Signal("settle_to_sleep", "B042", Action("sleep", "sleep", duration=4), "졸림")
EARLY_SLEEP = Signal("not_sleepy_yet", "B040", Action("fuss", "cry"), "칭얼")
CALM = (
    Signal("calm_newborn", "B142", Action("smile", "smile"), "평온"),
    Signal("coo", "B129", Action("coo", "curious", "아우"), "호기심", reaction=True),
    Signal("laugh", "B131", Action("laugh", "smile", "아하"), "기쁨", reaction=True),
    Signal("joy", "B149", Action("joy", "smile"), "기쁨", reaction=True),
    Signal("babble", "B134", Action("babble", "smile", "바바바"), "기쁨", reaction=True),
    Signal("jargon", "B135", Action("jargon", "curious", "아바바"), "호기심", reaction=True),
    Signal("first_word", "B137", Action("first_word", "smile", "까꿍"), "기쁨", reaction=True),
)
