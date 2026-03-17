from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class ASTNode:
    """Base marker class for all AST nodes.
    In a more complex compiler, this might define an accept() method for the Visitor pattern."""
    pass


@dataclass
class CharNode(ASTNode):
    char: str

    def __repr__(self):
        return f"Char({self.char!r})"


@dataclass
class DotNode(ASTNode):
    def __repr__(self):
        return "Dot(.)"


@dataclass
class CharClassNode(ASTNode):
    chars: Set[str]
    negated: bool = False  # True for [^abc]

    def __repr__(self):
        prefix = "^" if self.negated else ""
        chars_list = sorted(self.chars)
        # 1. OPTIMIZATION: Use Pythonic array slicing instead of a generator in a range loop
        chars_str = "".join(chars_list[:10])
        if len(chars_list) > 10:
            chars_str += "..."
        return f"CharClass([{prefix}{chars_str}])"


@dataclass
class PredefinedClassNode(ASTNode):
    class_type: str  # d, D, w, W, s, S

    def __repr__(self):
        return f"PredefinedClass(\\{self.class_type})"


@dataclass
class QuantifierNode(ASTNode):
    child: ASTNode
    min_count: int
    max_count: Optional[int]  # None means unlimited
    greedy: bool = True       # False for lazy quantifiers (*?, +?)

    def __repr__(self):
        # 2. OPTIMIZATION: Cleaned up the formatting logic for better readability
        q_str = ""
        if self.min_count == 0 and self.max_count == 1:
            q_str = "?"
        elif self.min_count == 0 and self.max_count is None:
            q_str = "*"
        elif self.min_count == 1 and self.max_count is None:
            q_str = "+"
        else:
            q_str = f"{{{self.min_count},{self.max_count if self.max_count is not None else ''}}}"

        if not self.greedy:
            q_str += "?"

        return f"Quantifier({self.child} {q_str})"


@dataclass
class ConcatNode(ASTNode):
    children: List[ASTNode]

    def __repr__(self):
        return f"Concat({len(self.children)} items)"


@dataclass
class AlternationNode(ASTNode):
    alternatives: List[ASTNode]

    def __repr__(self):
        return f"Alternation({len(self.alternatives)} branches)"


@dataclass
class GroupNode(ASTNode):
    child: ASTNode
    group_number: int

    def __repr__(self):
        return f"Group#{self.group_number}({self.child})"


@dataclass
class NonCapturingGroupNode(ASTNode):
    child: ASTNode

    def __repr__(self):
        return f"NonCapturingGroup({self.child})"


@dataclass
class BackreferenceNode(ASTNode):
    group_number: int

    def __repr__(self):
        return f"Backref(\\{self.group_number})"


@dataclass
class AnchorNode(ASTNode):
    anchor_type: str  # ^, $, b, B

    def __repr__(self):
        symbols = {"^": "^", "$": "$", "b": r"\b", "B": r"\B"}
        return f"Anchor({symbols.get(self.anchor_type, self.anchor_type)})"


@dataclass
class LookAheadNode(ASTNode):
    child: ASTNode
    positive: bool = True

    def __repr__(self):
        prefix = "?=" if self.positive else "?!"
        return f"LookAhead{prefix}({self.child})"


@dataclass
class LookBehindNode(ASTNode):
    child: ASTNode
    positive: bool = True

    def __repr__(self):
        prefix = "?<=" if self.positive else "?<!"
        return f"LookBehind{prefix}({self.child})"
