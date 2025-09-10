'''soluzion5.py

(was soluzion5c.py)

This file provides base classes for states and
operators.
This serves as part of the SOLUTION version 5
system of problem representation.

S.T., June 26, 2025

June 23, 2025: Slight change to Operator. There is an
optional role parameter now.  Needed so the precondition can
depend on what role a given player is taking.  Although
the state will typically represent whose turn it is, the
operator should not show up as applicable to any player
except the one who is playing that role.

June 24, 2025: Another tweak to the operator definition.
When accessing an operator's name, use the method
get_name(). This will either return the stored string name
or, if a function has been stored instead, apply that
function to the current state to get the string name to
return.  The driving use case for this is in OCCLUEdo,
where the operators to show cards need to compute the
names of the cards that can be shown.
'''

class Basic_State:
    Initial_State = None
    def __init__(self, old=None):
        if old==None:
            self.desc = "initial State"
            # Save the initial state for possible use
            # in reporting, analytics, etc.
            self.current_role = None # Default is no turn-taking
            Basic_State.Initial_State = self
        else:
            self.desc = "another state"
            # Normally, a subclass should do a deep copy here.

    def __str__(self):
        return s.desc

    def __eq__(self, other):
        if s.desc != other.desc: return False
        return True

    def __hash__(self):
        return str(self).__hash__()

    def is_goal(self):
        return False

class Invalid_State_Exception(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "Invalid state because: "+self.msg
    
class Basic_Operator:
    def __init__(self,
                 name,
                 precond=(lambda s: True),
                 transf=(lambda s: Basic_State(s)),
                 params=[]):
        self.name = name  # Either a string or a function of a state.
        self.precond = precond
        self.transf = transf
        self.params = params
 
    def is_applicable(self, s):
        return self.precond(s)

    def apply(self, s):
        if self.params:
            args = GET_ARGS(self)
            return self.transf(s, args)
        else:
            return self.transf(s)

    def get_name(self, s=None):
        if type(self.name)==type("abc"):
            return self.name # Just return the string.
        else:
            if s==None: return "deferred to runtime"
            else: return self.name(s) # apply function of state s.
        
def GET_ARGS(op):
    pass  # The client will implement and overwrite this.

def add_to_next_transition(txt, news):
  # Save txt as a property of the new state to use as
  # part of the next transition.
  if hasattr(news, "jit_transition"):
    news.jit_transition += txt + "\n"
  else:
    news.jit_transition = txt + "\n"
    
class ROLES_List(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return self.__dict__[name]

    def __setattr__(self, name, value):
        self.__dict__[name] = value


