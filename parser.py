from typing import List, Set
from lexer import Token, TokenType
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
        self.parse_alternation()

    def parse_alternation(self) -> ASTNode:
        self.parse_concat()

    def parse_concat(self) -> ASTNode:
        items = []

        while True:
            token = self.current_token()

            if token.type in (TokenType.PIPE, TokenType.RPAREN, TokenType.EOF):
                break

            if token.type in (TokenType.DASH, TokenType.COMMA):
                self.advance()
                items.append(CharNode(token.value))

            self.parse_quantified()

        return ConcatNode(items)

    def parse_quantified(self) -> ASTNode:
        self.parse_atom()

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
                        char.add("-")
                        self.advance()
                elif token.type == TokenType.DIGIT:
                    self.advance()
                    chars.update("0123456789")
                elif token.type == TokenType.WORD:
                    self.advance()
                    chars.update("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
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
                    char.add(token.value)
                else:
                    raise ValueError(f"Unexpected token {token.type} in character class at position")

        self.expect(TokenType.RBRACKET)

        if not chars:
            raise ValueError("Empty character class")

        return CharClassNode(chars, negated)
