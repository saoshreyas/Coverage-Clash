#!/usr/bin/python3
'''Select_Roles.py

This is the version of Aug. 13, 2025 which sets up
default ROLES if none found in problem formulation.
Previously was June 26, 2025,
which not only allows some roles to NOT
be played (minimum required players for role is 0),
and also adds an overall minimum number of roles
that have to be filled before a game can proceed.

It also adds a "default_is_played" field that can
be used by the client here to automatically assign
the role to the first, second, etc., player listed.
E.g., if NO CHOICES are made, OCLUEdo's Miss Scarlet
AND Mr. Green can both be automatically assigned to
the ONE PLAYER (assuming no players have been identified).

This file was created in order to work with Text_SOLUZION5.py
and OCCLUEdo.py.

'''

# Removed circular import for Web_SOLUZION5 compatibility
# import Text_SOLUZION5 as isc # Recursive import. (OK?)
# PROBLEM = isc.PROBLEM
PROBLEM = None  # Will be set by the server
import soluzion5 as SZ # version with ROLES_List defined.

#print("Looks like the Textual Client supporting roles was imported ok.")

ROLES = []

LAST_ROLE_UP = None
def announce_whose_turn(current_state):
  role_num = current_state.current_role
  if role == LAST_ROLE_UP:
    print("It's still "+str(whose_turn)+"'s turn.")
  else:
    role = ROLES[role_num]["name"]
    print("Now it is "+role+"'s turn.")
    print("If you are playing "+role+", press Enter now.")
    x = input("...")
    print("OK")

def get_roles():
  # Any declaration of ROLES ?
  global ROLES
  try:
    ROLES = PROBLEM.ROLES
    print("ROLES obtained from the formulation file.")
  except NameError:
    ROLES = None  
  except:
    print("No ROLES defined for this problem. Using default ROLES.")
    ROLES = [{'name':'Player/Solver 1', 'min':1, 'max':1}] # Default

  
def hasKey(dct, ky):
  "Return True if dict contains key."
  return ky in dct

#if not ROLES:
#    print("No ROLES defined, so we'll proceed with normal play.")
#    isc.mainloop()

MIN_ROLES_TO_PLAY = 1
MAX_ROLES_TO_PLAY = -1 # means no maximum, or limited to roles that exit.
PLAYERS = []
ASSIGNMENTS = []

MOST_RECENT_PLAYER = 'Player 1'
MOST_RECENT_ROLE = 'Role 1'
MOST_RECENT_ROLE_NUM = 0

def initialize_roles():
#else:
    global MIN_ROLES_TO_PLAY, MAX_ROLES_TO_PLAY, PLAYERS, ASSIGNMENTS, ROLES
    global MOST_RECENT_PLAYER
    global MOST_RECENT_ROLE_NUM
    global MOST_RECENT_ROLE
    print("There are the following roles:")
    # Set default of 1:
    MIN_ROLES_TO_PLAY = 1
    # If nobody takes a role, the game cannot be played.
    # But it is OK for the default player to be assigned the first role by default.
    MAX_ROLES_TO_PLAY = -1 # means no maximum, or limited to roles that exit.
    # We can imagine a game, e.g., with 3 roles defined of which only 2 can
    # be played at a time.  Weird, but allowed here.
    for role in ROLES:
      if hasKey(role, "name"):
        print(role)

    try:
      MIN_ROLES_TO_PLAY = ROLES.min_num_of_roles_to_play
    except:
      pass
    try:
      MAX_ROLES_TO_PLAY = ROLES.max_num_of_roles_to_play
    except:
      pass
    print("Minimum number of roles to be filled is ",MIN_ROLES_TO_PLAY)
    print("Maximum number of roles to be filled is ",MAX_ROLES_TO_PLAY)
    if int(MAX_ROLES_TO_PLAY)==-1: print("  (unlimited, the default)")
            
    # Set a callback to use in the Int_Solv_Client, that
    # will be called whenever there is a change in whose
    # turn it is.
    isc.announce_whose_turn = announce_whose_turn

    PLAYERS = ['Player 1', 'Player 2'] # Default.
    ASSIGNMENTS = [[0], [1]] + [[] for i in ROLES] # There might be 3 extra entries, but ignore them.

    # DEPRECATED AS the initial state will give the role that starts.
    # MOST_RECENT_ROLE = ROLES[0]['name'] # default is that player of ROLEs[0] goes first.
    # Need to override this in games like CLUE where not all roles have to be played.
    
    try: 
      MOST_RECENT_PLAYER = PLAYERS[ASSIGNMENTS[0][0]] # Needs changing to look up role index using the name of the role from the initial state.
    except:
      print("NOTE that role "+MOST_RECENT_ROLE+" has not been assigned to a player.")
      print("Quitting.")
      exit()
      
    
def display_current_role_assignments():
  print('''
+--------------------------------------+
|  PLAYER(S) SELECT YOUR ROLE(S)       |
|    for a game of OCLUEdo             |                                      |
|                                      |
|  Current roles and players are:      |
|                                      |
|  ROLE:    PLAYER                     |
|  ----     ------                     |''')
      
  for i, role in enumerate(ROLES):
    if "name" in role.keys():
      a = ASSIGNMENTS [i]
      if a==[]:
        players_assigned = "(none)"
      else:
        pnames = [PLAYERS[k] for k in a]
        players_assigned = ' & '.join(pnames)
      print("|  "+role["name"]+': ' + players_assigned)
  print('''|                                      |
|  Choices are:                        |
|     a. Go with current selection     |
|     b. Change a player name          |
|     c. Add a new player              |
|     d. Edit player(s) for ROLE       |
+--------------------------------------+     
''')

def show_players():
  print("Player Number    Player Name")
  print("-------------    -----------")
  for i, player in enumerate(PLAYERS):
    print(i+1, "              ", player)
        
def show_roles():
  print("Role Number    Role Name")
  print("-----------    ---------")
  for i, role in enumerate(ROLES):
    if "name" in role.keys():
      print(i+1, "            ", role["name"])
        
def select_roles():
  done = False
  while not done:
    display_current_role_assignments()
    response = input("Enter a, b, c, or d: ").upper()
    if response=='': print("Empty response; try again."); continue
    if response[0]=='A': return
    if response[0]=='B': change_player_name()
    elif response[0]=='C': add_player()
    elif response[0]=='D': edit_role_assignment()

def change_player_name():
  show_players()
  done = False
  while not done:
    player_to_change = input("Number for the player whose name should change (or c to cancel): ")
    if player_to_change.lower() == 'c': return
    try:
      player_num = int(player_to_change)-1
      if player_num < 0 or player_num >= len(PLAYERS):
        print("Player number must be between 1 and",len(PLAYERS))
        continue
      new_name = input("Input the new name: ")
      PLAYERS[player_num] = new_name
      done = True
    except:
      print("Invalid player number: ", player_to_change)

def add_player():
  player_name = input("Input name for new player: ")
  PLAYERS.append(player_name)

def edit_role_assignment():
  show_roles()
#  new_name = input("Input the new name: ")
  done = False
  while not done:
    role_to_change = input("Number for the role to get an updated assignment: ")
    try:
      role_num = int(role_to_change)
      if role_num < 1 or role_num > len(ROLES):
        print("NOTE: Role number must be between 1 and", len(ROLES))
        continue
      role_num -= 1 # Account for 0-based indexing in Python
      done = True
    except:
      print("Invalid role number: ", role_to_change)
  done = False
  while not done:
    show_players()
    print("Choose a player.")
    print("To remove the player from that role, NEGATE the player number.")
    player_to_assign = input("Number for a player to assign to this role: ")
    try:
      player_num = int(player_to_assign)
      deassign_player = False
      if player_num < 0:
        deassign_player = True
        player_num = - player_num
      player_num -= 1  # account for 0-based indexing in Python.
      if player_num < len(PLAYERS):
         done = True
      else:
        print("\nSORRY: Player number cannot exceed", len(PLAYERS))
    except:
      print("Invalid player number: ", player_to_assign)
  try:
    if deassign_player:
      try:
        ASSIGNMENTS[role_num].remove(player_num)
      except:
        print("NOTE: Player ",PLAYERS[player_num]," was not assigned to role ", ROLES[role_num]["name"])
    else:
      ASSIGNMENTS[role_num].append(player_num)
    return
  
  except:
    print("Could not assign or deassign player ",player_num," to role ", role_num)

def get_first_filled_role():
  # Can be used in games like Clue to determine who goes first.
  for role_num, role in enumerate(ROLES):
    if len(ASSIGNMENTS[role_num])>0:
      first_filled_role = (role_num, role)
      return first_filled_role
  print("Cannot proceed with the game, since no roles have been assigned to players.")
  return None

def role_being_played(role_num):
  return len(ASSIGNMENTS[role_num])>0

def get_first_player_for_role(role_num):
  plist = ASSIGNMENTS[role_num]
  if len(plist) > 0:
    return PLAYERS[plist[0]]
  else:
    return None
  
def cue_player(current_state):
  global MOST_RECENT_PLAYER
  global MOST_RECENT_ROLE_NUM
  global MOST_RECENT_ROLE
  player_continuing = False
  role_continuing = False
  # Get current role and player assigned to that role
  
  #if player==None: player=MOST_RECENT_PLAYER
  role=current_state.current_role
  role_num = current_state.current_role_num
  player = get_first_player_for_role(role_num)
  if player==None:
    player = MOST_RECENT_PLAYER
  if player==MOST_RECENT_PLAYER:
    player_continuing = True
  if role==MOST_RECENT_ROLE:
    role_continuing = True

  divider = '--------------------------------------------------'+'\n'
  prompt = divider
  if player_continuing and role_continuing:
    prompt += '('+player+' continuing in role '+role+' ... )\n'
  elif player_continuing:
      prompt += '('+player+' changing to role '+role+')\n'
  else:
    prompt += MOST_RECENT_PLAYER+' please turn over the computer to '+player+' for the role of '+role+')\n'
  prompt += divider
  print(prompt)
  ok = input('Press Enter to confirm.')
  print("Who's up: "+player+", in the role of "+role+".")
  MOST_RECENT_PLAYER = player
  MOST_RECENT_ROLE_NUM = role_num
  MOST_RECENT_ROLE = role

def is_ready_to_play():
  """Check if enough roles are filled to start a game"""
  global ROLES, ASSIGNMENTS, MIN_ROLES_TO_PLAY
  if not ROLES:
    return False
  
  filled_roles = 0
  for i, role in enumerate(ROLES):
    if len(ASSIGNMENTS[i]) >= role['min']:
      filled_roles += 1
  
  return filled_roles >= MIN_ROLES_TO_PLAY
