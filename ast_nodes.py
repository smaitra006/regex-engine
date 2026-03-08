from dataclasses import dataclass
from typing import List, Optional, Set

@dataclass
class ASTNode:
    pass

@dataclass
class CharNode(ASTNode):
    char: str

    def __repr__(self):
        return f"Char({self.char!r})" # Char(a)

@dataclass
class DotNode(ASTNode):
    def __repr__(self):
        return "Dot(.)"

@dataclass
class CharClassNode(ASTNode):
    chars: Set[str]
    negated: bool = False # True for [^abc]
    def __repr__(self):
        prefix = "^" if self.negated else ""
        chars_str = "".join(sorted(self.chars)[:10])
        if len(self.chars) > 0:
            chars_str += "..."
        return f"CharClass([{prefix}{chars_str}])"

@dataclass
class PredefinedClassNode(ASTNode):
    class_type: str # d D, w, W, s, S

    def __repr__(self):
        return f"PredefinedClass(\\{self.class_type})"

@dataclass
class QuantifierNode(ASTNode):
    child: ASTNode
    min_count: int
    max_count: Optional[int] # none means unlimited
    greedy: bool = True # false for lazy quantifiers (*?, +?, ??, {n, m}?)

    def __repr__(self):
        if self.min_count == 0 and self.max_count == 1:
            q = "?" if self.greedy else "??"
        elif self.min_count == 0 and self.max_count is None:
            q = "*" if self.greedy else "*?"
        elif self.min_count == 1 and self.max_count is None:
            q = "+" if self.greedy else "+?"
        else:
            q = f"{{{self.min_count}, {self.max_count}}}"
            if not self.greedy:
                q += "?"
        return f"Quantifier({self.child} {q})"

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
    anchor_type: str # ^, $, b, B

    def __repr__(self):
        symbols = {"^": "^", "$": "$", "b": r"\b", "B": r"\B"}
        return f"Anchor({symbols.get(self.anchor_type, self.anchor_type)})"

@dataclass
class LookAheadNode(ASTNode):
    child: ASTNode
    positive: bool = True

    def __repr__(self):
        prefix = "?=" if self.positive else "?!"
        return f"LookAhead{prefix}{self.child}"

@dataclass
class LookBehindNode(ASTNode):
    child: ASTNode
    positive: bool = True

    def __repr__(self):
        prefix = "?<=" if self.positive else "?<!"
        return f"LookBehind{prefix}{self.child}"
