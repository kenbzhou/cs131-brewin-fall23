# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
import copy

class EnvironmentManager:
    # Var:Val, Refarg:MappedVar:
    def __init__(self):
        self.environment = [({}, {})]
        self.lambda_environments = [([], {})]

    # returns a VariableDef object
    def get(self, symbol):
        for env in reversed(self.environment):
            if symbol in env[0]:
                return env[0][symbol]

        return None

    def set(self, symbol, value):
        #print("ASSIGNING ", value.value(), "to", symbol)
        for env in reversed(self.environment):
            if symbol in env[0]:
                env[0][symbol] = value
                #print("REFARGS AT ASSIGNMENT POINT:", env[1])
                if symbol in env[1]:
                    symbol = env[1][symbol]
                    continue
                else:
                    return
        # symbol not found anywhere in the environment
        self.environment[-1][0][symbol] = value
    
    def set_refarg(self, symbol, value):
        to_change_symbol = None
        if symbol not in self.environment[-1][1]:
            print("Symbol not in initial refarg list")
            return False
        
        self.set(symbol, value)
        for env in reversed(self.environment):
            refarg_list = env[1]
            if to_change_symbol == None:
                to_change_symbol = refarg_list[symbol]
                continue
            if to_change_symbol in env[0]:
                env[0][to_change_symbol] = value
                if to_change_symbol in refarg_list:
                    to_change_symbol = refarg_list[to_change_symbol]
                else:
                    return True
        return False
    

    # LAMBDA SPECIFIC FUNCTIONS
    def flatten_environment(self):
        flattened = {}
        for env in reversed(self.environment):
            for symbol in env[0]:
                if symbol not in flattened:
                    flattened[symbol] = copy.deepcopy(env[0][symbol])
        return flattened

    
    def create_lambda_env(self, var_name, env):
        if env == None:
            self.lambda_environments.append(([var_name], self.flatten_environment()))
        self.lambda_environments.append(([var_name], env))

    def add_alias_to_env(self, var_name, new_var):
        ret, idx, var_env = self.find_env_by_lambda_alias(var_name)
        if ret:
            self.lambda_environments[idx][0].append(new_var)
        else:
            print("NO EXISTING ALIAS FOUND")
    
    
    def find_env_by_lambda_alias(self, alias):
        for i in range(len(self.lambda_environments)):
            if alias in self.lambda_environments[i][0]:
                return True, i, self.lambda_environments[i][1]
        return False, None, None
    

    # When lambda function is assigned to a variable:
    #   lambda func is bound to variable
    #   environment at the time is flattened
    #   alias of function, as well as environment, is stored in lambda_environments

    # When variable 'new' is assigned to another var with a lambda function 'old':
    #   variable 'new' points to same value object as variable 'old'
    #   variable 'new' finds saved environment of variable 'old', and adds itself to alias list

    # When variable with lambda function is called:
    #   Stored lambda environment is retrieved
    #   lambda environment is appended to environment



    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        self.environment[-1][0][symbol] = value
    
    # Add refarged variable into list of variables.
    def add_refarg(self, refarg_symbol, mapped_var):
        self.environment[-1][1][refarg_symbol] = mapped_var

    # used when we enter a nested block to create a new environment for that block
    def push(self):
        self.environment.append(({},{}))  # [{}] -> [{}, {}]
    
    def push_new_env(self, env):
        self.environment.append((env, {}))

    # used when we exit a nested block to discard the environment for that block
    def pop(self):
        self.environment.pop()
