"""Pruebas del analizador léxico de Mini C.

Verifican todas las reglas y políticas de la especificación
'analizador-lexico-mini-c' (Los extraditables, grupo 1SF132).
"""

from minic.diagnostics.diagnostic import Diagnostic
from minic.lexer.lexer import Lexer
from minic.lexer.token import Token
from minic.lexer.token_type import TokenType
from minic.output.diagnostic_printer import format_diagnostic
from minic.output.token_printer import format_token


def test_keywords_and_identifiers() -> None:
    tokens, diagnostics = Lexer("int while int2 whilex _var x1_").scan()
    assert diagnostics == []

    expected_types = [
        TokenType.KW_INT,
        TokenType.KW_WHILE,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected_types
    assert [t.lexeme for t in tokens] == ["int", "while", "int2", "whilex", "_var", "x1_", ""]


def test_integer_literals() -> None:
    tokens, diagnostics = Lexer("0 007 42 1234567890").scan()
    assert diagnostics == []

    expected_literals = [0, 7, 42, 1234567890, None]
    assert [t.literal for t in tokens] == expected_literals
    assert [t.type for t in tokens[:-1]] == [TokenType.INTEGER_LITERAL] * 4


def test_all_operators_and_delimiters() -> None:
    source = "== != = + - ( ) { } ;"
    tokens, diagnostics = Lexer(source).scan()
    assert diagnostics == []

    expected = [
        (TokenType.EQUAL_EQUAL, "=="),
        (TokenType.NOT_EQUAL, "!="),
        (TokenType.ASSIGN, "="),
        (TokenType.PLUS, "+"),
        (TokenType.MINUS, "-"),
        (TokenType.LPAREN, "("),
        (TokenType.RPAREN, ")"),
        (TokenType.LBRACE, "{"),
        (TokenType.RBRACE, "}"),
        (TokenType.SEMICOLON, ";"),
        (TokenType.EOF, ""),
    ]
    assert [(t.type, t.lexeme) for t in tokens] == expected


def test_maximal_munch_double_vs_single_equal() -> None:
    tokens, diagnostics = Lexer("=== ==").scan()
    assert diagnostics == []

    # === se separa en == y =
    expected = [
        (TokenType.EQUAL_EQUAL, "=="),
        (TokenType.ASSIGN, "="),
        (TokenType.EQUAL_EQUAL, "=="),
        (TokenType.EOF, ""),
    ]
    assert [(t.type, t.lexeme) for t in tokens] == expected


def test_number_followed_by_letters() -> None:
    # Regla 5: 12abc -> 12 y abc
    tokens, diagnostics = Lexer("12abc").scan()
    assert diagnostics == []

    assert len(tokens) == 3
    assert tokens[0] == Token(TokenType.INTEGER_LITERAL, "12", 12, 1, 1)
    assert tokens[1] == Token(TokenType.IDENTIFIER, "abc", None, 1, 3)
    assert tokens[2] == Token(TokenType.EOF, "", None, 1, 6)


def test_minus_and_number() -> None:
    # Regla 6: -5 se separa en MINUS y INTEGER_LITERAL
    tokens, diagnostics = Lexer("-5").scan()
    assert diagnostics == []

    assert tokens[0] == Token(TokenType.MINUS, "-", None, 1, 1)
    assert tokens[1] == Token(TokenType.INTEGER_LITERAL, "5", 5, 1, 2)
    assert tokens[2] == Token(TokenType.EOF, "", None, 1, 3)


def test_whitespace_and_tab_positions() -> None:
    # Tab cuenta como 1 columna. Solo \n abre línea nueva. \r suelto es 1 columna.
    source = "int\tx\r=\n42;"
    tokens, diagnostics = Lexer(source).scan()
    assert diagnostics == []

    # int: 1:1, tab consume col 4, x: 1:5, \r consume col 6, =: 1:7, \n abre linea 2 col 1
    # 42: 2:1, ;: 2:3, EOF: 2:4
    assert tokens[0] == Token(TokenType.KW_INT, "int", None, 1, 1)
    assert tokens[1] == Token(TokenType.IDENTIFIER, "x", None, 1, 5)
    assert tokens[2] == Token(TokenType.ASSIGN, "=", None, 1, 7)
    assert tokens[3] == Token(TokenType.INTEGER_LITERAL, "42", 42, 2, 1)
    assert tokens[4] == Token(TokenType.SEMICOLON, ";", None, 2, 3)
    assert tokens[5] == Token(TokenType.EOF, "", None, 2, 4)


def test_section_7_case_1() -> None:
    source = "int2 = 12abc;\nwhilex == -5"
    tokens, diagnostics = Lexer(source).scan()

    assert diagnostics == []
    formatted = [format_token(t) for t in tokens]
    expected = [
        "IDENTIFIER 'int2' 1 1",
        "ASSIGN '=' 1 6",
        "INTEGER_LITERAL '12' 1 8",
        "IDENTIFIER 'abc' 1 10",
        "SEMICOLON ';' 1 13",
        "IDENTIFIER 'whilex' 2 1",
        "EQUAL_EQUAL '==' 2 8",
        "MINUS '-' 2 11",
        "INTEGER_LITERAL '5' 2 12",
        "EOF '' 2 13",
    ]
    assert formatted == expected


def test_section_7_case_2_with_errors() -> None:
    source = "int x = @;\nx ! = 0; // fin"
    tokens, diagnostics = Lexer(source).scan()

    formatted_tokens = [format_token(t) for t in tokens]
    expected_tokens = [
        "KW_INT 'int' 1 1",
        "IDENTIFIER 'x' 1 5",
        "ASSIGN '=' 1 7",
        "SEMICOLON ';' 1 10",
        "IDENTIFIER 'x' 2 1",
        "ASSIGN '=' 2 5",
        "INTEGER_LITERAL '0' 2 7",
        "SEMICOLON ';' 2 8",
        "IDENTIFIER 'fin' 2 13",
        "EOF '' 2 16",
    ]
    assert formatted_tokens == expected_tokens

    formatted_diags = [format_diagnostic(d) for d in diagnostics]
    expected_diags = [
        "LEX001 error 1:9 Carácter no reconocido: '@'",
        "LEX001 error 2:3 Carácter no reconocido: '!'",
        "LEX001 error 2:10 Carácter no reconocido: '/'",
        "LEX001 error 2:11 Carácter no reconocido: '/'",
    ]
    assert formatted_diags == expected_diags


def test_scan_always_reaches_eof_with_errors() -> None:
    # Regla 8 y Sección 9.2: scan() siempre llega al EOF y devuelve lista completa de tokens
    source = "@#$ 123"
    tokens, diagnostics = Lexer(source).scan()

    assert len(diagnostics) == 3
    assert tokens[0] == Token(TokenType.INTEGER_LITERAL, "123", 123, 1, 5)
    assert tokens[1] == Token(TokenType.EOF, "", None, 1, 8)
