"""Expression mapping for layer-based 2D characters."""
from dataclasses import dataclass
from typing import Dict

VALID_EXPRESSIONS = {
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprised",
    "shocked",
    "smirk",
}


@dataclass(frozen=True)
class ExpressionAssets:
    eyes_asset: str
    mouth_asset: str


EXPRESSION_MAP: Dict[str, ExpressionAssets] = {
    "neutral": ExpressionAssets(eyes_asset="eyes_open.svg", mouth_asset="mouth_neutral.svg"),
    "happy": ExpressionAssets(eyes_asset="eyes_open.svg", mouth_asset="mouth_happy.svg"),
    "sad": ExpressionAssets(eyes_asset="eyes_open.svg", mouth_asset="mouth_sad.svg"),
    "angry": ExpressionAssets(eyes_asset="eyes_angry.svg", mouth_asset="mouth_angry.svg"),
    "surprised": ExpressionAssets(eyes_asset="eyes_open.svg", mouth_asset="mouth_surprised.svg"),
    "shocked": ExpressionAssets(eyes_asset="eyes_shocked.svg", mouth_asset="mouth_shocked.svg"),
    "smirk": ExpressionAssets(eyes_asset="eyes_open.svg", mouth_asset="mouth_smirk.svg"),
}


def resolve_expression_assets(expression: str, is_blinking: bool = False) -> ExpressionAssets:
    """Resolve the eye and mouth SVG filenames for a given expression and blink state."""
    base = EXPRESSION_MAP.get(expression, EXPRESSION_MAP["neutral"])
    if is_blinking:
        return ExpressionAssets(eyes_asset="eyes_closed.svg", mouth_asset=base.mouth_asset)
    return base
