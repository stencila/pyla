"""
Handles parsing of CodeChunks to extract their properties and information about variables and functions used/defined.
"""
import ast
import logging
import traceback
import typing

from stencila.schema.types import (
    ArrayValidator,
    BooleanValidator,
    CodeChunk,
    CodeError,
    CodeExpression,
    Function,
    IntegerValidator,
    NumberValidator,
    Parameter,
    SoftwareSourceCode,
    StringValidator,
    TupleValidator,
    ValidatorTypes,
    Variable,
)

ImportsType = typing.List[typing.Union[str, SoftwareSourceCode]]
OptionalStringList = typing.Optional[typing.List[str]]

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

# pylint: disable=R0902
class CodeChunkParseResult:
    """
    The result of parsing a `CodeChunk`.
    """

    chunk_ast: typing.Optional[ast.Module]
    _imports: ImportsType
    _assigns: typing.List[str]
    _declares: typing.List[typing.Union[Function, Variable]]
    _alters: typing.List[str]
    _uses: typing.List[str]
    _reads: typing.List[str]
    error: typing.Optional[CodeError]

    # pylint: disable=R0913
    def __init__(
        self,
        chunk_ast: typing.Optional[ast.Module] = None,
        imports: typing.Optional[ImportsType] = None,
        assigns: OptionalStringList = None,
        declares: OptionalStringList = None,
        alters: OptionalStringList = None,
        uses: OptionalStringList = None,
        reads: OptionalStringList = None,
        error: typing.Optional[CodeError] = None,
    ):
        self.chunk_ast = chunk_ast
        self.imports = imports or []
        self.assigns = assigns or []
        self.declares = declares or []
        self.alters = alters or []
        self.uses = uses or []
        self.reads = reads or []
        self.error = error

    def combined_code_imports(
        self, existing_imports: typing.Optional[ImportsType]
    ) -> typing.Optional[ImportsType]:
        """
        Combine a list of existing imports (from a CodeChunk) with the parsed `imports`.

        `self.imports` will be combined with `existing_imports`, with duplicates removed, unless `existing_imports` has
        an empty string semaphore which indicates no new imports should be added.
        """
        if existing_imports is None or self.imports is None:
            return self.imports

        if "" in existing_imports:
            return existing_imports

        imports = list(existing_imports)  # copy the list

        for imp in self.imports:
            if imp not in imports:
                imports.append(imp)

        return imports

    @property
    def imports(self) -> typing.Optional[ImportsType]:
        """
        Get the `imports` list or `None` if the list is empty.
        """
        if not self._imports:
            return None

        return self._imports

    @imports.setter
    def imports(self, imports: ImportsType) -> None:
        self._imports = imports

    @property
    def assigns(self) -> OptionalStringList:
        """
        Get the `assigns` list or `None` if the list is empty.
        """
        if not self._assigns:
            return None
        return self._assigns

    @assigns.setter
    def assigns(self, assigns: typing.List[str]) -> None:
        self._assigns = assigns

    @property
    def declares(
        self,
    ) -> typing.Optional[typing.List[typing.Union[Function, Variable]]]:
        """
        Get the `declares` list or `None` if the list is empty.
        """
        if not self._declares:
            return None
        return self._declares

    @declares.setter
    def declares(self, declares: typing.List[typing.Union[Function, Variable]]) -> None:
        self._declares = declares

    @property
    def alters(self) -> OptionalStringList:
        """
        Get the `alters` list or `None` if the list is empty.
        """
        if not self._alters:
            return None
        return self._alters

    @alters.setter
    def alters(self, alters: typing.List[str]) -> None:
        self._alters = alters

    @property
    def uses(self) -> OptionalStringList:
        """
        Get the `uses` list or `None` if the list is empty.
        """
        if not self._uses:
            return None
        return self._uses

    @uses.setter
    def uses(self, uses: typing.List[str]) -> None:
        self._uses = uses

    @property
    def reads(self) -> OptionalStringList:
        """
        Get the `reads` list or `None` if the list is empty.
        """
        if not self._reads:
            return None
        return self._reads

    @reads.setter
    def reads(self, reads: typing.List[str]) -> None:
        self._reads = reads

    def to_dict(self):
        """
        Return all attributes as a dictionary.
        """
        return {
            "chunk_ast": self.chunk_ast,
            "imports": self.imports,
            "assigns": self.assigns,
            "declares": self.declares,
            "alters": self.alters,
            "uses": self.uses,
            "reads": self.reads,
            "error": self.error,
        }


class CodeChunkExecution(typing.NamedTuple):
    """
    Combination of a `CodeChunk` and its parse result.

    This is so the AST does not have to be parsed twice (once during parsing and again during execution).
    """

    code_chunk: CodeChunk
    parse_result: CodeChunkParseResult


def annotation_name_to_validator(
    name: typing.Optional[str],
) -> typing.Optional[ValidatorTypes]:
    """
    Parse a Python annotation string (basically a type name) and convert to a `Validator` type.
    """
    if name is None:
        return None

    return {
        "bool": BooleanValidator(),
        "str": StringValidator(),
        "int": IntegerValidator(),
        "float": NumberValidator(),
        "list": ArrayValidator(),
        "tuple": TupleValidator(),
    }.get(name)


def mode_is_read(mode: str) -> bool:
    """
    Determine if an open mode is a read. Opening a file with `w+` or `a+` allows read and write.
    """
    return "r" in mode or "+" in mode


def parse_open_filename(open_call: ast.Call) -> typing.Optional[str]:
    """
    Return the filename used in an `open` call (whether it's define positionally or with kwarg).

    If the filename is a variable, or the mode is not a read (or is a variable and thus can't be determined) then return
     `None`.
    """
    filename = None

    if hasattr(open_call, "args"):
        if len(open_call.args) >= 1:
            if not isinstance(open_call.args[0], ast.Str):
                return None
            filename = open_call.args[0].s

            if len(open_call.args) >= 2:
                if not isinstance(open_call.args[1], ast.Str):
                    return None

                if not mode_is_read(open_call.args[1].s):
                    return None

    if hasattr(open_call, "keywords"):
        for keyword in open_call.keywords:
            if not isinstance(keyword.value, ast.Str):
                continue

            if keyword.arg == "file":
                filename = keyword.value.s

            if keyword.arg == "mode":
                if not mode_is_read(keyword.value.s):
                    return None

    return filename


def exception_to_code_error(exception: Exception) -> CodeError:
    """
    Convert an `Exception` to a `CodeError` entity.
    """
    return CodeError(
        errorType=type(exception).__name__,
        errorMessage=str(exception),
        stackTrace=traceback.format_exc(),
    )


def set_code_error(
    code: typing.Union[CodeChunk, CodeExpression],
    error: typing.Union[Exception, CodeError],
) -> None:
    """
    Add the `CodeError` to a `CodeChunk` or `CodeExpression` `errors` list.

    If an `Exception` is passed then it is converted to a `CodeError`.
    """
    if code.errors is None:
        code.errors = []

    if isinstance(error, Exception):
        error = exception_to_code_error(error)

    code.errors.append(error)


def simple_code_chunk_parse(code: CodeChunk) -> CodeChunkExecution:
    """
    Build a CodeChunkExecution from CodeChunk.

    This is the most basic information that is needed to execute a CodeChunk in the interpreter.
    """
    parser = CodeChunkParser()
    cc_result = parser.parse(code)

    if cc_result.error:
        set_code_error(code, cc_result.error)

    return CodeChunkExecution(code, cc_result)


class CodeChunkParser:
    """
    Parse a `CodeChunk` by parsing its `text` into an AST and traversing it.
    """

    imports: typing.List[str]
    declares: typing.List[typing.Union[Variable, Function]]
    assigns: typing.List[str]
    alters: typing.List[str]
    uses: typing.List[str]
    reads: typing.List[str]

    seen_vars: typing.List[str]

    name_skip: typing.List[str] = []

    def reset(self) -> None:
        """Reset the storage lists."""
        self.imports = []
        self.declares = []
        self.assigns = []
        self.alters = []
        self.uses = []
        self.reads = []

        self.seen_vars = []

    def add_variable(self, name: str, type_annotation: typing.Optional[str]) -> None:
        """
        Store a variable declaration.

        Parses the `type_annotation` (if set) and transforms to a Validator subclass.
        """
        if name in self.seen_vars:
            return

        self.seen_vars.append(name)
        self.declares.append(
            Variable(name, validator=annotation_name_to_validator(type_annotation))
        )

    def add_name(self, name: str, target: typing.List) -> None:
        """
        Add a name to the target list, if it not already used.

        `target` should be one of the self properties (`imports`, `declares`, etc). `seen_vars` is the global record of
        any seen names to prevent duplicates (e.g. a variable would not be both declared [in `declares` list] and then
        used [in `uses` list]).
        """
        if (
            name in self.name_skip
        ):  # we can temporarily skip names we are not interested in (e.g. inside lambdas)
            return

        if name not in self.seen_vars and name not in target:
            self.seen_vars.append(name)
            target.append(name)

    def add_alters(self, name: str) -> None:
        """
        A special function for adding an `alters` name instead of using the general `add_name` function above.

        The difference is that if a name is added here and is already in `uses`, then it is removed from `uses` and
        added to `alters` as this is a more accurate definition.
        """
        if name in self.alters:
            return

        if name in self.seen_vars:
            if name not in self.uses:
                return

            self.uses.remove(name)
            # var has been seen, but only in `uses`, a more accurate description is `alters` so
            # move it there

        self.seen_vars.append(name)
        self.alters.append(name)

    def parse(self, chunk: CodeChunk) -> CodeChunkParseResult:
        """
        Main entry function for this class, parses a CodeChunk's properties into a CodeChunkParseResult.
        """
        self.reset()

        try:
            chunk_ast = ast.parse(chunk.text)
        except SyntaxError as exc:  # This should be either SyntaxError or IndentationError (which is a subclass)
            return CodeChunkParseResult(None, error=exception_to_code_error(exc))

        # If this is True, then there should be a call to 'open' somewhere in the code, which
        # means the parser should try to find it. This is a basic check so there might not be
        # one (like if the code did , but if 'open(' is NOT in the string then there definitely
        # ISN'T one
        search_for_open = "open(" in chunk.text

        for statement in chunk_ast.body:
            self.parse_statement(statement)

        if search_for_open:
            self._parse_file_reads(chunk_ast)

        return CodeChunkParseResult(
            chunk_ast,
            self.imports,
            self.assigns,
            self.declares,
            self.alters,
            self.uses,
            self.reads,
        )

    # pylint: disable=R0912,R0915 # Too many branches/statements warning but this is kind of a special case
    def parse_statement(
        self,
        statement: typing.Union[
            ast.stmt,
            ast.expr,
            typing.Sequence[typing.Union[ast.stmt, ast.expr, ast.comprehension]],
        ],
    ) -> None:
        """
        General statement parser that delegates to parsers for specific parser types.
        """
        if isinstance(statement, list):
            for sub_statement in statement:
                self.parse_statement(sub_statement)
        elif isinstance(statement, (ast.ImportFrom, ast.Import)):
            self._parse_import(statement)
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            self._parse_assigns(statement)
        elif isinstance(statement, ast.BinOp):
            self._parse_bin_op(statement)
        elif isinstance(statement, ast.BoolOp):
            self._parse_bool_op(statement)
        elif isinstance(statement, ast.Attribute):
            self._parse_attribute(statement)
        elif isinstance(statement, ast.Subscript):
            self._parse_subscript(statement, False)
        elif isinstance(statement, ast.Call):
            self._parse_call(statement)
        elif isinstance(statement, ast.FunctionDef):
            self._parse_function_def(statement)
        elif isinstance(statement, ast.Dict):
            self._parse_dict(statement)
        elif isinstance(statement, (ast.List, ast.Tuple)):
            self.parse_statement(statement.elts)
        elif isinstance(statement, ast.Name):
            self.add_name(statement.id, self.uses)
        elif isinstance(statement, ast.Expr):
            self.parse_statement(statement.value)
        elif isinstance(statement, ast.AugAssign):
            self._parse_aug_assign(statement)
        elif isinstance(statement, (ast.If, ast.While)):
            self._parse_if_while(statement)
        elif isinstance(statement, ast.Compare):
            self._parse_compare(statement)
        elif isinstance(statement, ast.For):
            self._parse_for(statement)
        elif isinstance(statement, ast.Try):
            self._parse_try(statement)
        elif isinstance(statement, ast.ExceptHandler):
            self._parse_except_handler(statement)
        elif isinstance(statement, ast.With):
            self._parse_with(statement)
        elif isinstance(statement, (ast.ListComp, ast.SetComp)):
            self._parse_list_or_set_comprehension(statement)
        elif isinstance(statement, ast.DictComp):
            self._parse_dict_comprehension(statement)
        elif isinstance(statement, ast.comprehension):
            self._parse_comprehension(statement)
        elif isinstance(statement, ast.Lambda):
            self._parse_lambda(statement)
        elif isinstance(statement, ast.UnaryOp):
            self._parse_unary_op(statement)
        elif isinstance(
            statement,
            (
                ast.ClassDef,
                ast.Num,
                ast.Str,
                ast.Pass,
                ast.NameConstant,
                ast.Bytes,
                ast.Break,
                ast.Continue,
            ),
        ):
            pass
        else:
            LOGGER.warning("Unrecognized statement %s", statement)

    def _parse_import(
        self, statement: typing.Union[ast.ImportFrom, ast.Import]
    ) -> None:
        """
        Parse 'import ...' or 'from ... import ...' statements.

        Adds the modules that are being imported from to the `imports` list.
        """
        if isinstance(statement, ast.ImportFrom):
            modules = [statement.module]
        else:
            modules = [name.name for name in statement.names]

        for module in modules:
            if module is not None and module not in self.imports:
                self.imports.append(module)

    def _parse_reference(
        self, ref: typing.Optional[typing.Union[ast.stmt, ast.expr, ast.slice]]
    ) -> typing.Optional[str]:
        """
        Attempts to get the final name of a reference (usually an `Index` used in a subscript).

        For example, `a[b:c:d]` -> `b`, `c`, `d`.
        """
        if isinstance(ref, ast.Name):
            return ref.id

        if not isinstance(ref, ast.Subscript) and hasattr(ref, "value"):
            # for some reason isinstance (ref, ast.Index) doesn't work, so the hasattr check is a
            # workaround to check for an ast.Index object
            return self._parse_reference(ref.value)  # type: ignore

        return None

    def _parse_assigns(
        self, statement: typing.Union[ast.Assign, ast.AnnAssign]
    ) -> None:
        """
        Parse an assigment and try to choose the best place to store it.

        If the assignment has a type annotation, treat that as a variable declaration (name into `declares`).
        If the  assignment is to an object (e.g. `x.y = z`) or list (e.g. `x[y] = z` treat that as an alters
        (`x` into `alters`).
        Otherwise, put the name into the `assigns` list. Also parse the right side of the expression to find other
        variables that are used.
        """
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            raise TypeError("{} has no target or targets".format(statement))

        for target in targets:
            if isinstance(target, ast.Attribute):
                self.add_alters(self._recurse_attribute(target))
                continue

            if isinstance(target, ast.Subscript):
                subscript_name = self._parse_subscript(target, True)
                if subscript_name is not None:
                    self.add_alters(subscript_name)
                continue

            if isinstance(target, ast.Name):
                if isinstance(statement, ast.AnnAssign):
                    annotation_name = (
                        statement.annotation.id
                        if isinstance(statement.annotation, ast.Name)
                        else None
                    )
                    self.add_variable(target.id, annotation_name)
                else:
                    self.add_name(target.id, self.assigns)

        statement_value = getattr(statement, "value", None)
        if statement_value is not None:
            self.parse_statement(statement_value)

    def _recurse_attribute(self, ref: typing.Union[ast.stmt, ast.expr]) -> str:
        """
        Recurse through an attribute to get the actual variable (e.g. `x.y.z` -> `x`).
        """
        if hasattr(ref, "value"):
            if isinstance(ref.value, ast.Attribute):  # type: ignore
                return self._recurse_attribute(ref.value)  # type: ignore

            if isinstance(ref.value, ast.Name):  # type: ignore
                return ref.value.id  # type: ignore

        raise TypeError("Can't get name of {}".format(ref))

    def _parse_attribute(self, statement: ast.Attribute) -> None:
        """
        Parse a standalone attribute and add it to the `uses` list.

        This will be in cases like list or dict literals, or function calls.
        Some examples:
        `a = [b.c]` -> `b` into `uses`.
        `a = {c.d: e.f}` -> `c` and `e` into `uses`.
        `call_func(a.b, c.d)` -> `a` and `c` into `uses`.
        """
        self.add_name(self._recurse_attribute(statement), self.uses)

    def _parse_subscript(
        self, statement: ast.Subscript, in_assign: bool
    ) -> typing.Optional[str]:
        """
        Parse a subscript (list access).

        Handles single element access (`a[b]`) and slices (`a[b:c:d]`).
        """
        if isinstance(statement.slice, ast.Slice):
            for ref_name in ("lower", "step", "upper"):
                ref = getattr(statement.slice, ref_name, None)
                name = self._parse_reference(ref)
                if name is not None:
                    self.add_name(name, self.uses)
                if ref is not None:
                    self.parse_statement(ref)
        else:
            slice_name = self._parse_reference(statement.slice)
            if slice_name is not None:
                self.add_name(slice_name, self.uses)

        value_ref = self._parse_reference(statement.value)
        if value_ref is not None:
            if not in_assign:
                self.add_name(value_ref, self.uses)
            return value_ref

        if isinstance(statement, ast.Subscript) and isinstance(
            statement.value, ast.Subscript
        ):
            return self._parse_subscript(statement.value, in_assign)

        self.parse_statement(statement.value)
        return None

    def _parse_bin_op(self, statement: ast.BinOp) -> None:
        """
        Parse a binary operation, e.g `a + b`, `c - d`.
        """
        self.parse_statement(statement.left)
        self.parse_statement(statement.right)

    def _parse_bool_op(self, statement: ast.BoolOp) -> None:
        """
        Parse a boolean operation, e.g. `a or b`, `d or e`.
        """
        self.parse_statement(statement.values)

    def _parse_call(self, statement: ast.Call) -> None:
        """
        Parse a function call to extract the variables used.
        """
        if hasattr(statement, "args"):
            self.parse_statement(statement.args)

        if hasattr(statement, "keywords"):
            for keyword in statement.keywords:
                self.parse_statement(keyword.value)

    def _parse_function_def(self, statement: ast.FunctionDef) -> None:
        """
        Parse a function definition to extract the `Parameter`s it accepts.
        """
        if statement.name in self.seen_vars:
            return

        return_ann = (
            statement.returns.id if isinstance(statement.returns, ast.Name) else None
        )

        func = Function(
            name=statement.name,
            returns=annotation_name_to_validator(return_ann),
            parameters=[],
        )

        for i, arg in enumerate(statement.args.args):
            param = Parameter(arg.arg)

            if arg.annotation and hasattr(arg.annotation, "id"):
                param.validator = annotation_name_to_validator(arg.annotation.id)  # type: ignore

            default_index = len(statement.args.defaults) - len(statement.args.args) + i
            # Only the last len(statement.args.defaults) can have defaults (since they must come after non-default
            # parameters)
            if default_index >= 0:
                default = statement.args.defaults[default_index]

                if isinstance(default, ast.Num):
                    param.default = default.n
                elif isinstance(default, ast.Str):
                    param.default = default.s
                elif isinstance(default, ast.NameConstant):
                    # default of None/True/False
                    param.default = default.value
                else:
                    self.parse_statement(default)
                param.isRequired = False
            else:
                param.isRequired = True

            func.parameters.append(param)

        if statement.args.vararg:
            func.parameters.append(
                Parameter(
                    name=statement.args.vararg.arg, isRequired=False, isVariadic=True
                )
            )

        if statement.args.kwarg:
            func.parameters.append(
                Parameter(
                    name=statement.args.kwarg.arg, isRequired=False, isExtensible=True
                )
            )

        self.seen_vars.append(func.name)
        self.declares.append(func)

    def _parse_dict(self, statement: ast.Dict) -> None:
        """
        Parse a dictionary definition, adding any variables it uses as keys or values
        to `uses`.
        """
        for key in statement.keys:
            if isinstance(key, ast.Name):
                self.add_name(key.id, self.uses)
            elif key:
                self.parse_statement(key)
        for value in statement.values:
            if isinstance(value, ast.Name):
                self.add_name(value.id, self.uses)
            else:
                self.parse_statement(value)

    def _parse_aug_assign(self, statement: ast.AugAssign) -> None:
        """
        Parse an augmented assignment (e.g. a += 1).

        Adds the variable being altered to the `alters` list.
        """
        if isinstance(statement.target, ast.Name):
            self.add_alters(statement.target.id)
        elif isinstance(statement.target, ast.Attribute):
            self.add_alters(self._recurse_attribute(statement.target))
        elif isinstance(statement.target, ast.Subscript):
            target_name = self._parse_subscript(statement.target, True)
            if target_name:
                self.add_alters(target_name)

        self.parse_statement(statement.value)

    def _parse_if_while(self, statement: typing.Union[ast.If, ast.While]) -> None:
        """
        Parse the test (condition), body, and `elif`/`else` statements of an `if` or `while`.
        """
        self.parse_statement(statement.test)
        self.parse_statement(statement.body)
        self.parse_statement(statement.orelse)

    def _parse_compare(self, statement: ast.Compare) -> None:
        """
        Parse a comparison statement (e.g. a > b, c < d, etc) and add the variables it uses to the `uses` list.
        """
        self.parse_statement(statement.left)
        self.parse_statement(statement.comparators)

    def _parse_for(self, statement: ast.For) -> None:
        """
        Parse a `for ...:` statement.

        Since the variable being assigned in iteration is available after the loop, it is added to the `assigns` list.
        """
        if isinstance(statement.target, ast.Name):
            self.add_name(statement.target.id, self.assigns)
        self.parse_statement(statement.iter)
        self.parse_statement(statement.body)
        self.parse_statement(statement.orelse)

    def _parse_try(self, statement: ast.Try) -> None:
        """
        Parse a `try`/`except`/`finally`/`else` statement.
        """
        self.parse_statement(statement.handlers)  # type: ignore  # Doesn't seem to understand List[ExceptHandler]
        # is valid
        self.parse_statement(statement.body)
        self.parse_statement(statement.finalbody)
        self.parse_statement(statement.orelse)

    def _parse_except_handler(self, statement: ast.ExceptHandler) -> None:
        """
        Parse an `except` handler (i.e. parse the statements in its `body`).
        """
        self.parse_statement(statement.body)

    def _parse_with(self, statement: ast.With) -> None:
        """
        Parse a `with` statement (i.e. parse the statements in its `body`).
        """
        self.parse_statement(statement.body)

    def _parse_list_or_set_comprehension(
        self, statement: typing.Union[ast.ListComp, ast.SetComp]
    ) -> None:
        """
        Parse a list or set comprehension (they have the same interface).
        """
        if not isinstance(statement.elt, ast.Name):
            # skip simple name assigns since they aren't really usable after the loop
            self.parse_statement(statement.elt)
        self.parse_statement(statement.generators)

    def _parse_dict_comprehension(self, statement: ast.DictComp) -> None:
        """
        Parse a dict comprehension.
        """
        self.parse_statement(statement.generators)
        self.parse_statement(statement.value)

    def _parse_comprehension(self, statement: ast.comprehension) -> None:
        """
        Parse a generator such as used in a comprehension.
        """
        target = statement.target

        if hasattr(target, "elts"):
            self.name_skip = [name.id for name in target.elts]  # type: ignore
        elif hasattr(target, "id"):
            self.name_skip = [target.id]  # type: ignore

        self.parse_statement(statement.iter)
        self.parse_statement(statement.ifs)

        self.name_skip = []

    def _parse_lambda(self, statement: ast.Lambda) -> None:
        # add the arguments to the name_skip so that they won't be added to 'uses' in the body parse
        self.name_skip = [
            arg.arg for arg in statement.args.args
        ]  # I feel like a pirate

        self.parse_statement(statement.body)

        self.name_skip = []

    def _parse_unary_op(self, statement: ast.UnaryOp) -> None:
        self.parse_statement(statement.operand)

    def _parse_file_reads(self, chunk_ast: ast.Module) -> None:
        """
        Walk the ast (including into function defs) and look for `open` function calls.

        Add any file reads (any `open` calls that aren't exclusively writes) to the `reads` list.
        """
        for node in ast.walk(chunk_ast):
            if (
                isinstance(node, ast.Call)
                and isinstance(getattr(node, "func", None), ast.Name)
                and node.func.id == "open"  # type: ignore
            ):
                filename = parse_open_filename(node)

                if filename and filename not in self.reads:
                    self.reads.append(filename)
