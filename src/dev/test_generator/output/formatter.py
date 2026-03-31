"""
Post-processing for hypothesis-generated test code — pure domain layer.

Promoted from scripts/hypot_test_gen.py (TestFixer / fix_duplicate_self).
The only transformation we currently need: removing duplicate `self`
parameters that `hypothesis write` occasionally emits.
"""

import ast
from typing import Optional


class _DuplicateSelfFixer(ast.NodeTransformer):
    """AST transformer: remove duplicate `self` arguments from every function."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        seen_self = False
        new_args = []
        for arg in node.args.args:
            if arg.arg == "self":
                if not seen_self:
                    seen_self = True
                    new_args.append(arg)
                # else: drop the duplicate
            else:
                new_args.append(arg)
        node.args.args = new_args
        self.generic_visit(node)
        return node

    # async functions can have the same issue
    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]


def fix_generated_code(source: str) -> Optional[str]:
    """Apply all post-processing passes to *source* and return clean code.

    Returns None if the source cannot be parsed (i.e., is already broken).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    fixed_tree = _DuplicateSelfFixer().visit(tree)
    ast.fix_missing_locations(fixed_tree)
    return ast.unparse(fixed_tree)
