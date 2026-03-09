# PyRegex: A Custom Backtracking Regex Engine

![Status](https://img.shields.io/badge/status-active_development-orange)
![Progress](https://img.shields.io/badge/progress-50%25-brightgreen)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Stability](https://img.shields.io/badge/stability-experimental-orange.svg)](#)

## Overview

PyRegex is a production-inspired Regular Expression engine implemented from the ground up in Python. While many academic implementations rely on Thompson’s NFA (Non-deterministic Finite Automaton) for linear-time matching, this project utilizes a **Backtracking Matcher** to support advanced features found in modern engines like Python's `re` module, including **capturing groups** and **back-references**.

This project serves as a deep dive into the phases of a compiler: Lexical Analysis, Syntactic Parsing, Abstract Syntax Tree (AST) construction, and Recursive Execution.

---

## System Architecture

The engine follows a modular pipeline, ensuring that the logic for tokenizing a pattern is completely decoupled from the logic used to match it against a string.

### 1. Lexical Analysis (The Lexer)

The Lexer performs a single pass over the regex string to generate a stream of high-level tokens. It handles:

- **Escaping Logic:** Identifying when a character (like `*`) should be treated as a literal.
- **Token Classification:** Categorizing metacharacters, quantifiers, and character classes.

### 2. Syntactic Parsing (Recursive Descent)

The Parser consumes the token stream to build a hierarchical **Abstract Syntax Tree (AST)**.

- **Grammar:** Implements an **LL(k) grammar** to handle operator precedence (e.g., ensuring `a|bc*` is parsed as `(a)|(b(c*))`).
- **Node Types:** Every regex feature is represented as a specific node (`GroupNode`, `AlternationNode`, `QuantifierNode`), making the engine highly extensible.

### 3. The Matcher Engine (Backtracking)

The engine executes the AST against the input string using a recursive backtracking algorithm. This allows the engine to "try" different paths (common in alternations and quantifiers) and revert its state if a match fails, facilitating complex features like back-referencing.

---

## Features

- **Character Classes:** Supports literals, ranges (`[a-z]`), and shorthand classes (`\d`, `\w`, `\s`).
- **Quantifiers:** Implementation of Greedy quantifiers: `*` (zero or more), `+` (one or more), `?` (zero or one), and `{n,m}` (range).
- **Alternation:** Supports the `|` operator for logical OR branching.
- **Grouping & Capturing:**
  - **Capturing Groups:** `(...)` for extracting sub-matches.
  - **Non-Capturing Groups:** `(?:...)` for grouping without overhead.
- **Back-references:** Ability to match the same text as previously matched by a capturing group (e.g., `\1`).
- **Standard API:** Includes `match()`, `search()`, and `findall()` functions.

---

## Engineering Analysis: NFA vs. Backtracking

In the design phase, a critical trade-off was evaluated regarding the matching algorithm:

| Criterion             | Thompson's NFA    | Backtracking (This Engine)        |
| :-------------------- | :---------------- | :-------------------------------- |
| **Search Complexity** | Linear $O(n)$     | Exponential $O(2^n)$ (Worst-case) |
| **Back-referencing**  | ❌ Impossible     | ✅ Supported                      |
| **Memory Overhead**   | High (State sets) | Low (Stack-based)                 |
| **Production Use**    | `grep`, `awk`     | `Python`, `Java`, `JavaScript`    |

**Conclusion:** Backtracking was chosen to maximize feature parity with modern programming languages, despite the potential for "Catastrophic Backtracking" on specifically crafted malicious patterns.

---

## Installation & Usage

### Prerequisites

- Python 3.10+

### Setup

```bash
# Clone the repository
git clone https://github.com/smaitra006/regex-engine.git
cd regex-engine
```

# Initialize virtual environment

```
python -m venv venv
source venv/bin/activate  # On Windows:
```
