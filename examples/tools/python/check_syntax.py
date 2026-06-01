"""Syntax checking tool."""

from __future__ import annotations

import ast

from omniagents_client.tools import tool


@tool
def check_syntax(code: str, filename: str = "<stdin>") -> str:
    """
    Check whether a Python code snippet has valid syntax.

    :param code: The Python source code to check.
    :param filename: Optional filename for error messages.
    :returns: 'OK' if valid, or the syntax error message.
    """
    try:
        ast.parse(code, filename=filename)
        return "OK"
    except SyntaxError as e:
        return f"SyntaxError at line {e.lineno}: {e.msg}"
