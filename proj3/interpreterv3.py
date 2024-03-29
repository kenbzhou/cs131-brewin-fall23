import copy
from enum import Enum

from brewparse import parse_program
from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import Type, Value, create_value, get_printable

TRACE_OUTPUT = False

class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=TRACE_OUTPUT):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.lambda_functions = []
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        main_func = self.__get_func_by_name("main", 0)
        self.__run_statements(main_func.get("statements"))

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            if self.trace_output:
                print(func_def)
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        # If function is stored in a variable
        func_by_var = self.env.get(name)
        if func_by_var:
            if func_by_var.type() == Type.FUNC:
                return func_by_var.value()
            else:
                super().error(ErrorType.TYPE_ERROR, f"Function referenced through var '{name}' not a function")

        # If function is defined by the AST
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status = ExecStatus.CONTINUE
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                self.__call_func(statement)
            elif statement.elem_type == "=":
                self.__assign(statement)
            elif statement.elem_type == InterpreterBase.RETURN_DEF:
                status, return_val = self.__do_return(statement)

                # Find out if returned val_obj is a Lambda
                if statement.get("expression").get("name"):
                    if self.env.get(statement.get("expression").get("name")):
                        if self.env.get(statement.get("expression").get("name")).value():
                            if self.env.get(statement.get("expression").get("name")).value().elem_type == InterpreterBase.LAMBDA_DEF:
                                self.lambda_functions.append(statement.get("expression").get("name"))
                
                
            elif statement.elem_type == Interpreter.IF_DEF:
                status, return_val = self.__do_if(statement)
            elif statement.elem_type == Interpreter.WHILE_DEF:
                status, return_val = self.__do_while(statement)

            if status == ExecStatus.RETURN:
                self.env.pop()
                return (status, return_val)

        self.env.pop()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        if func_name == "inputi":
            return self.__call_input(call_node)
        if func_name == "inputs":
            return self.__call_input(call_node)

        actual_args = call_node.get("args")
        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        
        # Arg length checking for functions defined.
        if len(actual_args) != len(formal_args):
            if self.env.get(func_name):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Function ref'd by var {func_ast.get('name')} with {len(actual_args)} args not found",
                )
            else:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
                )
        # Handle Lambda Case
        found_env_bool, idx, found_env = self.env.find_env_by_lambda_alias(func_name)
        if found_env_bool:
            self.env.push_new_env(found_env)
        else:
            self.env.push()
        
        # Add arguments to environment
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.deepcopy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            self.env.create(arg_name, result)

            # Append refarg to list of refarged variables
            if formal_ast.elem_type == InterpreterBase.REFARG_DEF and actual_ast.elem_type == InterpreterBase.VAR_DEF:
                self.env.add_refarg(arg_name, actual_ast.get("name"))

        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop()
        return return_val

    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, call_ast):
        args = call_ast.get("args")
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
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))

        # Handle Lambda assignment
        if value_obj.type() == Type.FUNC and value_obj.value().elem_type == InterpreterBase.LAMBDA_DEF:
            if assign_ast.get("expression").elem_type == InterpreterBase.VAR_DEF:
                existing_var_name = assign_ast.get("expression").get("name")
                self.env.add_alias_to_env(existing_var_name, var_name)
                #print("Alias added")
            elif assign_ast.get("expression").elem_type == InterpreterBase.FCALL_DEF:
                _, _, new_env = self.env.find_env_by_lambda_alias(self.lambda_functions[-1])
                self.env.create_lambda_env(var_name, copy.deepcopy(new_env))
                self.lambda_functions.pop()
            else:
                self.env.create_lambda_env(var_name, None)
                #print("Lambda env created")
            self.lambda_functions.append(var_name)
            #print(self.env.lambda_environments)

        self.env.set(var_name, value_obj)

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            # print("getting as nil")
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            # print("getting as str")
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, expr_ast.get("val"))

        # Must conditionally evaluate for function assignment
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = None
            if var_name in self.func_name_to_ast and self.env.get(var_name) != None:
                super().error(ErrorType.NAME_ERROR, f"'{var_name}' is both function and variable.")
            
            # Variable assignment
            if self.env.get(var_name):
                val = self.env.get(var_name)
                    
            
            # Function assignment
            if var_name in self.func_name_to_ast:
                pot_args = list(self.func_name_to_ast[var_name].keys())
                if len(pot_args) != 1:
                    super().error(ErrorType.NAME_ERROR, f"Assignment of '{var_name}' is overloaded")
                val = Value(Type.FUNC, (self.func_name_to_ast[var_name][pot_args[0]]))
            
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable or function {var_name} not found")
            return val
        
        if expr_ast.elem_type == InterpreterBase.LAMBDA_DEF:
            return Value(Type.FUNC, copy.deepcopy(expr_ast))
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_DEF:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_DEF:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        # Perform type coercions if necessary
        left_value_obj, right_value_obj = self.__coercion_check(left_value_obj, right_value_obj, arith_ast)
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types {left_value_obj.type()} and {right_value_obj.type()}for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __coercion_check(self, left_value_obj, right_value_obj, arith_ast):
        # Perform necessary coercions
        # Boolean Conversions
        if arith_ast.elem_type in ["&&", "||"]:
            left_value_obj = self.__coerce_val(left_value_obj, Type.BOOL)
            right_value_obj = self.__coerce_val(right_value_obj, Type.BOOL)
        # Int to Bool value comparison Conversions
        if arith_ast.elem_type in ["==", "!="] and left_value_obj.type() != right_value_obj.type():
            if ((left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT) or 
                (left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL)):
                left_value_obj = self.__coerce_val(left_value_obj, Type.BOOL)
                right_value_obj = self.__coerce_val(right_value_obj, Type.BOOL)
        # Bool to Int for binary operands
        if arith_ast.elem_type in ["+", "-", "*", "/"]:
            if left_value_obj.type() == Type.BOOL or right_value_obj.type() == Type.BOOL:
                left_value_obj = self.__coerce_val(left_value_obj, Type.INT)
                right_value_obj = self.__coerce_val(right_value_obj, Type.INT)
        
        return left_value_obj, right_value_obj

    def __coerce_val(self, obj, expected_type):
        # Coece Int to Bool or Bool to Int
        if obj.type() != expected_type:
            # Bool to Int
            if obj.type() == Type.BOOL:
                return Value(expected_type, int(obj.value()))
            # Int to Bool
            if obj.type() == Type.INT:
                return Value(expected_type, bool(obj.value()))
            # Return error if coercion impossible
            else:
                super().error(
                ErrorType.TYPE_ERROR,
                f"Coercion error for {expected_type} operation with operand {obj.value()}",
            )
        # If already the expect type, just return the value
        return Value(expected_type, obj.value())

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))

        # Coerce Int to Bool for logical negation.
        if value_obj.type() == Type.INT:
            value_obj = self.__coerce_val(value_obj, t)
        
        # Evaluate operand
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_int_ops(self):
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
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
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
   
    def __setup_str_ops(self):
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
    
    def __setup_bool_ops(self):
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __setup_null_ops(self):
        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
    
    def __setup_func_ops(self):
        self.op_to_lambda[Type.FUNC] = {}
        self.op_to_lambda[Type.FUNC]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.FUNC]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __setup_ops(self):
        self.op_to_lambda = {}
        # Integer
        self.__setup_int_ops()

        # String
        self.__setup_str_ops()

        # Bool
        self.__setup_bool_ops()

        # Null
        self.__setup_null_ops()

        # Funcs
        self.__setup_func_ops()



        
        



    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        
        if result.type() != Type.BOOL:
            if result.type() == Type.INT:
                result = self.__coerce_val(result, Type.BOOL)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for if condition",
                )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_while(self, while_ast):
        cond_ast = while_ast.get("condition")
        run_while = Interpreter.TRUE_VALUE
        while run_while.value():
            run_while = self.__eval_expr(cond_ast)
            if run_while.type() != Type.BOOL:
                if run_while.type() == Type.INT:
                    run_while = self.__coerce_val(run_while, Type.BOOL)
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Incompatible type for while condition",
                    )
            if run_while.value():
                statements = while_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.deepcopy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
    

if __name__ == "__main__":
        program_source = """
            func foo(ref x) {
                x();
            }

            func main() {
            a = lambda() { print("hi"); };
            foo(a);
            }
        """
        # Implement RETURN functionality.
        # Remember to encase the func {} with three quotations.
        interpreter = Interpreter(InterpreterBase)
        interpreter.run(program_source)
