"""
Calculator Tool for Safe Mathematical Evaluation.
"""

import ast
import operator
from typing import Union

# Supported operators for safe AST evaluation
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def evaluate_math_expression(expression: str) -> Union[int, float]:
    """
    Safely evaluates a mathematical string expression using AST parsing.
    Prevents code execution vulnerabilities.
    """
    try:
        node = ast.parse(expression, mode='eval').body
    except SyntaxError as e:
        raise ValueError(f"Invalid mathematical expression syntax: '{expression}'") from e

    def _eval_node(n: ast.AST) -> Union[int, float]:
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        elif isinstance(n, ast.BinOp):
            left = _eval_node(n.left)
            right = _eval_node(n.right)
            op_type = type(n.op)
            if op_type in _SAFE_OPERATORS:
                if op_type == ast.Div and right == 0:
                    raise ZeroDivisionError("Division by zero in mathematical expression.")
                return _SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        elif isinstance(n, ast.UnaryOp):
            operand = _eval_node(n.operand)
            op_type = type(n.op)
            if op_type in _SAFE_OPERATORS:
                return _SAFE_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        else:
            raise ValueError(f"Unsupported syntax node: {type(n).__name__}")

    return _eval_node(node)
