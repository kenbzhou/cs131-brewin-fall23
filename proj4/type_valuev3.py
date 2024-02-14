import copy

from enum import Enum
from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type(Enum):
    INT = 1
    BOOL = 2
    STRING = 3
    CLOSURE = 4
    NIL = 5
    OBJECT = 6


class Closure:
    def __init__(self, func_ast, env):
        self.captured_env = copy.deepcopy(env)
        self.func_ast = func_ast
        self.type = Type.CLOSURE

class Object:
    def __init__(self):
        self.members = {}
        self.proto = None
        self.type = Type.OBJECT

    def ret_member(self, member):
        if member in self.members:
            return self.members[member]
        elif self.proto:
            next_proto = self.proto
            while next_proto:
                if member in next_proto.value().members:
                    return next_proto.value().members[member]
                else:
                    next_proto = next_proto.value().proto

        return None
    
    def push_member(self, member, value):
        if member not in self.members:
            self.members[member] = ""
        
        if value.type() == Type.CLOSURE:
            self.members[member] = value
        else:
            #self.members[member] = copy.deepcopy(value)
            self.members[member] = value

    def add_proto(self, new_proto):
        if new_proto.value() == 'nil':
            self.proto = None
        else:
            self.proto = new_proto

        



# Create a field called self.proto.
# Self.proto can only point to one additional class.
# That class can only point to one additional class, and so forth.
# 


# Represents a value, which has a type and its value
class Value:
    def __init__(self, t, v=None):
        self.t = t
        self.v = v

    def value(self):
        return self.v

    def type(self):
        return self.t

    def set(self, other):
        self.t = other.t
        self.v = other.v


def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    else:
        raise ValueError("Unknown value type")


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None
