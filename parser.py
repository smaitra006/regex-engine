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
                f"Expected {token_type}, got {token.type} at position {token.position}"
            )
        return self.advance()

    def parse(self) -> ASTNode:
        ast = self.parse_alternation()

        if self.current_token().type != TokenType.EOF:
            token = self.current_token()
            raise ValueError(
                f"Unexpected token {token.type} at position {token.position}")

        return ast

    def parse_alternation(self) -> ASTNode:
        alternatives = [self.parse_concat()]

        while self.current_token().type == TokenType.PIPE:
            self.advance()
            alternatives.append(self.parse_concat())

        if len(alternatives) == 1:
            return alternatives[0]

        return AlternationNode(alternatives)

    def parse_concat(self) -> ASTNode:
        items = []

        while True:
            token = self.current_token()

            if token.type in (TokenType.PIPE, TokenType.RPAREN, TokenType.EOF):
                break

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

    def parse_quantified(self) -> ASTNode:
        atom = self.parse_atom()

        token = self.current_token()

        if token.type == TokenType.STAR:
            self.advance()
            greedy = not self._check_lazy_modifier()
            return QuantifierNode(atom, 0, None, greedy)
        elif token.type == TokenType.PLUS:
            self.advance()
            greedy = not self._check_lazy_modifier()
            return QuantifierNode(atom, 1, None, greedy)
        elif token.type == TokenType.QUESTION:
            self.advance()
            greedy = not self._check_lazy_modifier()
            return QuantifierNode(atom, 0, 1, greedy)
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
        greedy = not self._check_lazy_modifier()

        return QuantifierNode(atom, min_count, max_count, greedy)

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

            if token.type == TokenType.CHAR:
                char = token.value
                self.advance()

                if self.current_token().type == TokenType.DASH:
                    next_token = self.peek_token()
                    if next_token.type == TokenType.CHAR:
                        self.advance()
                        end_char = self.current_token().value
                        self.advance()

                        start_ord = ord(char)
                        end_ord = ord(end_char)

                        if start_ord > end_ord:
                            raise ValueError(
                                f"Invalid range {char}-{end_char} : start > end")

                        for code in range(start_ord, end_ord + 1):
                            chars.add(chr(code))

                    else:
                        chars.add(char)
                        chars.add("-")
                        self.advance()
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
                elif token.type == TokenType.DASH:
                    self.advance()
                    chars.add("-")
                elif token.type in (
                    TokenType.PLUS,
                    TokenType.STAR,
                    TokenType.QUESTION,
                    TokenType.DOT,
                    TokenType.PIPE,
                    TokenType.CARET,
                    TokenType.DOLLAR,
                    TokenType.LBRACE,
                    TokenType.RBRACE,
                    TokenType.LPAREN,
                    TokenType.RPAREN,
                ):
                    self.advance()
                    chars.add(token.value)
                else:
                    raise ValueError(
                        f"Unexpected token {token.type} in character class at position")

        self.expect(TokenType.RBRACKET)

        if not chars:
            raise ValueError("Empty character class")

        return CharClassNode(chars, negated)

    def _parse_group(self) -> GroupNode:
        self.expect(TokenType.LPAREN)

        self.group_counter += 1
        group_num = self.group_counter

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


lexer = Lexer(r"ab*c|d")
tokens = lexer.tokenize()
parser = Parser(tokens)
print(parser.parse())
