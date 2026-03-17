from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Dict


class TokenType(Enum):
    CHAR = auto()  # regular character (A-Z, a-z, 0-9, etc)

    STAR = (
        auto()
    )  # '*' (zero or more) -> ab*c -> ac, abc, abbc, abbbc, ...

    PLUS = (
        auto()
    )  # + (one or more) -> ab+c -> abc, abbc, abbbc, abbbbc, ...
    QUESTION = (
        auto()
    )  # '?' (zero or one) -> colou?r -> color and colour

    # ranged quantifiers
    # {n} -> matches preciding token exactly n times
    # {n,} -> matches preciding token n or more times
    # {n, m} -> matches preciding token atleast n and atmost m times
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    COMMA = auto()  # ,

    # pipe -> OR -> http | https -> http or https
    PIPE = auto()

    # grouping
    # 1. quantifier -> (ha)+ -> ha, haha, hahaha, just ha+ -> ha, haa, haaa
    # 2. capture grouping -> to capture matched text
    LPAREN = auto()  # (
    RPAREN = auto()  # )

    # character classes -> matches any single character present insde bracket
    # gr[ae]y -> gray and grey
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    # [^aeiou] -> any single character that is not lowercase vowel
    CARET = auto()  # ^
    # [a-z] -> any lowercase english letter , [a-zA-Z0-9] -> any alphanum
    DASH = auto()  # -

    # special characters
    # wildcard -> it matches anything except \n
    # h.t -> hat, hot, h&t, hBt, ...
    DOT = auto()  # .
    # anchor -> current position is at the end of the string
    # world$ -> accept "hello world" but now "world hello"
    DOLLAR = auto()  # $
    # escape character
    # remove special meaning from symbols \\, \+, \.
    # it signals the start of a special sequence like \d
    BACKSLASH = auto()

    # special escape sequence
    DIGIT = auto()  # \d -> matches any digit
    NON_DIGIT = auto()  # \D -> matches any non-digit. [^0-9]
    WORD = (
        auto()  # \w -> any alpha numeric and _
    )
    NON_WORD = (
        auto()  # \W -> not word -> negative word
    )
    WHITESPACE = (
        auto()  # \s  [\t\n\r\f\v]
    )
    NON_WHITESPACE = (
        auto()  # \S
    )

    # word boundaru -> matches the position b/w word and non-word, also start/end of string
    # \bboy\b -> matches boy in "Hello boy here" but not in "Hello tomboy here"
    WORD_BOUNDARY = auto()  # \b
    NON_WORD_BOUNDARY = auto()  # \B

    # backreferences
    # matchs the exact text that was previously captured by capturing group
    # (\w)\1 matches any repeated character like 'oo' in 'look'
    BACKREF = auto()

    # Lookahead / Lookbehind markers
    LOOKAHEAD_POS = (
        # (?= -> Password(?=.*[0-9]) checks if the password contains atleast one digit afterward
        auto()
    )
    LOOKAHEAD_NEG = (
        auto()  # (?! -> not present afterward
    )
    LOOKBEHIND_POS = (
        auto()  # (?<=
    )
    LOOKBEHIND_NEG = (
        auto()  # (?<!
    )
    NON_CAPTURING = (
        auto()  # (?: -> (?:http|https) -> this cannot be captures by \1
    )

    EOF = auto()  # end of file


@dataclass
class Token:
    type: TokenType
    value: Optional[str] = None
    position: int = 0


class Lexer:
    # 1. Lookup table for simple, single-character tokens (O(1) lookup)
    SIMPLE_TOKENS: Dict[str, TokenType] = {
        "*": TokenType.STAR,
        "+": TokenType.PLUS,
        "?": TokenType.QUESTION,
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
        ",": TokenType.COMMA,
        "|": TokenType.PIPE,
        # '(' is handled separately in _handle_group_start
        ")": TokenType.RPAREN,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        "^": TokenType.CARET,
        "$": TokenType.DOLLAR,
        ".": TokenType.DOT,
        "-": TokenType.DASH,
    }

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0
        self.length = len(pattern)

    def current_char(self) -> Optional[str]:
        if self.pos < self.length:
            return self.pattern[self.pos]
        return None

    def advance(self) -> Optional[str]:
        char = self.current_char()
        self.pos += 1
        return char

    def tokenize(self) -> List[Token]:
        tokens = []

        while self.pos < self.length:
            start_pos = self.pos
            char = self.current_char()

            if char == "\\":
                token = self._handle_escape()
                if token:
                    tokens.append(token)
            elif char == "(":
                tokens.append(self._handle_group_start())
            elif char in self.SIMPLE_TOKENS:
                # Replaces the massive if/elif chain
                tokens.append(Token(self.SIMPLE_TOKENS[char], char, start_pos))
                self.advance()
            else:
                tokens.append(Token(TokenType.CHAR, char, start_pos))
                self.advance()

        tokens.append(Token(TokenType.EOF, None, self.pos))
        return tokens

    # Fixed return type to Token instead of Optional[str]
    def _handle_escape(self) -> Token:
        start_pos = self.pos
        self.advance()  # Consume the '\'

        next_char = self.current_char()
        if next_char is None:
            raise ValueError(
                f"Pattern cannot end with backslash at position {start_pos}")

        self.advance()  # Consume the escaped character once here, instead of in every if-branch

        # 2. Map for escape sequences
        escape_map = {
            "d": (TokenType.DIGIT, r"\d"),
            "D": (TokenType.NON_DIGIT, r"\D"),
            "w": (TokenType.WORD, r"\w"),
            "W": (TokenType.NON_WORD, r"\W"),
            "s": (TokenType.WHITESPACE, r"\s"),
            "S": (TokenType.NON_WHITESPACE, r"\S"),
            "b": (TokenType.WORD_BOUNDARY, r"\b"),
            "B": (TokenType.NON_WORD_BOUNDARY, r"\B"),
            "n": (TokenType.CHAR, "\n"),
            # Fixed r"\t" to "\t" so it actually parses as a tab
            "t": (TokenType.CHAR, "\t"),
            "r": (TokenType.CHAR, "\r"),
        }

        if next_char in escape_map:
            tok_type, val = escape_map[next_char]
            return Token(tok_type, val, start_pos)

        elif next_char.isdigit():
            num = next_char
            while self.current_char() and self.current_char().isdigit():
                num += self.advance()
            return Token(TokenType.BACKREF, num, start_pos)
        else:
            # Handles escaped literals like \* or \+
            return Token(TokenType.CHAR, next_char, start_pos)

    def _handle_group_start(self) -> Token:
        start_pos = self.pos
        self.advance()  # Consume '('

        if self.current_char() == "?":
            self.advance()  # Consume '?'
            next_char = self.current_char()

            if next_char == ":":
                self.advance()
                return Token(TokenType.NON_CAPTURING, "(?:", start_pos)
            elif next_char == "=":
                self.advance()
                return Token(TokenType.LOOKAHEAD_POS, "(?=", start_pos)
            elif next_char == "!":
                self.advance()
                return Token(TokenType.LOOKAHEAD_NEG, "(?!", start_pos)
            elif next_char == "<":
                self.advance()
                look_char = self.current_char()

                if look_char == "=":
                    self.advance()
                    return Token(TokenType.LOOKBEHIND_POS, "(?<=", start_pos)
                elif look_char == "!":
                    self.advance()
                    return Token(TokenType.LOOKBEHIND_NEG, "(?<!", start_pos)
                else:
                    raise ValueError(
                        f"Invalid group syntax at position {start_pos}")
            else:
                raise ValueError(
                    f"Unknown group modifier '?{next_char}' at position {start_pos}")

        return Token(TokenType.LPAREN, "(", start_pos)
