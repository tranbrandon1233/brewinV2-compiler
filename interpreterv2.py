from env_v1 import EnvironmentManager
from type_valuev1 import Type, Value, create_value, get_printable
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    FALSE_VALUE = create_value(InterpreterBase.FALSE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "<", "<=", ">", ">=", "!=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()
        self.overloadCount = 2
        self.argNames = []

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        main_func = self.__get_func_by_name("main")
        self.env = EnvironmentManager()
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            if func_def.get("name") not in self.func_name_to_ast:
                self.func_name_to_ast[func_def.get("name")] = func_def
            else:  # Handle overloaded funcs
                self.func_name_to_ast[
                    func_def.get("name") + str(self.overloadCount)
                ] = func_def
                self.overloadCount += 1

    def __get_func_by_name(self, name):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.func_name_to_ast[name]

    def __run_statements(self, statements):
        # all statements of a function are held in arg3 of the function AST node
        for statement in statements:
            if self.trace_output:
                print(statement)
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.IF_DEF:
                ifVal = self.__eval_expr(statement.dict["condition"])
                if (
                    ifVal.type() != Type.BOOL
                    and ifVal.value() != True
                    and ifVal.value() != False
                ):
                    super().error(
                        ErrorType.TYPE_ERROR, f"Invalid conditional statement"
                    )
                if ifVal.value():
                    return self.__run_statements(statement.dict["statements"])
                else:
                    return self.__run_statements(statement.dict["else_statements"])

            elif statement.elem_type == InterpreterBase.WHILE_DEF:
                while self.__eval_expr(statement.dict["condition"]).value():
                    return self.__run_statements(statement.dict["statements"])
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                if statement.dict["expression"] == Interpreter.NIL_VALUE:
                    return None
                else:
                    return self.__eval_expr(statement.dict["expression"])

        return Interpreter.NIL_VALUE

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        else:
            return self.__call_new_func(call_node)

        # add code here later to call other functions
        super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.dict["args"]:
            result = self.__eval_expr(arg)  # result is a Value object
            if not isinstance(result, str):
                output = output + get_printable(result)
            else:
                output = output + result
        if output is "nil":
            super().error(ErrorType.NAME_ERROR, "Variable does not exist.")
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_new_func(self, call_ast):
        func = self.__get_func_by_name(call_ast.dict["name"])

        for i, arg in enumerate(call_ast.dict["args"]):
            self.env.set(
                func.dict["args"][i].dict["name"], self.__eval_expr(arg)
            )  # result is a Value
            self.argNames.append(func.dict["args"][i].dict["name"])
        for j in range(2, self.overloadCount):  # Repeat for overloaded funcs
            func = self.__get_func_by_name(call_ast.dict["name"] + str(j))
            for i, arg in enumerate(call_ast.dict["args"]):
                self.env.set(func.dict["args"][i].dict["name"], self.__eval_expr(arg))
                self.argNames.append(func.dict["args"][i].dict["name"])
        self.__run_statements(func.dict["statements"])
        for arg in self.argNames:
            self.env.set(
                arg, InterpreterBase.NIL_DEF
            )  # result is a Value object a Value object

        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = []
        for arg in call_ast.dict["args"]:
            args.append(arg)
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        # we can support inputs here later

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.dict["expression"])
        self.argNames.append(var_name)
        self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)

    def __eval_op(self, arith_ast):
        if arith_ast.elem_type == "neg":
            try:
                obj = self.__eval_expr(arith_ast.get("op1"))
                return Value(obj.type(), -obj.value())
            except:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible type for operation",
                )
        elif arith_ast.elem_type == "!":
            try:
                obj = self.__eval_expr(arith_ast.get("op1"))
                return Value(obj.type(), not obj.value())
            except:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for operation",
                )
        else:
            left_value_obj = self.__eval_expr(arith_ast.get("op1"))
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            if (
                left_value_obj == None
                or right_value_obj == None
                or left_value_obj.type() is "nil"
                or right_value_obj.type() is "nil"
                or left_value_obj.type() != right_value_obj.type()
            ):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for operation",
                )
            if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible operator.",
                )
            f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        result = f(left_value_obj, right_value_obj)
        if result == None:
            super().error(ErrorType.TYPE_ERROR, f"Invalid comparison")

        return f(left_value_obj, right_value_obj)

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            x.type(), x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            x.type(), x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            x.type(), x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            x.type(), x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            x.type(), x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            x.type(), x.value() >= y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            x.type(), x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            x.type(), x.value() != y.value()
        )
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            x.type(), x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            x.type(), x.value() != y.value()
        )
