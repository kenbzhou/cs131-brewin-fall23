from env_v1 import EnvironmentManager
from type_valuev1 import Type, Value, create_value, get_printable
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from copy import deepcopy


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    BIN_OPS = {"+", "-", "*", "/"}
    UNR_OPS = {"neg", "!"}
    COM_OPS = {"==", "!=", "<", "<=", ">", ">=", "||", "&&"}

    # METHODS
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    def run(self, program):
        # Create an AST
        ast = parse_program(program)
        # Set up function definitions connected to the "root" node
        self.__set_up_function_table(ast)
        # Obtain the "main" function node: the root of the execution
        main_func = self.__get_func_by_name("main", 0)

        # Set up the variable dictionary (environmentManager) for the main function, along with a stack implementation for the various scopes.
        self.env = [EnvironmentManager()]
        # Run main() in sequence
        if self.trace_output:
            print("Entering main()...")
        main_exec = self.__run_statements(main_func.get("statements"))

        if self.trace_output:
            print("MAIN OUTPUT: ", main_exec.value())


    # Runs the statements associated in the function's node.
    def __run_statements(self, statements):
        # all statements of a function are held in arg3 of the function AST node
        if self.trace_output:
            print(" Running statements for function...")
        for statement in statements:
            if self.trace_output:
                print(" statement", statement)
            # Function call
            if statement.elem_type == InterpreterBase.FCALL_DEF:
                if self.trace_output:
                    print("  entering function call...")
                call = self.__call_func(statement)
            # Assignment
            elif statement.elem_type == "=":
                if self.trace_output:
                    print("  entering assignment call...")
                call = self.__assign(statement)
            # If
            elif statement.elem_type == "if":
                if self.trace_output:
                    print("  entering if call...")
                call = self.__run_if(statement)
                if call.value() != None:
                    return deepcopy(call)
            # While
            elif statement.elem_type == "while":
                if self.trace_output:
                    print("  entering while call...")
                call = self.__run_while(statement)
                if call.value() != None:
                    return deepcopy(call)
            # Return
            elif statement.elem_type == "return":
                if self.trace_output:
                    print("  entering return call...")
                if statement.get("expression") == None:
                    break
                call = self.__eval_expr(statement.get("expression"))
                return deepcopy(call)
        return Interpreter.NIL_VALUE

        
    ### IF AND WHILE LOOPS ###
    # Run if statement
    def __run_if(self, if_node):
        # Instantiate scope for "if"
        self.env.append(deepcopy(self.env[-1]))

        result = Interpreter.NIL_VALUE

        # Evaluate condition
        if self.__test_condition(if_node.get("condition")):
            result = self.__run_statements(if_node.get("statements"))
        elif if_node.get("else_statements"):
            result = self.__run_statements(if_node.get("else_statements"))
        
        # Leave scope and resolve any inconsistencies
        self.__destroy_scope_and_res_inconsistencies([])

        return result
    
    # Run while statement
    def __run_while(self, while_node):
        # Instantiate scope for "while"
        self.env.append(deepcopy(self.env[-1]))

        result = Interpreter.NIL_VALUE

        # Evaluate condition
        while self.__test_condition(while_node.get("condition")):
            result = self.__run_statements(while_node.get("statements"))
            # If Return value detected
            if result != Interpreter.NIL_VALUE:
                break


        # Leave scope and resolve any inconsistencies
        self.__destroy_scope_and_res_inconsistencies([])

        return result

    # Tests if/while condition
    def __test_condition(self, eval_node):
        if self.trace_output:
            print("               evaluating condition for if/while statement")
        condition = self.__eval_expr(eval_node)
        if self.trace_output:
            print("            ",condition.value())
        if condition.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Defined if/while condition does not evaluate to Boolean",
            )
        return condition.value()
    

    ###  HELPERS ###
    # Resolve any inconsistencies between this scope and the nesting scope
    def __destroy_scope_and_res_inconsistencies(self, shadowed_parameters):
        resolved_environment = self.env.pop()
        for symbol in resolved_environment.environment:
            if self.env[-1].get(symbol) != None and symbol not in shadowed_parameters:
                self.env[-1].set(symbol, resolved_environment.get(symbol))

    # Assigns value to a variable.
    def __assign(self, assign_ast):
        # Retrieve name of variable to assign to
        var_name = assign_ast.get("name")
        # Evaluate whatever expression is captured by the =
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        # Within the overall function environment, set the variable name.
        self.env[-1].set(var_name, value_obj)

    # Retrieves the function by name from the function table
    def __get_func_by_name(self, name, arg_len):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
            if arg_len not in self.func_name_to_ast[name]:
                super().error(ErrorType.NAME_ERROR, f"Function {name} with argument count of {arg_len} not found")
        return self.func_name_to_ast[name][arg_len]

    def __get_all_instances(self):
        print("Environment vars at this time")
        for environment in self.env:
            environment.get_all_variables()


    ### FUNCTIONS ###
    # Calls the associated function
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        if func_name == "print":
            return self.__call_print(call_node)
        elif func_name == "inputi" or func_name == "inputs":
            return self.__call_input(call_node)
        elif func_name in self.func_name_to_ast:
            return self.__call_external(call_node)

        # TODO: add code here later to call other functions
        super().error(ErrorType.NAME_ERROR, f"Function {func_name} not found")

    # Calls the print function
    def __call_print(self, call_ast):
        output = ""
        for arg in call_ast.get("args"):
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    # Calls the inputi or inputs function
    def __call_input(self, call_ast):
        args = call_ast.get("args")
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() or inputs() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if call_ast.get("name") == "inputi":
            return Value(Type.INT, int(inp))
        if call_ast.get("name") == "inputs":
            return Value(Type.STRING, str(inp)) 
    
    # Calls an otherwise defined function
    def __call_external(self, call_ast):
        args = call_ast.get("args")
        func_name = call_ast.get("name")

        # Check if function definition exists within function dictioanry
        if len(args) not in self.func_name_to_ast[func_name]:
            super().error(
                ErrorType.NAME_ERROR, f"No overloaded function for {func_name} that accepts {len(args)} parameters"
            )
        
        # Create a new scope for the function
        self.env.append(deepcopy(self.env[-1]))

        # Get the function node
        func_node = self.__get_func_by_name(func_name, len(args))

        # Load in the arguments
        shadowed_parameters = []
        if self.trace_output:
            print("       evaluating arguments for function", call_ast.get("name"))
        for name_node, val_node in zip(func_node.get("args"), args):
            shadowed_parameters.append(name_node.get("name"))
            var_value = self.__eval_expr(val_node)
            self.env[-1].set(name_node.get("name"), var_value)
            if self.trace_output:
                print("          VAR", name_node.get("name"), ":", var_value.value())

        # Now, run the function
        return_val = self.__run_statements(func_node.get("statements"))

        # Destroy the environment
        self.__destroy_scope_and_res_inconsistencies(shadowed_parameters)

        return return_val


    ### OPERAND AND EXPRESSION EVALUATION ###
    # Evaluates the expression.
    def __eval_expr(self, expr_ast):
        if self.trace_output:
            print("    evaluating expression...")
        # VARIABLES
        # Int var
        if expr_ast.elem_type == InterpreterBase.INT_DEF:
            if self.trace_output:
                print("     returning integer of value", expr_ast.get("val"))
            return Value(Type.INT, expr_ast.get("val"))
        # String var
        if expr_ast.elem_type == InterpreterBase.STRING_DEF:
            if self.trace_output:
                print("     returning string of value", expr_ast.get("val"))
            return Value(Type.STRING, expr_ast.get("val"))
        # Boolean var
        if expr_ast.elem_type == InterpreterBase.BOOL_DEF:
            if self.trace_output:
                print("     returning bool of value", expr_ast.get("val"))
            return Value(Type.BOOL, expr_ast.get("val"))
        # Nil var
        if expr_ast.elem_type == InterpreterBase.NIL_DEF:
            if self.trace_output:
                print("     returning nil of value", expr_ast.get("val"))
            return Value(Type.NIL, expr_ast.get("val"))
        
        # Preexisting var
        if expr_ast.elem_type == InterpreterBase.VAR_DEF:
            var_name = expr_ast.get("name")
            val = self.env[-1].get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            if self.trace_output:
                print("     returning var of value", val.value())
            return val
        
        # If recursed to a function call, call the function
        if expr_ast.elem_type == InterpreterBase.FCALL_DEF:
            if self.trace_output:
                    print("     calling function", expr_ast.get("name"))
            return self.__call_func(expr_ast)
        
        # Handle binary operators
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_bin_op(expr_ast)
        
        # Handle unary operators
        if expr_ast.elem_type in Interpreter.UNR_OPS:
            return self.__eval_unary_op(expr_ast)

        # Handle comparison operators
        if expr_ast.elem_type in Interpreter.COM_OPS:
            return self.__eval_comp_op(expr_ast)

    # Evaluates unary operation.
    def __eval_unary_op(self, arith_ast):
        operator_val = self.__eval_expr(arith_ast.get("op1"))
        if arith_ast.elem_type not in self.op_to_lambda[operator_val.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {operator_val.type()}",
            )
        f = self.op_to_lambda[operator_val.type()][arith_ast.elem_type]
        return f(operator_val)
    
    # Evaluates binary operation.
    def __eval_bin_op(self, arith_ast):
        # Conclude the expressions to be evaluated.
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        # Check types of operators

        # Check "+" for strings at is a unique case.
        if arith_ast.elem_type == '+':
            if (left_value_obj.type() != Type.STRING or right_value_obj.type() != Type.STRING) and (left_value_obj.type() != Type.INT or right_value_obj.type() != Type.INT):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible variable types for variables {left_value_obj.value()} {right_value_obj.value()} in {arith_ast.elem_type} operation",
                )
        elif left_value_obj.type() != Type.INT or right_value_obj.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Non integer variables {left_value_obj.value()} {right_value_obj.value()} for {arith_ast.elem_type} operation",
            )

        # Check if the operator is contained within the dictionary for the current type
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No {arith_ast.elem_type} found for type {left_value_obj.type()}",
            )
        # Retrieve the associated operator from the dictionary of operators
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        # Execute the operations on the functions
        return f(left_value_obj, right_value_obj)
    
    # Evaluates comparison operators
    def __eval_comp_op(self, arith_ast):
        # Conclude the expressions to be evaluated.
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        # Handle special case for '==' and '!='
        if arith_ast.elem_type == "==" or arith_ast.elem_type == "!=":
            f = self.op_to_lambda[Type.BOOL][arith_ast.elem_type]
            if (left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL) or (left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT):
                if arith_ast.elem_type == "==":
                    return Value(Type.BOOL, False)
                else:
                    return Value(Type.BOOL, True)
            return f(left_value_obj, right_value_obj)
        
        # Handle mismatched operand types
        elif left_value_obj.type() != right_value_obj.type():
            super().error(
                ErrorType.TYPE_ERROR,
                f"Non-matching variables {left_value_obj.value()} {right_value_obj.value()} for {arith_ast.elem_type} operation",
            )
        
        # Check operator existence in dictionary
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No {arith_ast.elem_type} found for type {left_value_obj.type()}",
            )
        
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)
        

    ### INSTANTIATION ###
    # Creates a dictionary of function nodes in the AST
    def __set_up_function_table(self, ast):
        # This is the Dictionary
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            if func_def.get("name") not in self.func_name_to_ast:
                self.func_name_to_ast[func_def.get("name")] = {}
            self.func_name_to_ast[func_def.get("name")][len(func_def.get("args"))] = func_def

            # KEY : VALUE = FUNC_NAME, FUNC_NODE
            # KEY : VALUE = FUNC_NAME, DICT
            #                           KEY : VALUE = ARGLEN : FUNC_NODE

    # Set up various operators to be called upon in dictionary
    def __setup_ops(self):
        # Instantiate the dictionary of OPERATORS_FOR_EACH_TYPE
        self.op_to_lambda = {}

        # Set up operations on integers
        self.__setup_int_ops()

        # Set up operations on strings
        self.__setup_string_ops()

        # Set up operations on bools
        self.__setup_bool_ops()

    def __setup_int_ops(self):
        self.op_to_lambda[Type.INT] = {}
        # Unary Operators
        self.op_to_lambda[Type.INT]["neg"] = lambda x: Value(
            x.type(), -1 * x.value()
        )

        # Binary Operators
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


        # Comparison Operators
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
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

    def __setup_string_ops(self):
        self.op_to_lambda[Type.STRING] = {}
        # Binary Operators
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )

        # Comparison Operators
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
    
    def __setup_bool_ops(self):
        self.op_to_lambda[Type.BOOL] = {}
        # Unary Operators
        self.op_to_lambda[Type.BOOL]["!"] = lambda x: Value(
            x.type(), not x.value()
        )
        # Comparison Operators
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            Type.BOOL, x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            Type.BOOL, x.value() and y.value()
        )


if __name__ == "__main__":
    program_source = """
        func main(){
            print(1 == true);
        }
    """
    # Implement RETURN functionality.
    # Remember to encase the func {} with three quotations.
    interpreter = Interpreter(InterpreterBase)
    interpreter.run(program_source)