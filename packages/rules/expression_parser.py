"""Deterministic expression parser for rule condition evaluation.

Implements a recursive descent parser that tokenises a condition expression
string, builds an AST, and evaluates it against a flat context dictionary.

Grammar (informal):
    expression     -> or_expr
    or_expr        -> and_expr ( OR and_expr )*
    and_expr       -> not_expr ( AND not_expr )*
    not_expr       -> NOT not_expr | comparison
    comparison     -> primary ( comp_op primary )?
    primary        -> LPAREN expression RPAREN | literal | field
    comp_op        -> '==' | '!=' | '<' | '>' | '<=' | '>='
    literal        -> STRING | NUMBER | BOOLEAN
    field          -> FIELD  (dotted identifier like event.delay_minutes)

IMPORTANT: This module intentionally avoids eval(), exec(), and compile().
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ExpressionValidationError(Exception):
    """Raised when an expression cannot be parsed or evaluated."""

    def __init__(self, message: str, position: int | None = None) -> None:
        self.position = position
        detail = f" at position {position}" if position is not None else ""
        super().__init__(f"{message}{detail}")


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


class TokenType(Enum):
    FIELD = auto()
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    EQ = auto()       # ==
    NEQ = auto()      # !=
    LT = auto()       # <
    GT = auto()       # >
    LTE = auto()      # <=
    GTE = auto()      # >=
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: Any
    position: int


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

# Order matters — longer operators must come before shorter ones.
_OPERATOR_MAP: list[tuple[str, TokenType]] = [
    ("==", TokenType.EQ),
    ("!=", TokenType.NEQ),
    ("<=", TokenType.LTE),
    (">=", TokenType.GTE),
    ("<", TokenType.LT),
    (">", TokenType.GT),
    ("(", TokenType.LPAREN),
    (")", TokenType.RPAREN),
]

_KEYWORD_MAP: dict[str, TokenType] = {
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "true": TokenType.BOOLEAN,
    "false": TokenType.BOOLEAN,
}

# Regex for a dotted identifier (field reference): e.g. event.delay_minutes
_FIELD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+")

# Regex for a bare identifier (keyword or single-segment field)
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Regex for a numeric literal (int or float)
_NUMBER_RE = re.compile(r"-?(?:\d+\.?\d*|\.\d+)")

# Regex for a quoted string (double or single quotes)
_STRING_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'')


def tokenize(expression: str) -> list[Token]:
    """Convert an expression string into a list of tokens.

    Raises :class:`ExpressionValidationError` on unrecognised input.
    """
    tokens: list[Token] = []
    pos = 0
    length = len(expression)

    while pos < length:
        # Skip whitespace
        if expression[pos].isspace():
            pos += 1
            continue

        # Check operators / punctuation
        matched_op = False
        for op_str, op_type in _OPERATOR_MAP:
            if expression[pos:pos + len(op_str)] == op_str:
                tokens.append(Token(type=op_type, value=op_str, position=pos))
                pos += len(op_str)
                matched_op = True
                break
        if matched_op:
            continue

        # Quoted string
        m = _STRING_RE.match(expression, pos)
        if m:
            # Group 1 is double-quoted content, group 2 is single-quoted content
            value = m.group(1) if m.group(1) is not None else m.group(2)
            tokens.append(Token(type=TokenType.STRING, value=value, position=pos))
            pos = m.end()
            continue

        # Number literal (must check before identifiers to handle negative numbers)
        m = _NUMBER_RE.match(expression, pos)
        if m:
            num_str = m.group()
            # Make sure this isn't just a minus sign before an identifier
            if num_str == "-" or (num_str.startswith("-") and pos > 0 and tokens and tokens[-1].type in (TokenType.NUMBER, TokenType.STRING, TokenType.BOOLEAN, TokenType.FIELD, TokenType.RPAREN)):
                # Treat as part of comparison, not a negative number — fall through
                pass
            else:
                value = float(num_str) if "." in num_str else int(num_str)
                tokens.append(Token(type=TokenType.NUMBER, value=value, position=pos))
                pos = m.end()
                continue

        # Dotted field reference (must check before bare identifier)
        m = _FIELD_RE.match(expression, pos)
        if m:
            word = m.group()
            tokens.append(Token(type=TokenType.FIELD, value=word, position=pos))
            pos = m.end()
            continue

        # Bare identifier (keyword or single-segment field)
        m = _IDENT_RE.match(expression, pos)
        if m:
            word = m.group()
            lower = word.lower()
            if lower in _KEYWORD_MAP:
                tt = _KEYWORD_MAP[lower]
                if tt == TokenType.BOOLEAN:
                    tokens.append(Token(type=TokenType.BOOLEAN, value=(lower == "true"), position=pos))
                else:
                    tokens.append(Token(type=tt, value=lower, position=pos))
            else:
                # Treat bare identifiers as field references
                tokens.append(Token(type=TokenType.FIELD, value=word, position=pos))
            pos = m.end()
            continue

        raise ExpressionValidationError(
            f"Unexpected character '{expression[pos]}'", position=pos
        )

    tokens.append(Token(type=TokenType.EOF, value=None, position=pos))
    return tokens


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


class ASTNode:
    """Base class for AST nodes."""
    pass


@dataclass(slots=True)
class BinaryOpNode(ASTNode):
    """A binary operation: AND, OR, or comparison."""
    operator: str
    left: ASTNode
    right: ASTNode


@dataclass(slots=True)
class UnaryOpNode(ASTNode):
    """A unary operation: NOT."""
    operator: str
    operand: ASTNode


@dataclass(slots=True)
class LiteralNode(ASTNode):
    """A literal value: string, number, or boolean."""
    value: Any


@dataclass(slots=True)
class FieldNode(ASTNode):
    """A field reference like event.delay_minutes."""
    name: str


# ---------------------------------------------------------------------------
# Recursive descent parser
# ---------------------------------------------------------------------------


class _Parser:
    """Internal recursive descent parser that converts tokens to an AST."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self) -> TokenType:
        return self._current().type

    def _advance(self) -> Token:
        tok = self._current()
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _expect(self, tt: TokenType) -> Token:
        tok = self._current()
        if tok.type != tt:
            raise ExpressionValidationError(
                f"Expected {tt.name} but got {tok.type.name} ('{tok.value}')",
                position=tok.position,
            )
        return self._advance()

    # ---- Grammar rules ----

    def parse(self) -> ASTNode:
        node = self._or_expr()
        if self._peek() != TokenType.EOF:
            tok = self._current()
            raise ExpressionValidationError(
                f"Unexpected token {tok.type.name} ('{tok.value}') after expression",
                position=tok.position,
            )
        return node

    def _or_expr(self) -> ASTNode:
        left = self._and_expr()
        while self._peek() == TokenType.OR:
            self._advance()
            right = self._and_expr()
            left = BinaryOpNode(operator="OR", left=left, right=right)
        return left

    def _and_expr(self) -> ASTNode:
        left = self._not_expr()
        while self._peek() == TokenType.AND:
            self._advance()
            right = self._not_expr()
            left = BinaryOpNode(operator="AND", left=left, right=right)
        return left

    def _not_expr(self) -> ASTNode:
        if self._peek() == TokenType.NOT:
            self._advance()
            operand = self._not_expr()
            return UnaryOpNode(operator="NOT", operand=operand)
        return self._comparison()

    def _comparison(self) -> ASTNode:
        left = self._primary()
        if self._peek() in (
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        ):
            op_tok = self._advance()
            right = self._primary()
            return BinaryOpNode(operator=op_tok.value, left=left, right=right)
        return left

    def _primary(self) -> ASTNode:
        tok = self._current()

        if tok.type == TokenType.LPAREN:
            self._advance()
            node = self._or_expr()
            self._expect(TokenType.RPAREN)
            return node

        if tok.type == TokenType.STRING:
            self._advance()
            return LiteralNode(value=tok.value)

        if tok.type == TokenType.NUMBER:
            self._advance()
            return LiteralNode(value=tok.value)

        if tok.type == TokenType.BOOLEAN:
            self._advance()
            return LiteralNode(value=tok.value)

        if tok.type == TokenType.FIELD:
            self._advance()
            return FieldNode(name=tok.value)

        raise ExpressionValidationError(
            f"Unexpected token {tok.type.name} ('{tok.value}')",
            position=tok.position,
        )


# ---------------------------------------------------------------------------
# AST evaluator
# ---------------------------------------------------------------------------


def _coerce_for_comparison(left: Any, right: Any) -> tuple[Any, Any]:
    """Try to make left and right comparable when their types differ."""
    if type(left) is type(right):
        return left, right

    # int vs float — promote int
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left), float(right)

    # string-to-number coercion for comparisons
    if isinstance(left, str) and isinstance(right, (int, float)):
        try:
            return float(left), float(right)
        except (ValueError, TypeError):
            pass
    if isinstance(right, str) and isinstance(left, (int, float)):
        try:
            return float(left), float(right)
        except (ValueError, TypeError):
            pass

    return left, right


def evaluate(ast: ASTNode, context: dict[str, Any]) -> bool:
    """Walk the AST and return a boolean result.

    The *context* maps field names (e.g. ``"event.delay_minutes"``) to their
    runtime values.

    Raises :class:`ExpressionValidationError` on evaluation errors such as
    referencing a field not present in the context.
    """
    result = _eval_node(ast, context)
    if isinstance(result, bool):
        return result
    # A non-boolean at the top level is truthy/falsy
    return bool(result)


def _eval_node(node: ASTNode, context: dict[str, Any]) -> Any:
    if isinstance(node, LiteralNode):
        return node.value

    if isinstance(node, FieldNode):
        if node.name in context:
            return context[node.name]
        raise ExpressionValidationError(
            f"Field '{node.name}' not found in context"
        )

    if isinstance(node, UnaryOpNode):
        if node.operator == "NOT":
            operand = _eval_node(node.operand, context)
            return not operand
        raise ExpressionValidationError(f"Unknown unary operator '{node.operator}'")

    if isinstance(node, BinaryOpNode):
        if node.operator == "AND":
            left = _eval_node(node.left, context)
            if not left:
                return False
            return bool(_eval_node(node.right, context))

        if node.operator == "OR":
            left = _eval_node(node.left, context)
            if left:
                return True
            return bool(_eval_node(node.right, context))

        # Comparison operators
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        left, right = _coerce_for_comparison(left, right)

        if node.operator == "==":
            return left == right
        if node.operator == "!=":
            return left != right
        if node.operator == "<":
            try:
                return left < right
            except TypeError:
                raise ExpressionValidationError(
                    f"Cannot compare {type(left).__name__} < {type(right).__name__}"
                )
        if node.operator == ">":
            try:
                return left > right
            except TypeError:
                raise ExpressionValidationError(
                    f"Cannot compare {type(left).__name__} > {type(right).__name__}"
                )
        if node.operator == "<=":
            try:
                return left <= right
            except TypeError:
                raise ExpressionValidationError(
                    f"Cannot compare {type(left).__name__} <= {type(right).__name__}"
                )
        if node.operator == ">=":
            try:
                return left >= right
            except TypeError:
                raise ExpressionValidationError(
                    f"Cannot compare {type(left).__name__} >= {type(right).__name__}"
                )

        raise ExpressionValidationError(f"Unknown operator '{node.operator}'")

    raise ExpressionValidationError(f"Unknown AST node type: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ExpressionParser:
    """High-level facade for parsing and evaluating rule condition expressions.

    Usage::

        parser = ExpressionParser()
        result = parser.evaluate(
            'event.delay_minutes > 30 AND event.vendor_priority == "high"',
            {"event.delay_minutes": 45, "event.vendor_priority": "high"},
        )
        assert result is True
    """

    def tokenize(self, expression: str) -> list[Token]:
        """Tokenise an expression string."""
        if not expression or not expression.strip():
            raise ExpressionValidationError("Expression cannot be empty")
        return tokenize(expression)

    def parse(self, tokens: list[Token]) -> ASTNode:
        """Parse a token list into an AST."""
        parser = _Parser(tokens)
        return parser.parse()

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """Tokenise, parse, and evaluate an expression in one step.

        Args:
            expression: The condition expression string.
            context: A dict mapping field names to their values.

        Returns:
            True if the expression evaluates to a truthy value.

        Raises:
            ExpressionValidationError: If the expression is syntactically
                invalid or references missing fields.
        """
        tokens = self.tokenize(expression)
        ast = self.parse(tokens)
        return evaluate(ast, context)

    def validate(self, expression: str) -> bool:
        """Check whether an expression is syntactically valid.

        Returns True if valid, raises :class:`ExpressionValidationError` if not.
        """
        tokens = self.tokenize(expression)
        self.parse(tokens)
        return True
