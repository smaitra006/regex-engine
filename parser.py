from typing import List, Set
from lexer import Lexer, Token, TokenType
from ast_nodes import *


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.group_counter = 0

    def current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek_token(self, offset: int = 1) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]

    def advance(self) -> Token:
        token = self.current_token()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        token = self.current_token()
        if token.type != token_type:
            raise ValueError(
                f"Expected {token_type}, got {token.type} at position {token.position}")
        return self.advance()

    def parse(self) -> ASTNode:
        # The entry point always calls the lowest-precedence operator first.
        ast = self.parse_alternation()

        if self.current_token().type != TokenType.EOF:
            token = self.current_token()
            raise ValueError(
                f"Unexpected token {token.type} at position {token.position}")
        return ast

    # Precedence Level 4 (Lowest): Alternation ( | )
    def parse_alternation(self) -> ASTNode:
        alternatives = [self.parse_concat()]

        while self.current_token().type == TokenType.PIPE:
            self.advance()
            alternatives.append(self.parse_concat())

        if len(alternatives) == 1:
            return alternatives[0]
        return AlternationNode(alternatives)

    # Precedence Level 3: Concatenation ( ab )
    def parse_concat(self) -> ASTNode:
        items = []

        while True:
            token = self.current_token()
            # Stop concatenation if we hit an alternation, a closing parenthesis, or EOF
            if token.type in (TokenType.PIPE, TokenType.RPAREN, TokenType.EOF):
                break

            # Literal characters outside of special meaning
            if token.type in (TokenType.DASH, TokenType.COMMA):
                self.advance()
                items.append(CharNode(token.value))
                continue

            items.append(self.parse_quantified())

        if len(items) == 0:
            return ConcatNode([])
        if len(items) == 1:
            return items[0]
        return ConcatNode(items)

    # Precedence Level 2: Quantifiers ( *, +, ?, {n,m} )
    def parse_quantified(self) -> ASTNode:
        atom = self.parse_atom()
        token = self.current_token()

        if token.type == TokenType.STAR:
            self.advance()
            return QuantifierNode(atom, 0, None, not self._check_lazy_modifier())
        elif token.type == TokenType.PLUS:
            self.advance()
            return QuantifierNode(atom, 1, None, not self._check_lazy_modifier())
        elif token.type == TokenType.QUESTION:
            self.advance()
            return QuantifierNode(atom, 0, 1, not self._check_lazy_modifier())
        elif token.type == TokenType.LBRACE:
            return self._parse_range_quantifier(atom)

        return atom

    def _check_lazy_modifier(self) -> bool:
        if self.current_token().type == TokenType.QUESTION:
            self.advance()
            return True
        return False

    def _parse_range_quantifier(self, atom: ASTNode) -> ASTNode:
        self.expect(TokenType.LBRACE)
        token = self.current_token()

        if token.type != TokenType.CHAR or not token.value.isdigit():
            raise ValueError(
                f"Expected number in quantifier at position {token.position}")

        min_count = int(token.value)
        self.advance()
        max_count = min_count

        if self.current_token().type == TokenType.COMMA:
            self.advance()
            token = self.current_token()
            if token.type == TokenType.RBRACE:
                max_count = None
            elif token.type == TokenType.CHAR and token.value.isdigit():
                max_count = int(token.value)
                self.advance()
            else:
                raise ValueError(
                    f"Expected number or '}}' at position {token.position}")

        self.expect(TokenType.RBRACE)
        return QuantifierNode(atom, min_count, max_count, not self._check_lazy_modifier())

    # Precedence Level 1 (Highest): Atoms (Chars, Groups, Anchors)
    def parse_atom(self) -> ASTNode:
        token = self.current_token()

        if token.type == TokenType.CHAR:
            self.advance()
            return CharNode(token.value)
        elif token.type == TokenType.DOT:
            self.advance()
            return DotNode()
        elif token.type == TokenType.CARET:
            self.advance()
            return AnchorNode("^")
        elif token.type == TokenType.DOLLAR:
            self.advance()
            return AnchorNode("$")
        elif token.type == TokenType.WORD_BOUNDARY:
            self.advance()
            return AnchorNode("b")
        elif token.type == TokenType.NON_WORD_BOUNDARY:
            self.advance()
            return AnchorNode("B")
        elif token.type == TokenType.DIGIT:
            self.advance()
            return PredefinedClassNode("d")
        elif token.type == TokenType.NON_DIGIT:
            self.advance()
            return PredefinedClassNode("D")
        elif token.type == TokenType.WHITESPACE:
            self.advance()
            return PredefinedClassNode("s")
        elif token.type == TokenType.NON_WHITESPACE:
            self.advance()
            return PredefinedClassNode("S")
        elif token.type == TokenType.WORD:
            self.advance()
            return PredefinedClassNode("w")
        elif token.type == TokenType.NON_WORD:
            self.advance()
            return PredefinedClassNode("W")
        elif token.type == TokenType.BACKREF:
            self.advance()
            return BackreferenceNode(int(token.value))
        elif token.type == TokenType.LBRACKET:
            return self._parse_char_class()
        elif token.type == TokenType.LPAREN:
            return self._parse_group()
        elif token.type == TokenType.NON_CAPTURING:
            return self._parse_non_capturing_group()
        elif token.type == TokenType.LOOKAHEAD_POS:
            return self._parse_lookahead(positive=True)
        elif token.type == TokenType.LOOKAHEAD_NEG:
            return self._parse_lookahead(positive=False)
        elif token.type == TokenType.LOOKBEHIND_POS:
            return self._parse_lookbehind(positive=True)
        elif token.type == TokenType.LOOKBEHIND_NEG:
            return self._parse_lookbehind(positive=False)
        else:
            raise ValueError(
                f"Unexpected token {token.type} at position {token.position}")

    def _parse_char_class(self) -> CharClassNode:
        self.expect(TokenType.LBRACKET)
        negated = False
        if self.current_token().type == TokenType.CARET:
            negated = True
            self.advance()

        chars: Set[str] = set()

        while self.current_token().type != TokenType.RBRACKET:
            token = self.current_token()

            if token.type == TokenType.EOF:
                raise ValueError("Unclosed character class")

            # Handle Range (e.g., a-z)
            if token.type == TokenType.CHAR:
                char = token.value
                self.advance()
                if self.current_token().type == TokenType.DASH:
                    next_token = self.peek_token()
                    if next_token.type == TokenType.CHAR:
                        self.advance()  # consume dash
                        end_char = self.current_token().value
                        self.advance()  # consume end char
                        start_ord, end_ord = ord(char), ord(end_char)
                        if start_ord > end_ord:
                            raise ValueError(
                                f"Invalid range {char}-{end_char}")
                        for code in range(start_ord, end_ord + 1):
                            chars.add(chr(code))
                    else:
                        chars.add(char)
                        chars.add("-")
                        self.advance()
                else:
                    chars.add(char)
            # Pre-defined classes inside brackets like [\d\s]
            elif token.type == TokenType.DIGIT:
                self.advance()
                chars.update("0123456789")
            elif token.type == TokenType.WORD:
                self.advance()
                chars.update(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
            elif token.type == TokenType.WHITESPACE:
                self.advance()
                chars.update("\t\n\r\f\v")
            # OPTIMIZATION: Everything else inside a bracket is just treated as a literal character!
            elif token.value is not None:
                chars.add(token.value)
                self.advance()
            else:
                raise ValueError(
                    f"Unexpected token {token.type} in character class")

        self.expect(TokenType.RBRACKET)
        if not chars:
            raise ValueError("Empty character class")

        return CharClassNode(chars, negated)

    # Note how _parse_group calls self.parse_alternation() again!
    def _parse_group(self) -> GroupNode:
        self.expect(TokenType.LPAREN)
        self.group_counter += 1
        group_num = self.group_counter

        # This is the "Recursive" part of Recursive Descent
        child = self.parse_alternation()

        self.expect(TokenType.RPAREN)
        return GroupNode(child, group_num)

    def _parse_non_capturing_group(self) -> NonCapturingGroupNode:
        self.advance()
        child = self.parse_alternation()
        self.expect(TokenType.RPAREN)
        return NonCapturingGroupNode(child)

    def _parse_lookahead(self, positive: bool) -> LookAheadNode:
        self.advance()
        child = self.parse_alternation()
        self.expect(TokenType.RPAREN)
        return LookAheadNode(child, positive)

    def _parse_lookbehind(self, positive: bool) -> LookBehindNode:
        self.advance()
        child = self.parse_alternation()
        self.expect(TokenType.RPAREN)
        return LookBehindNode(child, positive)
