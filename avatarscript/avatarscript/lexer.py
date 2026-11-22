"""Indentation-aware lexer configuration for AvatarScript."""
from lark.indenter import Indenter


class AvatarIndenter(Indenter):
    NL_type = "_NL"
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4
