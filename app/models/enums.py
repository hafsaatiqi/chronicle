from enum import Enum


class Medium(str, Enum):
    BOOK = "BOOK"


class TagCategory(str, Enum):
    GENRE = "GENRE"
    MOOD = "MOOD"
    THEME = "THEME"
    PACING = "PACING"
    OTHER = "OTHER"


class TagSource(str, Enum):
    CATALOG = "CATALOG"
    USER_GENERATED = "USER_GENERATED"


class InteractionStatus(str, Enum):
    WANT_TO = "WANT_TO"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    DROPPED = "DROPPED"
    ON_HOLD = "ON_HOLD"


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
