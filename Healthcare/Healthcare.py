'''
Coverage_Clash_Beta.py
Updated version of "Coverage Clash" game with full state variables and operators.
Works with Web_SOLUZION5 system.
'''

#<METADATA>
SOLUZION_VERSION = "5.0"
PROBLEM_NAME = "Coverage Clash"
PROBLEM_VERSION = "1.0"
PROBLEM_AUTHORS = ['Shreyas', 'Lauren', 'Yaxin', 'Jennifer']
PROBLEM_CREATION_DATE = "9-September-2025"
PROBLEM_DESC=\
 '''Coverage Clash simulates competing forces in U.S. healthcare access.
 Policy Makers aim to reduce the healthcare access gap, while Insurance Companies
 aim to maximize profit. Features full state tracking including budgets, public
 opinion, influence meters, and comprehensive operator sets with bribery mechanics.'''
#</METADATA>

#<COMMON_DATA>
EMPTY = 2 # Not used in this game but included for consistency
POLICY_MAKER = 0
INSURANCE_COMPANY = 1
NAMES = ["Policy Maker", "Insurance Company", " "] # Third element for consistency with Tic-Tac-Toe
#</COMMON_DATA>

#<COMMON_CODE>
DEBUG=True
from soluzion5 import Basic_State, \
  Basic_Operator as Operator, ROLES_List, add_to_next_transition
import Select_Roles as sr
import random

def int_to_name(i):
  return NAMES[i]


class State(Basic_State):
    def __init__(self, old=None):
        if old is None:
            # Initial state
            self.whose_turn = POLICY_MAKER   # Policy Maker starts
            self.current_role_num = POLICY_MAKER  # Although role_num is the same
            # in this game as whose_turn, the SOLUZION software 
            # needs both to be specified, in general.
            self.current_role = int_to_name(self.current_role_num)
            self.uninsured_rate = 10.0  # percentage
            self.public_health_index = 60  # 0-100 scale
            self.access_gap_index = 30  # lower is better for policymaker
            self.profit = 65  # insurer profit in billions
            self.public_trust_meter = 50  # policymaker trust percentage
            self.influence_meter = 70  # insurer influence percentage
            self.budget = 70  # policymaker budget in billions
            self.premium_cap_turns_left = 0  # turns left where insurer can't raise premiums
            self.skip_next_turn = False  # for lobbying effects
            self.win = "" # String that describes a win, if any.
            self.winner = -1 # Integer giving role number of winner.
            self.bribe_choice_active = False # Flag to activate bribe options
            self.public_expansion_cap_turns_left = 0 # New variable for bribery effect
            self.last_lobbied = 0
            self.policymaker_bonus_turn_used_55 = False
            self.policymaker_bonus_turn_used_62 = False
            self.policymaker_bonus_turn_used_72 = False
            # The initial state is now ready.
        else:
            # Here we handle the case where an old state was passed in;
            # we'll make the new state be a deep copy of the old, and
            # it can then be mutated by the operator that called for
            # this new instance to be created.
            self.whose_turn = old.whose_turn
            self.current_role = old.current_role
            self.current_role_num = old.current_role_num
            self.uninsured_rate = old.uninsured_rate
            self.public_health_index = old.public_health_index
            self.access_gap_index = old.access_gap_index
            self.profit = old.profit
            self.public_trust_meter = old.public_trust_meter
            self.influence_meter = old.influence_meter
            self.budget = old.budget
            self.premium_cap_turns_left = old.premium_cap_turns_left
            self.skip_next_turn = old.skip_next_turn
            self.win = old.win
            self.winner = old.winner
            self.bribe_choice_active = old.bribe_choice_active
            self.public_expansion_cap_turns_left = old.public_expansion_cap_turns_left
            self.last_lobbied = old.last_lobbied
            self.policymaker_bonus_turn_used_55 = old.policymaker_bonus_turn_used_55
            self.policymaker_bonus_turn_used_62 = old.policymaker_bonus_turn_used_62
            self.policymaker_bonus_turn_used_72 = old.policymaker_bonus_turn_used_72

    def __str__(self):
        # Produces a simple textual description of a state.
        # Doesn't mention any win that might exist.
        return (f"=== COVERAGE CLASH GAME STATE ===\n"
                f"Current Turn: {self.current_role}\n"
                f"Uninsured Rate: {self.uninsured_rate:.1f}%\n"
                f"Public Health Index: {self.public_health_index}\n"
                f"Access Gap Index: {self.access_gap_index}\n"
                f"Insurance Profit: ${self.profit} billion\n"
                f"Public Trust (Policymaker): {self.public_trust_meter}%\n"
                f"Influence (Insurer): {self.influence_meter}%\n"
                f"Policymaker Budget: ${self.budget} billion\n"
                f"Premium Cap Turns Left: {self.premium_cap_turns_left}\n"
                f"Public Expansion Cap Turns Left: {self.public_expansion_cap_turns_left}\n")

    def __eq__(self, s):
        return self.__str__() == s.__str__()

    def __hash__(self):
        return (self.__str__()).__hash__()
    
    def find_any_win(self):
        # Policy Maker win condition: Access Gap Index below 15 (improved access)
        if self.access_gap_index < 15:
            return ("Policy Maker wins! Healthcare access significantly improved.", POLICY_MAKER)
            
        # Insurance Company win condition: Profit greater than 85 billion
        if self.profit > 85:
            return ("Insurance Company wins! Profit target achieved.", INSURANCE_COMPANY)
            
        # lose conditions
        if self.uninsured_rate > 14:
            return ("Game over - Uninsured rate too high! Both sides lose.", -1)
        if self.public_health_index < 30:
            return ("Game over - Public health crisis! Both sides lose.", -1)
        if self.access_gap_index > 45:
            return ("Game over - The access gap between income groups is too high! Policymaker loses.", INSURANCE_COMPANY)
        if self.public_trust_meter < 30:
            return ("Game over - The Policymaker has lost public trust and has been voted out! Policymaker loses.", INSURANCE_COMPANY)
            
        return False
  
    def check_for_win(self):
        any_win = self.find_any_win()
        if any_win: 
            (self.win, self.winner) = any_win
            #print("in check_for_win, we found: ", self.win)
        else:
            pass  # self.win = ""
        return any_win
    
    def is_goal(self):
        # This method is used by the SOLUZION system to test if
        # a final state of a game or problem has been reached.
        any_win = self.check_for_win()
        if any_win: return True  # Win or lose condition met
        return False # Game continues.

    def goal_message(self):
        # Needed by SOLUZION.
        if self.win != "":
            return self.win
        else:
            return "Game continues."

    def text_view_for_role(self, role_num):
        # Return a textual rep. of what the player for
        # this role should see in the current state.
        # "View for (role):"
        # Includes information about any win.
        role_name = int_to_name(role_num)
        txt = "Current view for " + role_name + ":\n"
        txt += str(self)
        if self.win == "" and not self.is_goal():
            txt += "It's "+int_to_name(self.whose_turn)+"'s turn.\n"
        elif self.winner != -1:
            txt += "Winner is "+int_to_name(self.winner)+"\n"
        elif self.win != "":
            txt += self.win + "\n"
        
        # Role-specific information
        if self.win == "":
            if role_num == POLICY_MAKER:
                txt += "\n--- POLICY MAKER GOALS ---\n"
                txt += f"WIN: Get Access Gap Index below 15 (currently {self.access_gap_index})\n"
                txt += f"AVOID: Uninsured rate above 25% (currently {self.uninsured_rate:.1f}%)\n"
                txt += f"AVOID: Public Health below 30 (currently {self.public_health_index})\n"
                txt += f"AVOID: Budget reaching 0 (currently ${self.budget} billion)\n"
                if self.budget < 15:
                    txt += f"\nWARNING: Low budget! Consider requesting funds.\n"
            elif role_num == INSURANCE_COMPANY:
                txt += f"\n--- INSURANCE COMPANY GOALS ---\n"
                txt += f"WIN: Get profit above $85 billion (currently ${self.profit} billion)\n"
                txt += f"AVOID: Uninsured rate above 25% (currently {self.uninsured_rate:.1f}%)\n"
                txt += f"AVOID: Public Health below 30 (currently {self.public_health_index})\n"
                if self.premium_cap_turns_left > 0:
                    txt += f"\nNOTE: Premium increases blocked for {self.premium_cap_turns_left} more turns\n"
        return txt

SESSION = None

# The function next_player(k, inactive_ok=False) returns
# the number of the player after player k.
def next_player(k):
  if k==POLICY_MAKER: return INSURANCE_COMPANY
  else: return POLICY_MAKER

def update_turn(news):
  
  # First, check if the turn should be skipped (Insurer bribe)
  if news.skip_next_turn:
    news.skip_next_turn = False
    return

  # Now, check if a bonus turn should be given based on the public trust meter
  if news.whose_turn == POLICY_MAKER:
    if news.public_trust_meter >= 72 and not news.policymaker_bonus_turn_used_72:
      add_to_next_transition("The Policymaker has reached a public trust meter of 72% and earns a bonus turn!", news)
      news.policymaker_bonus_turn_used_72 = True
      return
    elif news.public_trust_meter >= 62 and not news.policymaker_bonus_turn_used_62:
      add_to_next_transition("The Policymaker has reached a public trust meter of 62% and earns a bonus turn!", news)
      news.policymaker_bonus_turn_used_62 = True
      return
    elif news.public_trust_meter >= 55 and not news.policymaker_bonus_turn_used_55:
      add_to_next_transition("The Policymaker has reached a public trust meter of 55% and earns a bonus turn!", news)
      news.policymaker_bonus_turn_used_55 = True
      return

  # If no bonus turn is granted, proceed with normal turn advancement
  current = news.whose_turn
  updated = next_player(current)
  news.whose_turn = updated
  news.current_role_num = updated
  news.current_role = NAMES[updated]
  
  # Decrement premium cap counter
  if news.premium_cap_turns_left > 0 and news.whose_turn == POLICY_MAKER:
    news.premium_cap_turns_left -= 1

def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

# A function to facilitate role-specific visualizations...
def is_user_in_role(role_num):
  username = SESSION['USERNAME']
  rm = SESSION['ROLES_MEMBERSHIP']
  if rm==None: return False
  users_in_role = rm[role_num]
  return username in users_in_role

def get_session():
  return SESSION

#------------------
# Policy Maker operators
def expand_public_coverage(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" expands public coverage.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index - 6, 0, 100)
    new_s.public_trust_meter = clamp(s.public_trust_meter + 3, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate - 0.5, 0, 100)
    new_s.profit = clamp(s.profit - 5, 0, 200)
    new_s.public_health_index = clamp(s.public_health_index + 5, 0, 100)
    new_s.budget = clamp(s.budget - 17, 0, 200)
    update_turn(new_s)
    return new_s

def subsidize_coverage(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" subsidizes coverage.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index - 3, 0, 100)
    new_s.public_trust_meter = clamp(s.public_trust_meter + 2, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate - 0.3, 0, 100)
    new_s.profit = clamp(s.profit - 3, 0, 200)
    new_s.public_health_index = clamp(s.public_health_index + 4, 0, 100)
    new_s.budget = clamp(s.budget - 11, 0, 200)
    update_turn(new_s)
    return new_s

def request_funds(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" requests funds from the government.", new_s)
    
    # 30% chance of being intercepted by the insurer
    if random.random() < 0.3:
        add_to_next_transition("Funds are intercepted! The Insurance Company can now choose to act.", new_s)
        new_s.bribe_choice_active = True
    else:
        add_to_next_transition("Request succeeds!", new_s)
        new_s.budget = clamp(s.budget + 15, 0, 200)
        
    update_turn(new_s)
    return new_s

def cap_premiums(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" caps insurance premiums.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index - 2, 0, 100)
    new_s.public_trust_meter = clamp(s.public_trust_meter + 5, 0, 100)
    new_s.influence_meter = clamp(s.influence_meter - 8, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate - 0.2, 0, 100)
    new_s.premium_cap_turns_left = 3  # Insurer can't raise premiums for 3 turns
    new_s.budget = clamp(s.budget - 11, 0, 200)
    update_turn(new_s)
    return new_s

def mandate_coverage(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" mandates coverage.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index - 4, 0, 100)
    new_s.public_trust_meter = clamp(s.public_trust_meter - 2, 0, 100)  # Some public backlash
    new_s.uninsured_rate = clamp(s.uninsured_rate - 1.0, 0, 100)
    new_s.public_health_index = clamp(s.public_health_index + 3, 0, 100)
    new_s.budget = clamp(s.budget - 7, 0, 200)
    update_turn(new_s)
    return new_s

def invest_in_clinics(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" invests in public clinics.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index - 3, 0, 100)
    new_s.public_health_index = clamp(s.public_health_index + 6, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate - 0.4, 0, 100)
    new_s.public_trust_meter = clamp(s.public_trust_meter + 4, 0, 100)
    new_s.budget = clamp(s.budget - 15, 0, 200)
    update_turn(new_s)
    return new_s

#------------------
# Insurance Company operators
def raise_premiums(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" raises premiums.", new_s)
    new_s.profit = clamp(s.profit + 6, 0, 200)
    new_s.access_gap_index = clamp(s.access_gap_index + 3, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate + 0.8, 0, 100)
    new_s.public_health_index = clamp(s.public_health_index - 2, 0, 100)
    new_s.influence_meter = clamp(s.influence_meter - 2, 0, 100)  # Public backlash
    new_s.last_lobbied += 1
    update_turn(new_s)
    return new_s

def risk_selection(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" engages in risk selection.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index + 6, 0, 100)
    new_s.influence_meter = clamp(s.influence_meter - 5, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate + 0.6, 0, 100)
    new_s.profit = clamp(s.profit + 5, 0, 200)
    new_s.public_health_index = clamp(s.public_health_index - 4, 0, 100)
    new_s.last_lobbied += 1
    update_turn(new_s)
    return new_s

def narrow_provider_network(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" narrows provider network.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index + 5, 0, 100)
    new_s.influence_meter = clamp(s.influence_meter - 3, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate + 0.8, 0, 100)
    new_s.profit = clamp(s.profit + 3, 0, 200)
    new_s.public_health_index = clamp(s.public_health_index - 4, 0, 100)
    new_s.last_lobbied += 1
    update_turn(new_s)
    return new_s

def lobby_government(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" lobbies government, causing policymaker to lose a turn.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index + 3, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate + 0.6, 0, 100)
    new_s.public_health_index = clamp(s.public_health_index - 4, 0, 100)
    '''new_s.influence_meter = clamp(s.influence_meter - 5, 0, 100)'''
    # Skip policymaker's next turn
    new_s.skip_next_turn = True
    new_s.last_lobbied = 0
    update_turn(new_s)
    return new_s

def misinformation_campaigns(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" launches misinformation campaigns.", new_s)
    new_s.access_gap_index = clamp(s.access_gap_index + 3, 0, 100)
    new_s.influence_meter = clamp(s.influence_meter + 5, 0, 100)
    new_s.uninsured_rate = clamp(s.uninsured_rate + 0.3, 0, 100)
    new_s.profit = clamp(s.profit - 3, 0, 200)  # Campaigns cost money
    new_s.public_trust_meter = clamp(s.public_trust_meter - 5, 0, 100)  # Reduce policymaker trust
    new_s.last_lobbied += 1
    update_turn(new_s)
    return new_s

def prevent_expansion(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" uses intercepted funds to prevent public coverage expansion for 3 turns.", new_s)
    new_s.public_expansion_cap_turns_left = 3
    new_s.bribe_choice_active = False # Reset the flag
    new_s.skip_next_turn = True   # the Insurer still gets their regular turn in addition to the bribe
    update_turn(new_s)
    return new_s

def fund_misinformation_with_bribe(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" uses intercepted funds to launch a misinformation campaign.", new_s)
    new_s.public_trust_meter = clamp(s.public_trust_meter - 5, 0, 100)
    new_s.bribe_choice_active = False # Reset the flag
    new_s.skip_next_turn = True   # the Insurer still gets their regular turn in addition to the bribe
    update_turn(new_s)
    return new_s
  
def turn_pass(s):
    new_s = State(s)
    add_to_next_transition(int_to_name(s.whose_turn)+" passes.", new_s)
    if new_s.whose_turn == POLICY_MAKER:
        new_s.public_trust_meter = clamp(s.public_trust_meter - 5, 0, 100)
        if new_s.access_gap_index >= 30:
            new_s.access_gap_index = clamp(s.access_gap_index + 1, 0, 100)
        if new_s.influence_meter >= 80:
            new_s.access_gap_index = clamp(s.access_gap_index + 2, 0, 100)
    if new_s.whose_turn == INSURANCE_COMPANY:
        new_s.influence_meter = clamp(s.influence_meter - 5, 0, 100)
        if new_s.influence_meter <= 65:
            new_s.profit = clamp(s.profit - 2, 0, 100)
    update_turn(new_s)
    return new_s
    

#------------------
# Precondition functions
def can_expand_coverage(s):
    return s.whose_turn == POLICY_MAKER and s.budget >= 20 \
    and s.public_expansion_cap_turns_left <= 0
def can_subsidize(s):
    return s.whose_turn == POLICY_MAKER and s.budget >= 14

def can_request_funds(s):
    return s.whose_turn == POLICY_MAKER

def can_cap_premiums(s):
    return s.whose_turn == POLICY_MAKER and s.budget >= 14

def can_mandate_coverage(s):
    return s.whose_turn == POLICY_MAKER and s.budget >= 10

def can_invest_clinics(s):
    return s.whose_turn == POLICY_MAKER and s.budget >= 18

def can_raise_premiums(s):
    return s.whose_turn == INSURANCE_COMPANY and s.premium_cap_turns_left <= 0

def can_risk_select(s):
    return s.whose_turn == INSURANCE_COMPANY

def can_narrow_network(s):
    return s.whose_turn == INSURANCE_COMPANY

def can_lobby(s):
    return s.whose_turn == INSURANCE_COMPANY and s.influence_meter >= 75 and s.last_lobbied >= 3

def can_misinformation(s):
    return s.whose_turn == INSURANCE_COMPANY and s.profit >= 3

def can_bribe_prevent_expansion(s):
    return s.whose_turn == INSURANCE_COMPANY and s.bribe_choice_active

def can_bribe_fund_misinformation(s):
    return s.whose_turn == INSURANCE_COMPANY and s.bribe_choice_active

def p_can_pass(s):
    return s.whose_turn == POLICY_MAKER

def i_can_pass(s):
    return s.whose_turn == INSURANCE_COMPANY

#------------------
#<OPERATORS>
# Policy Maker operators - following Tic-Tac-Toe pattern
POLICY_MAKER_OPS = [Operator("Expand Public Coverage",\
  lambda s: can_expand_coverage(s),
  lambda s: expand_public_coverage(s)),
  Operator("Subsidize Coverage",\
  lambda s: can_subsidize(s),
  lambda s: subsidize_coverage(s)),
  Operator("Request Funds",\
  lambda s: can_request_funds(s),
  lambda s: request_funds(s)),
  Operator("Cap Premiums",\
  lambda s: can_cap_premiums(s),
  lambda s: cap_premiums(s)),
  Operator("Mandate Coverage",\
  lambda s: can_mandate_coverage(s),
  lambda s: mandate_coverage(s)),
  Operator("Invest in Clinics",\
  lambda s: can_invest_clinics(s),
  lambda s: invest_in_clinics(s)),
  Operator("Pass",\
  lambda s: p_can_pass(s),
  lambda s: turn_pass(s))]

# Insurance Company operators - following Tic-Tac-Toe pattern  
INSURANCE_COMPANY_OPS = [Operator("Raise Premiums",\
  lambda s: can_raise_premiums(s),
  lambda s: raise_premiums(s)),
  Operator("Risk Selection",\
  lambda s: can_risk_select(s),
  lambda s: risk_selection(s)),
  Operator("Narrow Provider Network",\
  lambda s: can_narrow_network(s),
  lambda s: narrow_provider_network(s)),
  Operator("Lobby Government",\
  lambda s: can_lobby(s),
  lambda s: lobby_government(s)),
  Operator("Misinformation Campaigns",\
  lambda s: can_misinformation(s),
  lambda s: misinformation_campaigns(s)),
  # bribe operators
  Operator("Prevent Expansion (Bribe)",\
  lambda s: can_bribe_prevent_expansion(s),
  lambda s: prevent_expansion(s)),
  Operator("Fund Misinformation (Bribe)",\
  lambda s: can_bribe_fund_misinformation(s),
  lambda s: fund_misinformation_with_bribe(s)),
  Operator("Pass",\
  lambda s: i_can_pass(s),
  lambda s: turn_pass(s))]

OPERATORS = POLICY_MAKER_OPS + INSURANCE_COMPANY_OPS    # Operators for Insurance Companies

#</OPERATORS>
    
#</COMMON_CODE>

#<INITIAL_STATE>
def create_initial_state():
  return State()
#</INITIAL_STATE>

#<ROLES>
ROLES = [ {'name': 'Policy Maker', 'min': 1, 'max': 1},
          {'name': 'Insurance Company', 'min': 1, 'max': 1},
          {'name': 'Observer', 'min': 0, 'max': 25}]
#</ROLES>

#<STATE_VIS>
BRIFL_SVG = True
render_state = None
def use_BRIFL_SVG():
  global render_state
  from  Healthcare_SVG_FOR_BRIFL import render_state
DEBUG_VIS = True
#</STATE_VIS>


