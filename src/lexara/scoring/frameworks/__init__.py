"""Built-in framework instances."""

from lexara.scoring.frameworks.atos_estimated import AtosEstimated
from lexara.scoring.frameworks.dale_chall import DaleChall
from lexara.scoring.frameworks.flesch_kincaid import FleschKincaidGrade
from lexara.scoring.frameworks.lexile_estimated import LexileEstimated

BUILTIN_FRAMEWORKS = [
    FleschKincaidGrade(),
    DaleChall(),
    AtosEstimated(),
    LexileEstimated(),
]

__all__ = [
    "AtosEstimated",
    "DaleChall",
    "FleschKincaidGrade",
    "LexileEstimated",
    "BUILTIN_FRAMEWORKS",
]
