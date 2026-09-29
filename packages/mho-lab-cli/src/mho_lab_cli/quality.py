"""Bounded AST policy checks for the new typed Python workspace.

This complements Ruff and mypy; it does not infer runtime types. Import and
simple assignment aliases are resolved conservatively within each file. Runtime
strings are data, while forward annotations and type comments are checked.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, order=True)
class PolicyViolation:
    path: Path
    line: int
    reason: str


_TYPING_MODULES = frozenset({"typing", "typing_extensions"})
_CONTAINER_NAMES = frozenset(
    {
        "list",
        "dict",
        "set",
        "frozenset",
        "tuple",
        "List",
        "Dict",
        "Set",
        "FrozenSet",
        "Tuple",
        "Mapping",
        "MutableMapping",
        "Sequence",
        "MutableSequence",
        "Collection",
        "Iterable",
        "Iterator",
        "Generator",
        "AsyncIterable",
        "AsyncIterator",
        "AsyncGenerator",
        "AbstractSet",
        "MutableSet",
        "Deque",
        "DefaultDict",
        "Counter",
        "ChainMap",
        "deque",
        "defaultdict",
    }
)
_BUILTIN_CONTAINERS = frozenset({"list", "dict", "set", "frozenset", "tuple"})
_CONTAINER_MODULES = _TYPING_MODULES | {"collections", "collections.abc", "builtins"}
_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore\b(?!\s*\[[^\]\s]+(?:[^\]]*)\])", re.I)
_NOQA = re.compile(r"#\s*(?:(?:ruff|flake8)\s*:\s*)?noqa\b(?!\s*:\s*[A-Z]+\d+)", re.I)
_MYPY_IGNORE = re.compile(
    r"#\s*mypy:\s*(?:[^,]+,\s*)*ignore[-_]errors"
    r"(?:\s*=\s*(?:true|yes|1))?\s*(?:,|$)",
    re.I,
)


def _line(node: ast.AST) -> int:
    value: object = getattr(node, "lineno", 0)
    return value if isinstance(value, int) else 0


def _reference(node: ast.AST, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return bindings.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _reference(node.value, bindings)
        return None if parent is None else parent + "." + node.attr
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        parent = _reference(node.args[0], bindings)
        return None if parent is None else parent + "." + node.args[1].value
    return None


def _bindings(tree: ast.Module) -> dict[str, str]:
    bindings: dict[str, str] = {}
    assignments: list[ast.Assign | ast.AnnAssign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bindings[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                bindings[alias.asname or alias.name] = node.module + "." + alias.name
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            assignments.append(node)
    # A bounded fixed point also catches a forward reference through simple aliases.
    for _ in range(len(assignments) + 1):
        changed = False
        for assignment in assignments:
            if assignment.value is None:
                continue
            value = _reference(assignment.value, bindings)
            if value is None:
                continue
            targets = (
                assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            )
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and value != target.id
                    and bindings.get(target.id) != value
                ):
                    bindings[target.id] = value
                    changed = True
        if not changed:
            break
    return bindings


def _is_container(reference: str | None) -> bool:
    if reference in _BUILTIN_CONTAINERS:
        return True
    if reference is None or "." not in reference:
        return False
    module, _, name = reference.rpartition(".")
    return module in _CONTAINER_MODULES and name in _CONTAINER_NAMES


def _is_tuple(reference: str | None) -> bool:
    return reference in {"tuple", "builtins.tuple", "typing.Tuple", "typing_extensions.Tuple"}


def _annotation_aliases(tree: ast.Module) -> dict[str, ast.expr]:
    aliases: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.TypeAlias):
            aliases[node.name.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                aliases[node.target.id] = node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = node.value
    return aliases


def _homogeneous_tuple(
    node: ast.AST | None,
    bindings: dict[str, str],
    aliases: dict[str, ast.expr],
    seen: frozenset[str] = frozenset(),
) -> bool:
    if isinstance(node, ast.Name) and node.id in aliases:
        if node.id in seen:
            return False
        return _homogeneous_tuple(aliases[node.id], bindings, aliases, seen | {node.id})
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return _homogeneous_tuple(
                ast.parse(node.value, mode="eval").body, bindings, aliases, seen
            )
        except SyntaxError:
            return False
    return (
        isinstance(node, ast.Subscript)
        and _is_tuple(_reference(node.value, bindings))
        and isinstance(node.slice, ast.Tuple)
        and len(node.slice.elts) == 2
        and isinstance(node.slice.elts[1], ast.Constant)
        and node.slice.elts[1].value is Ellipsis
    )


class _PolicyVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, tree: ast.Module) -> None:
        self.path = path
        self.bindings = _bindings(tree)
        self.aliases = _annotation_aliases(tree)
        self.violations: set[PolicyViolation] = set()
        self.homogeneous_returns: list[bool] = []

    def report(self, node: ast.AST, reason: str, line: int | None = None) -> None:
        self.violations.add(
            PolicyViolation(self.path, line if line is not None else _line(node), reason)
        )

    def check_reference(self, node: ast.AST, line: int | None = None) -> None:
        reference = _reference(node, self.bindings)
        if reference is not None:
            self.check_resolved_reference(reference, node, line)

    def check_resolved_reference(
        self, reference: str, node: ast.AST, line: int | None = None
    ) -> None:
        if reference == "Any" or reference in {m + ".Any" for m in _TYPING_MODULES}:
            self.report(node, "Use an explicit type instead of Any (including aliases).", line)
        if reference in {m + "." + n for m in _TYPING_MODULES for n in ("Dict", "Tuple")}:
            self.report(node, "Use built-in generic syntax instead of typing.Dict/Tuple.", line)
        if reference in {m + ".cast" for m in _TYPING_MODULES}:
            self.report(node, "typing.cast is prohibited; validate or narrow the value.", line)
        if reference in {
            "typing.NamedTuple",
            "typing_extensions.NamedTuple",
            "collections.namedtuple",
        }:
            self.report(node, "Use a named dataclass or model instead of a tuple record.", line)

    def check_annotation(self, node: ast.AST, line: int | None = None) -> None:
        line = _line(node) if line is None else line
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                annotation = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                self.report(node, "Forward annotation could not be parsed.", line)
                return
            self.check_annotation(annotation, line)
            return
        if isinstance(node, ast.Subscript):
            self.check_reference(node.value, line)
            reference = _reference(node.value, self.bindings)
            if _is_tuple(reference) and not _homogeneous_tuple(node, self.bindings, self.aliases):
                self.report(
                    node, "Fixed tuple annotations are positional records; use a model.", line
                )
            if reference in {m + ".Literal" for m in _TYPING_MODULES}:
                return  # Literal string values are data, not forward annotations.
            if reference in {m + ".Annotated" for m in _TYPING_MODULES}:
                if isinstance(node.slice, ast.Tuple) and node.slice.elts:
                    self.check_annotation(node.slice.elts[0], line)
                return  # Remaining elements are metadata.
            self.check_annotation(node.slice, line)
            return
        self.check_reference(node, line)
        if isinstance(node, ast.Name | ast.Attribute) and _is_container(
            _reference(node, self.bindings)
        ):
            self.report(node, "Container annotations must include their element types.", line)
        for child in ast.iter_child_nodes(node):
            self.check_annotation(child, line)

    def check_type_comment(self, node: ast.AST, text: str | None) -> None:
        if text is None:
            return
        mode = "func_type" if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else "eval"
        try:
            parsed = ast.parse(text, mode=mode)
        except SyntaxError:
            self.report(node, "Type comment could not be parsed.")
            return
        for child in ast.iter_child_nodes(parsed):
            self.check_annotation(child, _line(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        for alias in node.names:
            if alias.name == "*" and node.module in _TYPING_MODULES:
                self.report(node, "Wildcard typing imports obscure the type policy.")
            self.check_resolved_reference(node.module + "." + alias.name, node)

    def visit_Name(self, node: ast.Name) -> None:
        self.check_reference(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.check_reference(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.check_reference(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.check_annotation(node.annotation)
        if node.value is not None and _reference(node.annotation, self.bindings) in {
            "typing.TypeAlias",
            "typing_extensions.TypeAlias",
        }:
            self.check_annotation(node.value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.check_type_comment(node, node.type_comment)
        if isinstance(node.value, ast.Subscript) and _is_container(
            _reference(node.value.value, self.bindings)
        ):
            self.check_annotation(node.value)
        self.generic_visit(node)

    def visit_TypeAlias(self, node: ast.TypeAlias) -> None:
        self.check_annotation(node.value)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if node.annotation is not None:
            self.check_annotation(node.annotation)
        self.check_type_comment(node, node.type_comment)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.check_function(node)

    def check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.returns is not None:
            self.check_annotation(node.returns)
        self.check_type_comment(node, node.type_comment)
        self.homogeneous_returns.append(
            _homogeneous_tuple(node.returns, self.bindings, self.aliases)
        )
        self.generic_visit(node)
        self.homogeneous_returns.pop()

    def visit_Return(self, node: ast.Return) -> None:
        if (
            isinstance(node.value, ast.Tuple)
            and node.value.elts
            and not (self.homogeneous_returns and self.homogeneous_returns[-1])
        ):
            self.report(
                node, "Tuple return records require a named model or homogeneous tuple type."
            )
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        if isinstance(node.body, ast.Tuple) and node.body.elts:
            self.report(node, "Lambda tuple records require a named model.")
        self.generic_visit(node)


def _check_file(path: Path) -> list[PolicyViolation]:
    try:
        with tokenize.open(path) as stream:
            source = stream.read()
        tree = ast.parse(source, filename=str(path), type_comments=True)
    except (OSError, UnicodeError, SyntaxError) as error:
        line = error.lineno or 1 if isinstance(error, SyntaxError) else 0
        return [PolicyViolation(path, line, "Cannot parse source: " + str(error))]
    visitor = _PolicyVisitor(path, tree)
    visitor.visit(tree)
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and (
            _TYPE_IGNORE.search(token.string)
            or _NOQA.search(token.string)
            or _MYPY_IGNORE.search(token.string)
        ):
            visitor.violations.add(
                PolicyViolation(path, token.start[0], "Blanket type-ignore/noqa is prohibited.")
            )
    return sorted(visitor.violations)


def check_paths(paths: list[Path]) -> list[PolicyViolation]:
    """Check explicit Python files or directories; never modify their contents."""
    files: set[Path] = set()
    violations: list[PolicyViolation] = []
    for path in paths:
        if path.is_dir():
            files.update(
                p for p in path.rglob("*.py") if not {".venv", "__pycache__"}.intersection(p.parts)
            )
        elif path.is_file():
            files.add(path)
        else:
            violations.append(PolicyViolation(path, 0, "Requested path does not exist."))
    for path in sorted(files):
        violations.extend(_check_file(path))
    return sorted(violations)
