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
        """
        Remove duplicate 'self' parameters from a function definition, keeping only the first occurrence.
        
        Parameters:
            node (ast.FunctionDef): The function definition AST node to process; its arguments are modified in place and child nodes are visited.
        
        Returns:
            ast.FunctionDef: The same `node` after duplicate `'self'` parameters have been removed.
        """
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
    """
    Apply domain-layer post-processing to Python source to remove duplicate `self` parameters emitted by generators.
    
    Parameters:
        source (str): Python source code to process.
    
    Returns:
        Optional[str]: Transformed source code with duplicate `self` parameters removed, or `None` if the input cannot be parsed due to a syntax error.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    fixed_tree = _DuplicateSelfFixer().visit(tree)
    ast.fix_missing_locations(fixed_tree)
    return ast.unparse(fixed_tree)
