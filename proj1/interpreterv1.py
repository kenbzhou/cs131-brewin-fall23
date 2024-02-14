from brewparse import parse_program
from element import Element
from intbase import InterpreterBase, ErrorType

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        self.variables = {}
        self.functions = {}
    
    # Main worker function
    def run(self, program):
        # Create Abstract Syntax Tree
        ast = parse_program(program)
        # Load in all the function definitions
        self.load_in_functions(ast)
        # Get the main function node
        main_func_node = self.get_main_func_node(ast)
        # Run the main node
        self.run_func(main_func_node)
        pass

    # Loads in function definitions from AST
    def load_in_functions(self, ast):
        for function_node in ast.dict['functions']:
            self.functions[function_node.dict['name']] = function_node

    # Gets main() from AST; basic check on operatability
    def get_main_func_node(self, ast):
        if 'main' not in self.functions:
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
        return self.functions['main']
    
    # Run function-type call
    def run_func(self, func_node):
        for statement_node in func_node.dict['statements']:
            self.run_statement(statement_node)
    
    # Run statement
    def run_statement(self, statement_node):
        # Obtain statement type
        statement_type = statement_node.elem_type

        # Assignment
        if statement_type == '=':
            self.do_assignment(statement_node)

        # Function call
        elif statement_type == 'fcall':
            self.do_function_call(statement_node)

    def do_function_call(self, statement_node):
        function_name = statement_node.dict['name']
        # Run a defined function
        if function_name in self.functions:
            self.run_func(self.functions[function_name])

        # Run print
        elif function_name == 'print':
            self.print(statement_node.dict['args'])

        # Run inputi
        elif function_name == 'inputi':
            self.inputi(statement_node.dict['args'])
        
        # If function does not exist:
        else:
            super().error(ErrorType.NAME_ERROR, f"Function '{function_name}' does not exist.")

    # Process assignment call
    def do_assignment(self, statement_node):
        # Get target variable name
        var_name = statement_node.dict['name']

        # Create variable in variable dictionary
        if var_name not in self.variables:
            self.variables[var_name] = None

        # Evaluate expression
        expression_node = statement_node.dict['expression']
        self.variables[var_name] = self.evaluate_expression(expression_node)

        print(self.variables)


    def evaluate_expression(self, expression_node):
        expression_type = expression_node.elem_type
        # Evaluate if it's a value node.
        if expression_type == 'int' or expression_type == 'string':
            return self.get_val_node(expression_node)
        
        # Evaluate if it's a var node.
        elif expression_type == 'var':
            return self.get_var_node(expression_node)
        
        # Evaluate binary operator node
        elif expression_type == '-' or expression_type == '+':
            return self.eval_binary_operator(expression_node)
        
        # Evaluate negative node
        elif expression_type == 'neg':
            print(expression_node.dict)
            return self.eval_neg(expression_node)

        # Evaluate inputi function
        elif expression_type == 'fcall' and expression_node.dict['name'] == 'inputi':
            return self.inputi(expression_node.dict['args'])
        
        elif expression_type == 'fcall' and expression_node.dict['name'] in self.functions:
            return self.do_function_call(self.functions[expression_node.dict['name']])
        
        # For future use: if function is declared otherwise
        # elif expression_type == 'fcall' and expression_node.dict['name'] in self.functions:
        #       return self.run_func(self.functions[expression_node.dict['name']])

        # Evaluate impossible behavior
        else:
            super().error(ErrorType.NAME_ERROR, f"Call to '{expression_node.dict['name']}' fails.")

    

    ##### HELPERS #####

    # Handle value nodes
    def get_val_node(self, val_node):
        return val_node.dict['val']

    # Handle variable assignments
    def get_var_node(self, var_node):
        var_name = var_node.dict['name']
        if var_name not in self.variables:
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} has not been defined")
        return self.variables[var_name]
    
    # Handle binary operator
    def eval_binary_operator(self, operator_node):
        # Evaluate the operands post-order
        op1 = self.evaluate_expression(operator_node.dict['op1'])
        op2 = self.evaluate_expression(operator_node.dict['op2'])
        
        operator_type = operator_node.elem_type
        self.check_operand_types(op1, op2)

        # Evaluate using operator
        if operator_type == '-':
            return op1 - op2
        elif operator_type == '+':
            return op1 + op2
        
        # Throw error if nothing returns
        super().error(ErrorType.NAME_ERROR, f"Operation {op1} {operator_type} {op2} cannot conclude")
    
    # Evaluates negative operator
    def eval_neg(self, neg_node):
        #return -1 * 
        return -1 * self.evaluate_expression(neg_node.dict['op1'])
    
    # Checks operand types for operations
    def check_operand_types(self, op1, op2):
        if type(op1) != type(op2):
            super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")
        #elif type(op1) == 'string' or type(op2) == 'string':
        #    super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")
        return -1



    # FUNCTIONS
    def inputi(self, args):
        # If inputi has more than a single parameter, throw an error.
        if len(args) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes > 1 parameter")

        # Output prompt if existant
        if len(args) == 1:
            prompt = self.get_val_node(args[0])
            super().output(prompt)
        user_input = super().get_input()

        # Return user input
        return int(user_input)

    def print(self, args):
        overall_string = ""
        for element in args:
            overall_string += str(self.evaluate_expression(element))

        super().output(overall_string)



if __name__ == "__main__":
    program_source = """
        func main() {
            x = 3 + b();
            return x;
        }
        func b() {
            y = 3 + 7;
            return y;
        }
    """
    # Implement RETURN functionality.
    # Remember to encase the func {} with three quotations.
    interpreter = Interpreter(InterpreterBase)
    interpreter.run(program_source)



