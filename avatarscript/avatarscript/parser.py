"""Lark parser entry point for AvatarScript."""
from pathlib import Path
from lark import Lark, UnexpectedInput
from avatarscript.lexer import AvatarIndenter
from avatarscript.ast.nodes import SceneNode, SourceLocation
from avatarscript.ast.builder import ASTBuilder


class AvatarSyntaxError(Exception):
    """Syntax error raised when an .ava script violates the grammar."""

    def __init__(self, message: str, loc: SourceLocation):
        super().__init__(f"Line {loc.line}, Col {loc.column}: {message}")
        self.message = message
        self.loc = loc


class AvatarParser:
    def __init__(self) -> None:
        grammar_path = Path(__file__).resolve().parent / "grammar.lark"
        grammar_text = grammar_path.read_text(encoding="utf-8")
        self._lark = Lark(
            grammar_text,
            parser="lalr",
            postlex=AvatarIndenter(),
            propagate_positions=True,
        )
        self._builder = ASTBuilder()

    def parse(self, source_text: str) -> SceneNode:
        """Parse an .ava script string into a typed SceneNode AST."""
        # Ensure trailing newline for clean DEDENT emission at EOF
        if not source_text.endswith("\n"):
            source_text = source_text + "\n"
        try:
            tree = self._lark.parse(source_text)
            return self._builder.transform(tree)
        except UnexpectedInput as exc:
            line = getattr(exc, "line", 1) or 1
            col = getattr(exc, "column", 1) or 1
            loc = SourceLocation(line=line, column=col)
            context = exc.get_context(source_text) if hasattr(exc, "get_context") else ""
            msg = f"Syntax error near line {line}, column {col}:\n{context}".strip()
            raise AvatarSyntaxError(msg, loc) from exc
