from typing import Optional, Dict, Iterator, List
from dataclasses import dataclass
from ast_nodes import *


@dataclass
class Match:
    start: int
    end: int
    text: str
    groups: Dict[int, Optional[str]]

    def group(self, n: int = 0) -> Optional[str]:
        if n == 0:
            return self.text
        return self.groups.get(n)


class Matcher:
    def __init__(self, ast: ASTNode, flags: Optional[Dict[str, bool]] = None):
        self.ast = ast
        self.flags = flags or {}

        self.ignore_case = self.flags.get("ignorecase", False)
        self.multiline = self.flags.get("multiline", False)
        self.dotall = self.flags.get("dotall", False)

        self.text = ""
        self.length = 0
        self.captures: Dict[int, Optional[str]] = {}

    def search(self, text: str) -> Optional[Match]:
        """Searches for the first occurrence of the pattern in the text."""
        self.text = text
        self.length = len(text)

        # Try matching starting at every possible index (O(N) outer loop)
        for start_pos in range(self.length + 1):
            self.captures = {}
            # We only care about the FIRST successful full path yielded
            for end_pos in self._match_node(self.ast, start_pos):
                return Match(start_pos, end_pos, self.text[start_pos:end_pos], self.captures.copy())
        return None

    def match(self, text: str) -> Optional[Match]:
        """Matches only if the pattern matches at the very beginning of the text."""
        self.text = text
        self.length = len(text)
        self.captures = {}

        for end_pos in self._match_node(self.ast, 0):
            return Match(0, end_pos, self.text[0:end_pos], self.captures.copy())
        return None

    # --- THE BACKTRACKING GENERATOR ENGINE ---
    def _match_node(self, node: ASTNode, pos: int) -> Iterator[int]:
        """Yields all possible valid end positions for this node."""
        if isinstance(node, CharNode):
            yield from self._match_char(node, pos)
        elif isinstance(node, DotNode):
            yield from self._match_dot(node, pos)
        elif isinstance(node, CharClassNode):
            yield from self._match_char_class(node, pos)
        elif isinstance(node, PredefinedClassNode):
            yield from self._match_predefined(node, pos)
        elif isinstance(node, ConcatNode):
            yield from self._match_concat(node.children, pos)
        elif isinstance(node, AlternationNode):
            yield from self._match_alternation(node, pos)
        elif isinstance(node, QuantifierNode):
            yield from self._match_quantifier(node, pos, 0)
        elif isinstance(node, GroupNode):
            yield from self._match_group(node, pos)
        elif isinstance(node, BackreferenceNode):
            yield from self._match_backref(node, pos)
        elif isinstance(node, AnchorNode):
            yield from self._match_anchor(node, pos)
        elif isinstance(node, LookAheadNode):
            yield from self._match_lookahead(node, pos)

    # --- TERMINAL NODES (Base Cases) ---
    def _match_char(self, node: CharNode, pos: int) -> Iterator[int]:
        if pos < self.length:
            t_char = self.text[pos].lower(
            ) if self.ignore_case else self.text[pos]
            p_char = node.char.lower() if self.ignore_case else node.char
            if t_char == p_char:
                yield pos + 1

    def _match_dot(self, node: DotNode, pos: int) -> Iterator[int]:
        if pos < self.length:
            if self.dotall or self.text[pos] != "\n":
                yield pos + 1

    def _match_char_class(self, node: CharClassNode, pos: int) -> Iterator[int]:
        if pos < self.length:
            char = self.text[pos].lower(
            ) if self.ignore_case else self.text[pos]
            chars = set(c.lower()
                        for c in node.chars) if self.ignore_case else node.chars
            if (char in chars) != node.negated:
                yield pos + 1

    def _match_predefined(self, node: PredefinedClassNode, pos: int) -> Iterator[int]:
        if pos < self.length:
            char = self.text[pos]
            # Simplistic representation for brevity
            mapping = {
                "d": char.isdigit(),
                "D": not char.isdigit(),
                "s": char.isspace(),
                "S": not char.isspace(),
                "w": char.isalnum() or char == "_",
                "W": not (char.isalnum() or char == "_")
            }
            if mapping.get(node.class_type, False):
                yield pos + 1

    # --- STRUCTURAL NODES (The Magic) ---
    def _match_concat(self, nodes: List[ASTNode], pos: int) -> Iterator[int]:
        # Base case: empty concatenation matches without consuming
        if not nodes:
            yield pos
            return

        # Recursive Descent Backtracking
        for next_pos in self._match_node(nodes[0], pos):
            yield from self._match_concat(nodes[1:], next_pos)

    def _match_alternation(self, node: AlternationNode, pos: int) -> Iterator[int]:
        # Try left branch. If it fails, the loop continues and tries the right branch.
        for alt in node.alternatives:
            yield from self._match_node(alt, pos)

    def _match_quantifier(self, node: QuantifierNode, pos: int, count: int) -> Iterator[int]:
        # If we hit max constraints, stop recursing and yield.
        if node.max_count is not None and count == node.max_count:
            yield pos
            return

        # GREEDY: Try to match deeply first, yield current pos as a fallback.
        if node.greedy:
            for next_pos in self._match_node(node.child, pos):
                # Prevent infinite loops on zero-width matches (e.g., A* on empty string)
                if next_pos == pos and count > 0:
                    continue
                yield from self._match_quantifier(node, next_pos, count + 1)

            # Fallback (Backtrack): If deep matching failed or exhausted, yield current
            if count >= node.min_count:
                yield pos

        # LAZY: Yield current pos first (if valid), then try deeper matching.
        else:
            if count >= node.min_count:
                yield pos
            for next_pos in self._match_node(node.child, pos):
                if next_pos == pos and count > 0:
                    continue
                yield from self._match_quantifier(node, next_pos, count + 1)

    # --- STATE AND LOOKAROUNDS ---
    def _match_group(self, node: GroupNode, pos: int) -> Iterator[int]:
        old_capture = self.captures.get(node.group_number)

        for next_pos in self._match_node(node.child, pos):
            # Save state
            self.captures[node.group_number] = self.text[pos:next_pos]
            yield next_pos
            # Restore state upon backtracking failure
            self.captures[node.group_number] = old_capture

    def _match_backref(self, node: BackreferenceNode, pos: int) -> Iterator[int]:
        target = self.captures.get(node.group_number)
        if target is not None:
            end_pos = pos + len(target)
            if end_pos <= self.length and self.text[pos:end_pos] == target:
                yield end_pos

    def _match_lookahead(self, node: LookAheadNode, pos: int) -> Iterator[int]:
        # We try to find AT LEAST ONE valid match ahead
        matched = any(self._match_node(node.child, pos))
        if matched == node.positive:
            yield pos  # Yield current position without consuming characters!

    def _match_anchor(self, node: AnchorNode, pos: int) -> Iterator[int]:
        if node.anchor_type == "^" and pos == 0:
            yield pos
        elif node.anchor_type == "$" and pos == self.length:
            yield pos
