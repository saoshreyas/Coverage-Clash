#!/usr/bin/python
'''Web_SZ5_01.py
Created: August 2025.  S. Tanimoto with Claude Code

This is an enhanced version of the Flask_SOLUZION5 system that supports:
  -- Multiple concurrent game sessions
  -- Enhanced UI features including splash screens, full-screen mode
  -- React frontend integration
  -- All 11 requirements from Requirements.txt

This program runs a multi-session web server for playing SOLUZION
games or solving SOLUZION problems through web browsers.

SOLUZION version 5 features supported:
  -- multiplayer role-based games with turn-taking
  -- parameterized operators (player-provided function arguments)
  -- transitions (messages for state changes)
  -- multiple concurrent sessions
  -- enhanced visualizations and UI

TECHNOLOGY:
Flask, flask_socketio, svgwrite, React (frontend)

HOW TO RUN:
> uv run python Web_SZ5_01.py Tic_Tac_Toe
> uv run python Web_SZ5_01.py Tic_Tac_Toe 5432  # custom port

Then access via browser at localhost:5000 (or specified port)
'''

if __name__ == '__main__':
    print("Hello from Web_SZ5_01.py - Multi-Session Python Web Server for SOLUZION5.")

from flask import Flask, render_template, session, request, jsonify, send_from_directory, send_file
import json
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
import uuid
import time
import threading
import copy
import webbrowser
import requests
import subprocess
import os
import traceback
import sys

import soluzion5 as SZ
import Select_Roles as SR

DEBUG = True
HOST = 'localhost'
PORT = 5000
formulation_name = None  # Will be set during initialization

import os
CURR_DIR = os.getcwd()
THE_DIR = ''

# Multi-session support
SESSIONS = {}  # Dictionary of active sessions
SESSION_CLEANUP_INTERVAL = 300  # 5 minutes
DEBUG_VIS_MODE = False  # Track if we're in debug visualization mode
DEBUG_BROWSERS_LAUNCHED = False  # Prevent multiple launches
DEBUG_SESSION_ID = None  # Store the debug session ID globally

# Session structure:
# SESSIONS[session_id] = {
#     'SESSION_DATA': {...},  # User/role data
#     'GAME_STATE': state_obj,
#     'GAME_IN_PROGRESS': False,
#     'ROLES_FROZEN': False,
#     'CREATED_AT': timestamp,
#     'LAST_ACTIVITY': timestamp,
#     'AUTOPLAY_ACTIVE': False,
#     'DEBUG_MODE': False
# }

def create_session():
    """Create a new game session with unique ID"""
    session_id = str(uuid.uuid4())
    
    # Initialize session with structure similar to original global SESSION
    session_data = {
        'USERNAMES': {},
        'NUMBER_OF_USERS': 0,
        'USER_NUMBERS': {},
        'SESSION_OWNER': None,
        'ROLES_MEMBERSHIP': None,
        'USERNAME': 'nobody now',
        'HOST': HOST,
        'PORT': PORT,
        'USE_ROLE_SPECIFIC_VISUALIZATIONS': True  # Enable role-specific vis like old system
    }
    
    SESSIONS[session_id] = {
        'SESSION_DATA': session_data,
        'GAME_STATE': None,
        'GAME_IN_PROGRESS': False,
        'ROLES_FROZEN': False,
        'CREATED_AT': time.time(),
        'LAST_ACTIVITY': time.time(),
        'AUTOPLAY_ACTIVE': False,
        'DEBUG_MODE': False,
        'PREVIOUS_STATE': None,  # For "show previous state" feature
        'TRANSITION_HISTORY': []  # For transition message history
    }
    
    return session_id

def get_session(session_id):
    """Get session data, updating last activity"""
    if session_id in SESSIONS:
        SESSIONS[session_id]['LAST_ACTIVITY'] = time.time()
        return SESSIONS[session_id]
    return None

def cleanup_inactive_sessions():
    """Remove sessions that have been inactive for too long"""
    current_time = time.time()
    sessions_to_remove = []
    
    for session_id, session in SESSIONS.items():
        # Remove sessions inactive for more than 1 hour
        if current_time - session['LAST_ACTIVITY'] > 3600:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del SESSIONS[session_id]
        print(f"Cleaned up inactive session: {session_id}")

def start_cleanup_thread():
    """Start background thread for session cleanup"""
    def cleanup_loop():
        while True:
            time.sleep(SESSION_CLEANUP_INTERVAL)
            cleanup_inactive_sessions()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()

# Start cleanup thread
start_cleanup_thread()

# Flask app setup
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Enhanced SOLUZION5 Multi-Session Server Key'
socketio = SocketIO(app, async_mode=async_mode)

# Problem formulation will be loaded at startup
PROBLEM = None
ROLES = [{'name':'Player/Solver 1', 'min':1, 'max':1}] # Default; also defined in Select_Roles, as of Aug. 13, 2025.

def initialize_roles_membership(session_id):
    """Initialize roles membership for a specific session (only if not already initialized)"""
    session = get_session(session_id)
    if not session:
        return
    
    # Only initialize if ROLES_MEMBERSHIP is None - don't overwrite existing assignments!
    if session['SESSION_DATA']['ROLES_MEMBERSHIP'] is None:
        session['SESSION_DATA']['ROLES_MEMBERSHIP'] = [[] for i in range(len(ROLES))]
        if DEBUG:
            print(f"Initialized empty ROLES_MEMBERSHIP for session {session_id}")
    else:
        if DEBUG:
            print(f"ROLES_MEMBERSHIP already exists for session {session_id}: {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
    
    # Make session data available to problem formulation code
    PROBLEM.SESSION = session['SESSION_DATA']

def get_users_in_role(session_id, role_no):
    """Get users in a specific role for a session"""
    session = get_session(session_id)
    if not session:
        return []
    
    rm = session['SESSION_DATA']['ROLES_MEMBERSHIP']
    if rm is None:
        # Initialize if needed
        rm = [[] for i in range(len(ROLES))]
        session['SESSION_DATA']['ROLES_MEMBERSHIP'] = rm
    
    if role_no >= len(rm):
        return []
    
    return rm[role_no]

def get_roles_for_user(session_id, username):
    """Return list of role numbers for a user in a session"""
    roles_for_user = []
    session = get_session(session_id)
    
    if DEBUG:
        print(f"Getting roles for user {username} in session {session_id}")
        if session:
            rm = session['SESSION_DATA']['ROLES_MEMBERSHIP']
            print(f"ROLES_MEMBERSHIP: {rm}")
        else:
            print("Session not found!")
    
    for role_no in range(len(ROLES)):
        users_in_role = get_users_in_role(session_id, role_no)
        if DEBUG:
            print(f"Role {role_no} ({ROLES[role_no]['name']}): users = {users_in_role}")
            print(f"  Checking if '{username}' is in {users_in_role}")
            print(f"  Username type: {type(username)}, values in list types: {[type(u) for u in users_in_role]}")
        if username in users_in_role:
            roles_for_user.append(role_no)
            if DEBUG:
                print(f"  ✅ MATCH: {username} is in role {role_no}")
        elif DEBUG:
            print(f"  ❌ NO MATCH: {username} not in role {role_no}")
    
    if DEBUG:
        print(f"🔧 FINAL: User {username} has roles: {roles_for_user}")
    
    return roles_for_user

def update_roles_data(session_id):
    """Update roles data for a specific session"""
    session = get_session(session_id)
    if not session:
        return []
    
    roles_data = []
    rm = session['SESSION_DATA']['ROLES_MEMBERSHIP']
    
    # Initialize roles membership if it's None
    if rm is None:
        rm = [[] for i in range(len(ROLES))]
        session['SESSION_DATA']['ROLES_MEMBERSHIP'] = rm
    
    for i, role in enumerate(ROLES):
        this_role = {
            'desc': role['name'], 
            'min': role['min'], 
            'max': role['max'],
            'who': rm[i] if i < len(rm) else [],
            'current': len(rm[i]) if i < len(rm) else 0,
            'role_num': i
        }
        roles_data.append(this_role)
    return roles_data

def all_required_roles_filled(session_id):
    """Check if all required roles have minimum players in a session"""
    session = get_session(session_id)
    if not session:
        return False
    
    roles_data = update_roles_data(session_id)
    
    for role_data in roles_data:
        required_min = role_data.get('min', 0)
        current_count = len(role_data.get('who', []))
        
        if required_min > 0 and current_count < required_min:
            if DEBUG:
                print(f"🔧 Role '{role_data['desc']}' needs {required_min} players, has {current_count}")
            return False
    
    if DEBUG:
        print(f"🔧 All required roles filled for session {session_id}")
    return True

def check_auto_start_debug_game(session_id):
    """Auto-start game when all required roles filled in debug mode"""
    session = get_session(session_id)
    if not session:
        return
    
    # Only auto-start in debug mode
    if not session.get('DEBUG_MODE', False):
        return
    
    # Only auto-start if game hasn't started yet
    if session.get('GAME_IN_PROGRESS', False):
        return
    
    # Check if all required roles are filled
    if not all_required_roles_filled(session_id):
        if DEBUG:
            print(f"🔧 Not all roles filled yet for debug session {session_id}")
        return
    
    if DEBUG:
        print(f"🔧 All roles filled in debug session {session_id} - auto-starting game!")
    
    # Small delay to let UI update, then auto-start
    def delayed_start():
        time.sleep(2)  # Give clients time to process role updates
        
        session = get_session(session_id)
        if not session or session.get('GAME_IN_PROGRESS', False):
            return  # Game already started or session gone
        
        owner = session['SESSION_DATA']['SESSION_OWNER']
        if DEBUG:
            print(f"🔧 Auto-starting debug game for session {session_id} as owner {owner}")
        
        # Start the game directly using socketio.emit instead of the handler
        # (since handle_game_command requires SocketIO context)
        session = get_session(session_id)
        if not session or session.get('GAME_IN_PROGRESS', False):
            return  # Game already started or session gone
        
        # Initialize the problem for this session
        if not initialize_problem_for_session(session_id):
            print(f"Error: Failed to initialize problem for debug auto-start in session {session_id}")
            return
        
        session['GAME_IN_PROGRESS'] = True
        if DEBUG:
            print(f"Debug auto-start: Game started for session {session_id}, emitting game_started and problem state")
        
        # Use socketio.emit instead of emit to work outside of event handler context
        socketio.emit('game_started', room=session_id, namespace='/session')
        emit_problem_state(session_id, use_socketio_emit=True)
    
    threading.Thread(target=delayed_start, daemon=True).start()

# Routes
@app.route('/')
def index():
    """Main page - will serve React frontend"""
    global DEBUG_VIS_MODE
    
    # Check for new debug parameters
    debug_mode = request.args.get('debug', 'false').lower() == 'true'
    player_name = request.args.get('player', '')
    role_num = request.args.get('role', '0')
    
    # Handle debug mode URL parameters (new approach)
    if debug_mode and player_name:
        problem_name = getattr(PROBLEM, 'PROBLEM_NAME', formulation_name) if 'PROBLEM' in globals() else formulation_name
        if DEBUG:
            print(f"🔧 Debug route - problem_name: {problem_name}")
        problem_desc = getattr(PROBLEM, 'PROBLEM_DESC', 'No problem description available.') if 'PROBLEM' in globals() else 'No problem description available.'
        return render_template('index.html', 
                             async_mode=socketio.async_mode, 
                             port=PORT,
                             debug_mode=debug_mode,
                             debug_player=player_name,
                             debug_role=int(role_num),
                             debug_vis_mode=DEBUG_VIS_MODE,
                             problem_name=problem_name,
                             problem_desc=problem_desc)
    
    # Legacy debug player access (old approach - keep for now)
    debug_player = request.args.get('debug_player')
    debug_session_id = request.args.get('session_id')
    
    if debug_player and debug_session_id:
        # This is a debug player accessing the full interface - allow it
        problem_name = getattr(PROBLEM, 'PROBLEM_NAME', formulation_name) if 'PROBLEM' in globals() else formulation_name
        problem_desc = getattr(PROBLEM, 'PROBLEM_DESC', 'No problem description available.') if 'PROBLEM' in globals() else 'No problem description available.'
        return render_template('index.html', async_mode=socketio.async_mode, port=PORT, debug_vis_mode=DEBUG_VIS_MODE, problem_name=problem_name, problem_desc=problem_desc)
    
    # In debug visualization mode, show a message instead of normal login (for non-debug access)
    if DEBUG_VIS_MODE:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug Mode Active - Web SOLUZION5</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                .debug-notice { background: #e7f3ff; border: 2px solid #0066cc; border-radius: 10px; 
                               padding: 20px; max-width: 600px; margin: 0 auto; }
            </style>
        </head>
        <body>
            <div class="debug-notice">
                <h2>🔧 Debug Visualization Mode Active</h2>
                <p>The server is running in <strong>DEBUG_VIS</strong> mode.</p>
                <p>Browser tabs should have opened automatically with debug players.</p>
                <p>If tabs didn't open automatically, check the server console for manual URLs.</p>
                <hr>
                <p><strong>Debug Players:</strong></p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Player 1 → X role</li>
                    <li>Player 2 → O role</li>
                    <li>Player 3 → Observer role</li>
                </ul>
                <p><small>To disable debug mode, set DEBUG_VIS=False in the formulation file.</small></p>
            </div>
        </body>
        </html>
        '''
    
    problem_name = getattr(PROBLEM, 'PROBLEM_NAME', formulation_name) if 'PROBLEM' in globals() else formulation_name
    problem_desc = getattr(PROBLEM, 'PROBLEM_DESC', 'No problem description available.') if 'PROBLEM' in globals() else 'No problem description available.'
    if DEBUG:
        print(f"🔧 Route / - PROBLEM available: {'PROBLEM' in globals()}")
        print(f"🔧 Route / - formulation_name: {formulation_name}")
        print(f"🔧 Route / - problem_name: {problem_name}")
    return render_template('index.html', async_mode=socketio.async_mode, port=PORT, debug_vis_mode=DEBUG_VIS_MODE, problem_name=problem_name, problem_desc=problem_desc)

@app.route('/api/sessions')
def get_sessions():
    """API endpoint to get list of active sessions"""
    session_list = []
    for session_id, session_data in SESSIONS.items():
        session_info = {
            'session_id': session_id,
            'created_at': session_data['CREATED_AT'],
            'game_in_progress': session_data['GAME_IN_PROGRESS'],
            'num_users': session_data['SESSION_DATA']['NUMBER_OF_USERS'],
            'owner': session_data['SESSION_DATA']['SESSION_OWNER']
        }
        session_list.append(session_info)
    
    if DEBUG:
        print(f"Returning {len(session_list)} sessions: {session_list}")
    
    return jsonify(session_list)

@app.route('/api/sessions', methods=['POST'])
def create_new_session():
    """API endpoint to create a new session"""
    session_id = create_session()
    return jsonify({'session_id': session_id})

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session_api(session_id):
    """API endpoint to delete a session"""
    try:
        data = request.get_json()
        username = data.get('username') if data else None
        
        if not username:
            return jsonify({'error': 'Username required'}), 400
            
        if session_id not in SESSIONS:
            return jsonify({'error': 'Session not found'}), 404
            
        session_data = SESSIONS[session_id]
        session_owner = session_data['SESSION_DATA']['SESSION_OWNER']
        
        # Only session owner can delete the session
        if session_owner != username:
            return jsonify({'error': 'Only session owner can delete this session'}), 403
            
        # Notify all users in the session before deletion
        socketio.emit('session_ended_by_owner', {
            'message': f'Current session ended by owner {session_owner}'
        }, room=session_id, namespace='/session')
        
        # Close the room and remove session
        close_room(session_id, namespace='/session')
        del SESSIONS[session_id]
        
        if DEBUG:
            print(f"Session {session_id} deleted by owner {username}")
            
        return jsonify({'message': 'Session deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/get_image/<image_filename>')
def get_image(image_filename):
    """Serve images from problem formulation directory"""
    return send_file(THE_DIR + "/images/" + image_filename, mimetype='image/jpg')

# Debug mode endpoints
@app.route('/debug-auto-login')
def debug_auto_login():
    """Auto-login page for debugging mode - bypasses normal login"""
    player_name = request.args.get('player', 'Player 1')
    session_id = request.args.get('session_id', '')
    role_num = request.args.get('role', '0')
    
    return render_template('debug_login.html', 
                         player_name=player_name, 
                         session_id=session_id, 
                         role_num=int(role_num),
                         port=PORT)

@app.route('/debug-game')
def debug_game():
    """Direct game interface for debug players"""
    player_name = request.args.get('player', 'Player 1')
    session_id = request.args.get('session_id', '')
    
    if not player_name or not session_id:
        return "Missing player name or session ID", 400
    
    # Check if session exists before serving the interface
    session = get_session(session_id)
    if not session:
        return f"Debug session {session_id[:8]}... not found. Available sessions: {list(SESSIONS.keys())}", 404
    
    # Pre-populate the React app with debug player info
    return render_template('debug_game.html', 
                         player_name=player_name, 
                         session_id=session_id,
                         port=PORT)

@app.route('/debug-status')
def debug_status():
    """Debug endpoint to check session status"""
    return jsonify({
        'debug_mode': DEBUG_VIS_MODE,
        'debug_session_id': DEBUG_SESSION_ID,
        'active_sessions': list(SESSIONS.keys()),
        'session_count': len(SESSIONS),
        'sessions_detail': {
            sid: {
                'owner': session['SESSION_DATA'].get('SESSION_OWNER'),
                'users': session['SESSION_DATA'].get('NUMBER_OF_USERS', 0),
                'game_in_progress': session.get('GAME_IN_PROGRESS', False),
                'usernames': session['SESSION_DATA'].get('USERNAMES', {}),
                'roles_membership': session['SESSION_DATA'].get('ROLES_MEMBERSHIP', [])
            }
            for sid, session in SESSIONS.items()
        }
    })

# SocketIO event handlers
@socketio.on('join_session', namespace='/session')
def handle_join_session(data):
    """Handle user joining a specific session"""
    session_id = data.get('session_id')
    username = data.get('username')
    is_debug_vis = data.get('debug_vis_mode', False)
    
    if DEBUG:
        print(f"=== JOIN_SESSION REQUEST ===")
        print(f"Session ID: {session_id}")
        print(f"Username: {username}")
        print(f"Debug VIS Mode: {is_debug_vis}")
        print(f"Available sessions: {list(SESSIONS.keys())}")
    
    if not session_id or not username:
        if DEBUG:
            print("❌ Missing session_id or username")
        emit('error', {'message': 'Missing session_id or username'})
        return
    
    session = get_session(session_id)
    if not session:
        if DEBUG:
            print(f"❌ Session {session_id} not found")
            print(f"Available sessions: {list(SESSIONS.keys())}")
        emit('error', {'message': 'Session not found'})
        return
    
    if DEBUG:
        print(f"✅ Session {session_id} found, processing join...")
    
    # Mark session as DEBUG_MODE if this is a DEBUG_VIS_MODE join
    if is_debug_vis and DEBUG_VIS_MODE:
        session['DEBUG_MODE'] = True
        if DEBUG:
            print(f"🔧 Marked session {session_id} as DEBUG_MODE due to DEBUG_VIS_MODE")
    
    # Join the SocketIO room for this session
    join_room(session_id)
    
    # Update session data
    session_data = session['SESSION_DATA']
    if username not in session_data['USERNAMES']:
        session_data['USERNAMES'][session_data['NUMBER_OF_USERS']] = username
        session_data['USER_NUMBERS'][username] = session_data['NUMBER_OF_USERS']
        session_data['NUMBER_OF_USERS'] += 1
        
        # First user becomes session owner
        if session_data['SESSION_OWNER'] is None:
            session_data['SESSION_OWNER'] = username
    
    session_data['USERNAME'] = username
    
    # Emit success and current session state
    emit('joined_session', {
        'session_id': session_id,
        'is_owner': username == session_data['SESSION_OWNER'],
        'roles_data': update_roles_data(session_id),
        'game_in_progress': session['GAME_IN_PROGRESS'],
        'roles_frozen': session['ROLES_FROZEN']
    })
    
    # Notify other users in the session
    emit('user_joined', {
        'username': username,
        'user_count': session_data['NUMBER_OF_USERS']
    }, room=session_id, include_self=False)

@socketio.on('role_request', namespace='/session')
def handle_role_request(data):
    """Handle user requesting to join/leave a role"""
    session_id = data.get('session_id')
    username = data.get('username')
    role_no = data.get('role_number')
    join_or_quit = data.get('join_or_quit')
    
    session = get_session(session_id)
    if not session:
        emit('error', {'message': 'Session not found'})
        return
        
    if session['ROLES_FROZEN']:
        emit('error', {'message': 'Cannot change roles - they are frozen'})
        return
    
    # During active game, only allow Observer role changes
    if session['GAME_IN_PROGRESS']:
        if role_no >= len(ROLES):
            emit('error', {'message': 'Invalid role number'})
            return
        role_info = ROLES[role_no]
        if role_info.get('name', '') != 'Observer':
            emit('error', {'message': 'During active games, only Observer role changes are allowed'})
            return
    
    rm = session['SESSION_DATA']['ROLES_MEMBERSHIP']
    if rm is None:
        rm = [[] for i in range(len(ROLES))]
        session['SESSION_DATA']['ROLES_MEMBERSHIP'] = rm
    
    if role_no >= len(rm):
        emit('error', {'message': 'Invalid role number'})
        return
    
    current_members = rm[role_no]
    current_status = username in current_members
    
    join = True
    changed = False
    
    # Toggle logic: if user is in role, leave it; if not in role, join it
    if (join_or_quit == 'join_or_quit') and current_status:
        join = False
    
    if join and not current_status:
        # Check if role is full
        role_info = ROLES[role_no]
        if len(current_members) >= role_info['max']:
            emit('error', {'message': f'Role {role_info["name"]} is full'})
            return
        current_members.append(username)
        changed = True
    elif (not join) and current_status:
        current_members.remove(username)
        changed = True
    
    if changed:
        # Update the session data available to problem formulation
        PROBLEM.SESSION = session['SESSION_DATA']
        
        if DEBUG:
            print(f"🔧 ROLE ASSIGNMENT: User {username} {'joined' if join else 'left'} role {ROLES[role_no]['name']} in session {session_id}")
            print(f"🔧 Updated ROLES_MEMBERSHIP: {rm}")
            print(f"🔧 Username type stored: {type(username)}")
            print(f"🔧 Role {role_no} now has users: {rm[role_no] if role_no < len(rm) else 'INDEX OUT OF RANGE'}")
            
            # Verify the user is actually in the role
            verify_roles = get_roles_for_user(session_id, username)
            print(f"🔧 VERIFICATION: get_roles_for_user({username}) returns: {verify_roles}")
        
        roles_data = update_roles_data(session_id)
        
        # Enhanced debugging for role updates
        if DEBUG:
            print(f"🔧 Emitting roles_announcement to session {session_id}")
            print(f"🔧 Roles data being sent: {json.dumps(roles_data, indent=2)}")
            
            # Check if all required roles are filled
            filled_roles = 0
            required_roles = 0
            for role_data in roles_data:
                if role_data.get('min', 0) > 0:
                    required_roles += 1
                    if len(role_data.get('who', [])) >= role_data.get('min', 0):
                        filled_roles += 1
            print(f"🔧 All roles filled check: {filled_roles}/{required_roles} required roles filled")
        
        emit('roles_announcement', {'roles_data': roles_data}, room=session_id)
        
        # NEW: Auto-start check for DEBUG_VIS_MODE
        check_auto_start_debug_game(session_id)
    else:
        emit('error', {'message': 'No change made to your roles'})

@socketio.on('game_command', namespace='/session')
def handle_game_command(data):
    """Handle game commands like start, cancel, freeze roles, etc."""
    session_id = data.get('session_id')
    username = data.get('username')
    cmd = data.get('command')
    
    if DEBUG:
        print(f"🔧 GAME_COMMAND received: {cmd} from {username} in session {session_id}")
    
    session = get_session(session_id)
    if not session:
        emit('error', {'message': 'Session not found'})
        return
    
    # Verify user is session owner for certain commands
    session_data = session['SESSION_DATA']
    is_owner = username == session_data['SESSION_OWNER']
    
    if cmd in ['start', 'cancel_game', 'freeze_roles', 'unfreeze_roles'] and not is_owner:
        emit('error', {'message': 'Only session owner can execute this command'})
        return
    
    session_data['USERNAME'] = username
    
    if cmd == 'start':
        if session['GAME_IN_PROGRESS']:
            emit('error', {'message': 'Game already in progress'})
            return
        
        if DEBUG:
            print(f"🔧 BEFORE GAME START: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
        
        # Initialize the problem for this session
        if not initialize_problem_for_session(session_id):
            emit('error', {'message': 'Failed to initialize problem'})
            return
        
        if DEBUG:
            print(f"🔧 AFTER PROBLEM INIT: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
        
        session['GAME_IN_PROGRESS'] = True
        if DEBUG:
            print(f"Game started for session {session_id}, emitting game_started and problem state")
        emit('game_started', room=session_id)
        emit_problem_state(session_id)
        
    elif cmd == 'cancel_game':
        if not session['GAME_IN_PROGRESS']:
            emit('error', {'message': 'No game in progress'})
            return
        
        session['GAME_IN_PROGRESS'] = False
        emit('game_canceled', room=session_id)
        
    elif cmd == 'freeze_roles':
        session['ROLES_FROZEN'] = True
        emit('roles_frozen_status_changed', True, room=session_id)
        
    elif cmd == 'unfreeze_roles':
        session['ROLES_FROZEN'] = False
        emit('roles_frozen_status_changed', False, room=session_id)

def transfer_roles_info_to_select_roles(session_id):
    """Transfer role membership information to Select_Roles module (like old Flask system)"""
    session = get_session(session_id)
    if not session:
        if DEBUG:
            print(f"Error: Session {session_id} not found in transfer_roles_info_to_select_roles")
        return False
    
    try:
        rm = session['SESSION_DATA']['ROLES_MEMBERSHIP']
        if rm is None:
            if DEBUG:
                print("Error: ROLES_MEMBERSHIP is None in transfer_roles_info_to_select_roles")
            return False
        
        # Clear and rebuild the assignments exactly like the old system
        SR.PLAYERS = []  # Override defaults of 2 players and an arbitrary assignment
        SR.ASSIGNMENTS = [[] for i in range(len(rm))]
        
        # Set the ROLES in Select_Roles module (critical!)
        SR.ROLES = ROLES
        if DEBUG:
            print(f"🔧 Set SR.ROLES = {SR.ROLES}")
        
        # Look at all the entries for each role and add each player to PLAYERS, avoiding repeats
        player_num = 0
        if DEBUG:
            print(f"🔧 Transferring role info to Select_Roles for session {session_id}")
            print(f"🔧 ROLES_MEMBERSHIP: {rm}")
        
        for i, r in enumerate(rm):
            for p in r:
                if DEBUG:
                    print(f"🔧 Considering player named '{p}' for role {i}")
                if p not in SR.PLAYERS:
                    SR.PLAYERS.append(p)
                    SR.ASSIGNMENTS[i].append(player_num)
                    if DEBUG:
                        print(f"🔧 Added new player '{p}' as player #{player_num} to role {i}")
                    player_num += 1
                else:
                    pn = SR.PLAYERS.index(p)
                    SR.ASSIGNMENTS[i].append(pn)
                    if DEBUG:
                        print(f"🔧 Assigned existing player '{p}' (#{pn}) to role {i}")
        
        if DEBUG:
            print(f"🔧 Final SR.PLAYERS: {SR.PLAYERS}")
            print(f"🔧 Final SR.ASSIGNMENTS: {SR.ASSIGNMENTS}")
        
        return True
        
    except Exception as e:
        if DEBUG:
            print(f"Error in transfer_roles_info_to_select_roles for session {session_id}: {e}")
            traceback.print_exc()
        return False

def initialize_problem_for_session(session_id):
    """Initialize the problem formulation for a specific session"""
    session = get_session(session_id)
    if not session:
        return False
    
    if DEBUG:
        print(f"🔧 INITIALIZE_PROBLEM START: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
    
    try:
        # Set the session data for the problem formulation
        PROBLEM.SESSION = session['SESSION_DATA']
        
        # Initialize roles membership first
        try: 
          initialize_roles_membership(session_id)
          if DEBUG:
              print(f"🔧 AFTER initialize_roles_membership: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
        except Exception as e_irm:
          print(f"Error initializing roles membership: {e_irm}")  
          traceback.print_exc()
          return False
        
        # Transfer role info to Select_Roles module (critical for games like OCCLUEdo)
        try:
          if not transfer_roles_info_to_select_roles(session_id):
              print(f"Error transferring roles info to Select_Roles for session {session_id}")
              return False
          if DEBUG:
              print(f"🔧 AFTER transfer_roles_info_to_select_roles: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
        except Exception as e_tri:
          print(f"Error in transfer_roles_info_to_select_roles: {e_tri}")
          traceback.print_exc()
          return False
        
        # Create initial state (after role info is transferred)
        try: 
          initial_state = PROBLEM.create_initial_state()
          session['GAME_STATE'] = initial_state
          if DEBUG:
              print(f"🔧 AFTER create_initial_state: ROLES_MEMBERSHIP = {session['SESSION_DATA']['ROLES_MEMBERSHIP']}")
        except Exception as e_cis:
          print(f"Error creating initial state: {e_cis}")
          traceback.print_exc()
          return False
        
        return True
    except Exception as e:
        if DEBUG:
            print(f"Error initializing problem for session {session_id}: {e}")
        return False

def emit_problem_state(session_id, use_socketio_emit=False):
    """Emit the current problem state to all users in a session
    
    Args:
        session_id: The session ID to emit state for
        use_socketio_emit: If True, use socketio.emit (for calls outside event handlers)
                          If False, use emit (for calls inside event handlers)
    """
    session = get_session(session_id)
    if not session or not session['GAME_STATE']:
        return
    
    # Helper function to choose the right emit method
    def smart_emit(event, data, room=None):
        if use_socketio_emit:
            socketio.emit(event, data, room=room, namespace='/session')
        else:
            emit(event, data, room=room)
    
    current_state = session['GAME_STATE']
    current_role_num = getattr(current_state, 'current_role_num', 0)
    current_role = getattr(current_state, 'current_role', 'Unknown')
    whose_turn = getattr(current_state, 'whose_turn', -1)
    
    if DEBUG:
        print(f"=== EMIT_PROBLEM_STATE DEBUG ===")
        print(f"Current state whose_turn: {whose_turn}")
        print(f"Current state current_role_num: {current_role_num}")
        print(f"Current state current_role: {current_role}")
    
    # Flag to track if we successfully sent individual state updates
    sent_individual_updates = False
    successful_individual_updates = 0
    
    # Generate role-specific SVG visualization for each user
    try:
        if hasattr(PROBLEM, 'BRIFL_SVG') and PROBLEM.BRIFL_SVG and hasattr(PROBLEM, 'render_state'):
            session_data = session['SESSION_DATA']
            usernames_dict = session_data.get('USERNAMES', {})
            
            if DEBUG:
                print(f"🔧 Generating role-specific SVGs for {len(usernames_dict)} users")
            
            # Generate and send individual SVGs for each user based on their roles
            for user_num, username in usernames_dict.items():
                try:
                    user_roles = get_roles_for_user(session_id, username)
                    
                    if DEBUG:
                        print(f"🔧 DEBUG: User {username} has roles: {user_roles}")
                        print(f"🔧 DEBUG: ROLES_MEMBERSHIP for session: {session_data.get('ROLES_MEMBERSHIP')}")
                    
                    # Set session context for this specific user
                    PROBLEM.SESSION = session_data
                    PROBLEM.SESSION['USERNAME'] = username
                    
                    # Generate role-specific SVG for this user (use roles= keyword argument like old system)
                    user_svg = PROBLEM.render_state(current_state, roles=user_roles)
                    
                    if DEBUG:
                        print(f"🔧 Generated {len(user_svg) if user_svg else 0} char SVG for {username} with roles {user_roles}")
                        if not user_roles:
                            print(f"🔧 WARNING: User {username} has no roles assigned - will show 'no role' message")
                    
                    # Create user-specific state update
                    state_update_data = {
                        'whose_turn': current_role,
                        'current_role_num': current_role_num,
                        'is_goal': current_state.is_goal() if hasattr(current_state, 'is_goal') else False
                    }
                    
                    # Include user-specific SVG or fallback to text
                    if user_svg:
                        state_update_data['state_svg'] = user_svg
                    else:
                        state_update_data['current_state'] = str(current_state)
                        if DEBUG:
                            print(f"🔧 No SVG generated for {username}, using text state")
                    
                    # Always include text state in debug mode
                    session_debug_mode = session.get('DEBUG_MODE', False)
                    if session_debug_mode:
                        state_update_data['current_state'] = str(current_state)
                    
                    # Send to this specific user
                    state_update_data['for_user'] = username
                    smart_emit('state_update', state_update_data, room=session_id)
                    successful_individual_updates += 1
                    
                    if DEBUG:
                        print(f"🔧 Sent role-specific state update to {username}")
                        
                except Exception as e:
                    if DEBUG:
                        print(f"Error generating individual state for user {username}: {e}")
            
            # Continue with operator processing
            if DEBUG:
                print(f"Checking operators for {len(usernames_dict)} users in session")
            
            # Collect and send operators for each user
            all_user_operators = {}
            for user_num, username in usernames_dict.items():
                try:
                    user_roles = get_roles_for_user(session_id, username)
                    if DEBUG:
                        print(f"User {username} has roles {user_roles}, current turn role is {current_role_num}")
                    
                    # Get operators for this user
                    applicable_ops = []
                    user_can_act = False
                    
                    # Check if user can act (either their turn in turn-based game, or has role in simple game)
                    if hasattr(current_state, 'current_role_num'):
                        # Turn-based game
                        user_can_act = current_role_num in user_roles
                        if DEBUG:
                            print(f"Turn-based game: {username} can act = {user_can_act} (role {current_role_num} in {user_roles})")
                    else:
                        # Simple game without turns
                        user_can_act = bool(user_roles)
                        if DEBUG:
                            print(f"Simple game: {username} can act = {user_can_act} (has roles: {user_roles})")
                    
                    if user_can_act:
                        if DEBUG:
                            print(f"Getting operators for {username}")
                        
                        # Set session context
                        PROBLEM.SESSION = session['SESSION_DATA']
                        PROBLEM.SESSION['USERNAME'] = username
                        
                        for i, op in enumerate(PROBLEM.OPERATORS):
                            try:
                                if op.is_applicable(current_state):
                                    applicable_ops.append({
                                        'index': i,
                                        'description': op.name,
                                        'is_applicable': True
                                    })
                                    if DEBUG:
                                        print(f"Operator {i} ({op.name}) is applicable for {username}")
                            except Exception as e:
                                if DEBUG:
                                    print(f"Error checking operator {i}: {e}")
                    else:
                        if DEBUG:
                            print(f"No operators for {username} (cannot act)")
                    
                    all_user_operators[username] = applicable_ops
                    if DEBUG:
                        print(f"User {username} gets {len(applicable_ops)} operators")
                except Exception as e:
                    if DEBUG:
                        print(f"Error getting operators for user {username}: {e}")
                    all_user_operators[username] = []
            
            # Send operators to each user individually
            for username, operators in all_user_operators.items():
                try:
                    smart_emit('operators_list', {
                        'operators': operators, 
                        'for_user': username
                    }, room=session_id)
                    if DEBUG:
                        print(f"Emitted {len(operators)} operators for user {username}")
                except Exception as e:
                    if DEBUG:
                        print(f"Error emitting operators for user {username}: {e}")
            
            # Mark that we attempted individual updates
            sent_individual_updates = successful_individual_updates > 0
            
    except Exception as e:
        if DEBUG:
            print(f"Error in role-specific rendering for session {session_id}: {e}")
        sent_individual_updates = False
    
    # Only send a general fallback if NO individual updates were sent successfully
    if successful_individual_updates == 0:
        if DEBUG:
            print(f"🔧 No individual updates sent - sending fallback general state update")
        
        state_update_data = {
            'whose_turn': current_role,
            'current_role_num': current_role_num,
            'is_goal': current_state.is_goal() if hasattr(current_state, 'is_goal') else False,
            'current_state': str(current_state)
        }
        
        # Try to get a general SVG (not role-specific)
        try:
            if hasattr(PROBLEM, 'BRIFL_SVG') and PROBLEM.BRIFL_SVG and hasattr(PROBLEM, 'render_state'):
                general_svg = PROBLEM.render_state(current_state)
                if general_svg:
                    state_update_data['state_svg'] = general_svg
                    if DEBUG:
                        print(f"🔧 Generated fallback general SVG ({len(general_svg)} chars)")
        except Exception as e:
            if DEBUG:
                print(f"Error generating general SVG: {e}")
        
        # Send general update WITHOUT for_user field so all users receive it
        smart_emit('state_update', state_update_data, room=session_id)
        if DEBUG:
            print(f"🔧 Emitted fallback general state update for session {session_id}")
    else:
        if DEBUG:
            print(f"🔧 Successfully sent {successful_individual_updates} individual updates - skipping general fallback")
    
    if DEBUG:
        print(f"Emitted state update for session {session_id}, current turn: {current_role} (role {current_role_num})")

def handle_get_operators_for_user(session_id, username):
    """Internal function to get operators for a specific user"""
    session = get_session(session_id)
    if not session or not session['GAME_IN_PROGRESS']:
        return
    
    current_state = session['GAME_STATE']
    if not current_state:
        return
    
    user_roles = get_roles_for_user(session_id, username)
    current_role_num = getattr(current_state, 'current_role_num', 0)
    
    # Get applicable operators
    applicable_ops = []
    PROBLEM.SESSION = session['SESSION_DATA']
    PROBLEM.SESSION['USERNAME'] = username
    
    # Check if it's this user's turn
    if current_role_num in user_roles:
        if DEBUG:
            print(f"It's {username}'s turn (role {current_role_num}), getting operators")
        # User's turn - get applicable operators
        print(f"DEBUG: Getting operators for {username}, total operators: {len(PROBLEM.OPERATORS)}")
        for i, op in enumerate(PROBLEM.OPERATORS):
            try:
                if op.is_applicable(current_state):
                    has_params = bool(hasattr(op, 'params') and op.params)
                    if DEBUG:
                        print(f"Operator {i}: {op.name}")
                        print(f"  hasattr(op, 'params'): {hasattr(op, 'params')}")
                        print(f"  op.params: {getattr(op, 'params', 'MISSING')}")
                        print(f"  has_params: {has_params}")
                    applicable_ops.append({
                        'index': i,
                        'description': op.get_name(current_state) if hasattr(op, 'get_name') else op.name,
                        'is_applicable': True,
                        'has_params': has_params
                    })
            except Exception as e:
                if DEBUG:
                    print(f"Error checking operator {i}: {e}")
    else:
        if DEBUG:
            print(f"NOT {username}'s turn - current role is {current_role_num}, user has roles {user_roles}")
    
    # We need to send to this specific user, but we don't have their socket ID
    # For now, emit to the whole room but the frontend should filter
    emit('operators_list', {'operators': applicable_ops, 'for_user': username}, room=session_id)
    
    if DEBUG:
        print(f"Sent {len(applicable_ops)} operators for user {username} in session {session_id}")

@socketio.on('get_operator_params', namespace='/session')
def handle_get_operator_params(data):
    """Get parameter specifications for a parameterized operator"""
    session_id = data.get('session_id')
    username = data.get('username')
    operator_index = data.get('operator_index')
    
    session = get_session(session_id)
    if not session or not session['GAME_IN_PROGRESS']:
        emit('error', {'message': 'No game in progress'})
        return
    
    current_state = session['GAME_STATE']
    if not current_state:
        emit('error', {'message': 'No current state found'})
        return
    
    try:
        # Get the operator
        if operator_index >= len(PROBLEM.OPERATORS):
            emit('error', {'message': 'Invalid operator'})
            return
        
        operator = PROBLEM.OPERATORS[operator_index]
        
        # Check if operator has parameters
        has_params_attr = hasattr(operator, 'params')
        params_value = getattr(operator, 'params', None)
        
        if not has_params_attr or not params_value:
            emit('error', {'message': 'Operator has no parameters'})
            return
        
        # Get parameter specifications
        param_specs = operator.params
        
        # If params is a function, evaluate it with current state
        if callable(param_specs):
            param_specs = param_specs(current_state)
        
        # Send parameter specifications to client
        response_data = {
            'operator_index': operator_index,
            'operator_name': operator.get_name(current_state) if hasattr(operator, 'get_name') else operator.name,
            'params': param_specs
        }
        emit('operator_params', response_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        emit('error', {'message': f'Error getting operator parameters: {str(e)}'})

@socketio.on('operator_request', namespace='/session')
def handle_operator_request(data):
    """Handle user requesting to apply an operator"""
    session_id = data.get('session_id')
    username = data.get('username')
    operator_index = data.get('operator_index')
    params = data.get('params', [])
    
    session = get_session(session_id)
    if not session or not session['GAME_IN_PROGRESS']:
        emit('error', {'message': 'No game in progress'})
        return
    
    current_state = session['GAME_STATE']
    if not current_state:
        emit('error', {'message': 'No current state found'})
        return
    
    # Verify user can act
    user_roles = get_roles_for_user(session_id, username)
    current_role_num = getattr(current_state, 'current_role_num', 0)
    
    # Check if user can act (either their turn in turn-based game, or has role in simple game)
    user_can_act = False
    if hasattr(current_state, 'current_role_num'):
        # Turn-based game
        user_can_act = current_role_num in user_roles
        if not user_can_act:
            emit('error', {'message': 'Not your turn'})
            return
    else:
        # Simple game without turns
        user_can_act = bool(user_roles)
        if not user_can_act:
            emit('error', {'message': 'You must have a role to make moves'})
            return
    
    try:
        # Get the operator
        if operator_index >= len(PROBLEM.OPERATORS):
            emit('error', {'message': 'Invalid operator'})
            return
        
        operator = PROBLEM.OPERATORS[operator_index]
        
        # Check preconditions
        if not operator.is_applicable(current_state):
            emit('error', {'message': 'Operator not applicable'})
            return
        
        # Store previous state for "show previous state" feature
        session['PREVIOUS_STATE'] = copy.deepcopy(current_state)
        
        print(f"DEBUG: Before applying operator, current_state.whose_turn = {current_state.whose_turn}")
        # Apply the operator (with parameters if provided)
        try:
            if hasattr(operator, 'params') and operator.params:
                # Parameterized operator
                if not params:
                    emit('error', {'message': 'Parameterized operator requires parameters'})
                    return
                # Apply operator with parameters
                new_state = operator.transf(current_state, params)
            else:
                # Regular operator
                new_state = operator.apply(current_state)
        except Exception as e:
            # Operator application failed - send error with retry option
            error_message = f"Operator failed: {str(e)}"
            if hasattr(operator, 'params') and operator.params:
                # For parameterized operators, offer retry
                emit('operator_error', {
                    'message': error_message,
                    'operator_index': operator_index,
                    'can_retry': True
                })
            else:
                # For regular operators, just send error
                emit('error', {'message': error_message})
            return
        session['GAME_STATE'] = new_state
        
        if DEBUG:
            print(f"=== OPERATOR APPLIED ===")
            print(f"Old state whose_turn: {getattr(current_state, 'whose_turn', 'N/A')}")
            print(f"New state whose_turn: {getattr(new_state, 'whose_turn', 'N/A')}")
            print(f"New state current_role_num: {getattr(new_state, 'current_role_num', 'N/A')}")
            print(f"New state current_role: {getattr(new_state, 'current_role', 'N/A')}")
        
        # Process transitions
        process_transition(session_id, current_state, new_state, operator)
        
        # Emit the new state
        emit_problem_state(session_id)
        
        # Check for goal state
        if hasattr(new_state, 'is_goal') and new_state.is_goal():
            if DEBUG:
                print(f"=== GOAL STATE DETECTED ===")
                print(f"State is goal: {new_state.is_goal()}")
                print(f"State win: {getattr(new_state, 'win', 'N/A')}")
                print(f"State winner: {getattr(new_state, 'winner', 'N/A')}")
            
            goal_message = getattr(new_state, 'goal_message', lambda: 'Game completed!')()
            
            # Handle case where goal_message returns None (e.g., for draws)
            if not goal_message:
                if hasattr(new_state, 'moves_left') and not new_state.moves_left():
                    # Use the actual problem name from the formulation
                    problem_name = getattr(PROBLEM, 'PROBLEM_NAME', formulation_name)
                    goal_message = f"It's a draw! Thanks for playing {problem_name}."
                else:
                    goal_message = "Game completed!"
            
            if DEBUG:
                print(f"Goal message: {goal_message}")
            
            emit('game_completed', {'message': goal_message}, room=session_id)
            session['GAME_IN_PROGRESS'] = False
            
            if DEBUG:
                print(f"Emitted game_completed to session {session_id}")
        
    except Exception as e:
        if DEBUG:
            print(f"Error applying operator in session {session_id}: {e}")
        emit('error', {'message': 'Error applying operator'})

def process_transition(session_id, old_state, new_state, operator):
    """Process transition messages for state changes"""
    session = get_session(session_id)
    if not session:
        return
    
    try:
        # First check if the new state has a jit_transition property (simpler approach)
        if hasattr(new_state, 'jit_transition'):
            transition_entry = {
                'message': new_state.jit_transition.strip(),
                'timestamp': time.time(),
                'options': {}
            }
            session['TRANSITION_HISTORY'].append(transition_entry)
            
            # Emit transition
            emit('transition', transition_entry, room=session_id)
            if DEBUG:
                print(f"Emitted jit_transition: {transition_entry['message']}")
            return
        
        # Fall back to TRANSITIONS approach (more complex, condition-based)
        transitions = getattr(PROBLEM, 'TRANSITIONS', [])
        for condition, action, options in transitions:
            if condition(old_state, new_state, operator):
                if callable(action):
                    action = action(old_state, new_state, operator)
                
                # Add to transition history
                transition_entry = {
                    'message': action,
                    'timestamp': time.time(),
                    'options': options
                }
                session['TRANSITION_HISTORY'].append(transition_entry)
                
                # Emit transition
                emit('transition', transition_entry, room=session_id)
                if DEBUG:
                    print(f"Emitted TRANSITIONS-based transition: {action}")
                break
    except Exception as e:
        if DEBUG:
            print(f"Error processing transition: {e}")

@socketio.on('disconnect', namespace='/session')
def handle_disconnect():
    """Handle user disconnecting"""
    if DEBUG:
        print(f'Client disconnected: {request.sid}')
    
    # Note: In a production system, you might want to handle
    # removing users from sessions when they disconnect
    # For now, we'll keep sessions alive as per requirements

# Additional features for enhanced requirements

@socketio.on('get_operators', namespace='/session')
def handle_get_operators(data):
    """Get available operators for current user/state"""
    session_id = data.get('session_id')
    username = data.get('username')
    
    if DEBUG:
        print(f"=== GET_OPERATORS called by {username} for session {session_id} ===")
    
    session = get_session(session_id)
    if not session:
        if DEBUG:
            print(f"Session {session_id} not found")
        emit('operators_list', {'operators': []})
        return
        
    if not session['GAME_IN_PROGRESS']:
        if DEBUG:
            print(f"Game not in progress for session {session_id}")
        emit('operators_list', {'operators': []})
        return
    
    current_state = session['GAME_STATE']
    if not current_state:
        emit('operators_list', {'operators': []})
        return
    
    user_roles = get_roles_for_user(session_id, username)
    current_role_num = getattr(current_state, 'current_role_num', 0)
    
    if DEBUG:
        print(f"User {username} has roles {user_roles}, current turn is role {current_role_num}")
    
    # Check if it's this user's turn
    # For simple games without turn management, allow operators if user has any role
    if hasattr(current_state, 'current_role_num'):
        # This is a turn-based game, check specific role
        if current_role_num not in user_roles:
            emit('operators_list', {'operators': []})
            if DEBUG:
                print(f"Not {username}'s turn - current role {current_role_num} not in user roles {user_roles}")
            return
    else:
        # This is a simple game without turn management, allow if user has any role
        if not user_roles:
            emit('operators_list', {'operators': []})
            if DEBUG:
                print(f"User {username} has no roles, cannot get operators")
            return
        if DEBUG:
            print(f"Simple game mode - allowing operators for any role holder")
    
    # Get applicable operators for the current role
    applicable_ops = []
    
    # Set the session data for the problem formulation so operators can check roles
    PROBLEM.SESSION = session['SESSION_DATA']
    PROBLEM.SESSION['USERNAME'] = username
    
    for i, op in enumerate(PROBLEM.OPERATORS):
        try:
            if op.is_applicable(current_state):
                applicable_ops.append({
                    'index': i,
                    'description': op.get_name(current_state) if hasattr(op, 'get_name') else op.name,
                    'is_applicable': True,
                    'has_params': bool(hasattr(op, 'params') and op.params)
                })
                if DEBUG:
                    print(f"Operator {i} ({op.name}) is applicable")
            else:
                if DEBUG:
                    print(f"Operator {i} ({op.name}) is NOT applicable")
        except Exception as e:
            if DEBUG:
                print(f"Error checking precondition for operator {i}: {e}")
    
    if DEBUG:
        print(f"Sending {len(applicable_ops)} operators to user {username}")
    
    emit('operators_list', {'operators': applicable_ops, 'for_user': username})

@socketio.on('get_previous_state', namespace='/session')
def handle_get_previous_state(data):
    """Get previous state for 'show previous state' feature"""
    session_id = data.get('session_id')
    
    session = get_session(session_id)
    if not session or not session.get('PREVIOUS_STATE'):
        emit('previous_state', {'has_previous': False})
        return
    
    previous_state = session['PREVIOUS_STATE']
    username = data.get('username')
    user_roles = get_roles_for_user(session_id, username)
    
    try:
        if hasattr(PROBLEM, 'BRIFL_SVG') and PROBLEM.BRIFL_SVG:
            previous_svg = PROBLEM.render_state(previous_state, user_roles)
            emit('previous_state', {
                'has_previous': True,
                'state_svg': previous_svg,
                'state_text': str(previous_state)
            })
        else:
            emit('previous_state', {
                'has_previous': True,
                'state_text': str(previous_state)
            })
    except Exception as e:
        if DEBUG:
            print(f"Error getting previous state: {e}")
        emit('previous_state', {'has_previous': False})

@socketio.on('get_transition_history', namespace='/session')
def handle_get_transition_history(data):
    """Get transition message history for a session"""
    session_id = data.get('session_id')
    
    session = get_session(session_id)
    if not session:
        emit('transition_history', {'history': []})
        return
    
    emit('transition_history', {'history': session['TRANSITION_HISTORY']})

def open_browser_url(url):
    """Smart browser opening that works in WSL and regular Linux - prioritizes wslview"""
    try:
        # First, try wslview if available (best option for WSL)
        try:
            subprocess.run(['wslview', url], check=True, capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        
        # Check if we're in WSL (Windows Subsystem for Linux)
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    # We're in WSL - try other Windows methods
                    wsl_methods = [
                        # Method 1: Use powershell to start the URL
                        ['powershell.exe', '-Command', f'Start-Process "{url}"'],
                        # Method 2: Use cmd with proper URL handling
                        ['cmd.exe', '/c', 'start', '""', url],
                        # Method 3: Use explorer.exe to open URL
                        ['explorer.exe', url]
                    ]
                    
                    for method in wsl_methods:
                        try:
                            subprocess.run(method, check=True, capture_output=True, timeout=5)
                            return True
                        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                            continue
        
        # Try standard webbrowser module (for regular Linux/macOS)
        try:
            webbrowser.open_new_tab(url)
            return True
        except:
            pass
        
        # Fallback: try common browsers directly
        browsers = [
            'google-chrome', 'chromium-browser', 'firefox', 
            'microsoft-edge', 'brave-browser'
        ]
        
        for browser in browsers:
            try:
                subprocess.run([browser, url], check=True, capture_output=True, timeout=5)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
        
        return False
        
    except Exception as e:
        if DEBUG:
            print(f"⚠️ Error opening browser: {e}")
        return False

def setup_visualization_debugging():
    """Set up visualization debugging mode - auto-launch browser tabs"""
    global DEBUG_VIS_MODE, DEBUG_BROWSERS_LAUNCHED, DEBUG_SESSION_ID
    
    # Prevent multiple launches
    if DEBUG_BROWSERS_LAUNCHED:
        print("🔧 Debug browsers already launched, skipping...")
        return
    
    DEBUG_VIS_MODE = True
    DEBUG_BROWSERS_LAUNCHED = True
    
    def launch_debug_browsers():
        # Wait a moment for the server to fully start
        time.sleep(3)
        
        global DEBUG_SESSION_ID
        
        try:
            # No longer create session here - Player 1 will create it via JavaScript automation
            print("🔧 Session creation now handled by Player 1's browser automation")
            
            # Launch browser tabs for each role using new index.html approach
            base_url = f'http://{HOST}:{PORT}/'
            
            # Only open exactly the number of roles we have - no more, no less
            print(f"🔧 Opening browser tabs for {len(ROLES)} roles (ONE TIME ONLY)...")
            
            successful_opens = 0
            for i in range(len(ROLES)):  # Use range to prevent any issues
                if i >= len(ROLES):  # Safety check
                    break
                    
                role = ROLES[i]
                player_name = f"Player {i + 1}"
                role_name = role['name']
                
                # Build URL with new debug parameters
                debug_url = f"{base_url}?debug=true&player={player_name}&role={i}"
                
                print(f"🔧 Opening tab {i+1}/{len(ROLES)}: {player_name} -> Role {i} ({role_name})")
                
                # Try to open browser tab using wslview (should work reliably now)
                try:
                    if open_browser_url(debug_url):
                        successful_opens += 1
                        print(f"   ✅ Successfully opened tab for {player_name}")
                    else:
                        print(f"   ❌ Failed to open tab for {player_name}")
                        print(f"   📋 Manual URL: {debug_url}")
                except Exception as e:
                    print(f"   ❌ Error opening tab for {player_name}: {e}")
                    print(f"   📋 Manual URL: {debug_url}")
                
                # Longer delay between opening tabs to ensure proper session coordination
                # Player 1 needs time to create session before Player 2 looks for it
                if i == 0:
                    time.sleep(3.0)  # Give Player 1 extra time to create session
                else:
                    time.sleep(2.0)  # Standard delay for other players
            
            if successful_opens > 0:
                print(f"🔧 Visualization debugging mode setup complete! ({successful_opens}/{len(ROLES)} tabs opened)")
                print("🔧 Browser tabs should automatically join roles and start the game.")
                if successful_opens < len(ROLES):
                    print("🔧 Some tabs failed to open. Manual URLs for failed tabs:")
                    print("-" * 60)
                    for i, role in enumerate(ROLES):
                        player_name = f"Player {i + 1}"
                        role_name = role['name']
                        debug_url = f"{base_url}?player={player_name}&session_id={debug_session_id}&role={i}"
                        print(f"Tab {i+1}: {debug_url}")
                        print(f"   -> {player_name} as {role_name}")
                    print("-" * 60)
            else:
                print("🔧 Could not auto-open any browsers. Here are the URLs to open manually:")
                print("=" * 85)
                print(f"Debug Session ID: {debug_session_id}")
                print("=" * 85)
                for i in range(len(ROLES)):
                    player_name = f"Player {i + 1}"
                    role_name = ROLES[i]['name']
                    debug_url = f"{base_url}?player={player_name}&session_id={debug_session_id}&role={i}"
                    print(f"Tab {i+1}: {debug_url}")
                    print(f"   -> {player_name} will join {role_name} role")
                print("=" * 85)
                print("🔧 Copy and paste each URL into separate browser tabs to test debug mode.")
            
        except Exception as e:
            print(f"❌ Error setting up visualization debugging: {e}")
    
    # Launch browsers in a separate thread so it doesn't block the server
    print("🔧 Starting debug browser launcher thread...")
    browser_thread = threading.Thread(target=launch_debug_browsers, daemon=True)
    browser_thread.start()

# Load problem formulation and handle command line arguments
def load_problem_formulation():
    """Load the problem formulation from command line argument"""
    global PROBLEM, ROLES, THE_DIR
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python Web_SZ5_01.py <problem_formulation> [port]")
        print("Example: python Web_SZ5_01.py Tic_Tac_Toe 5000")
        sys.exit(1)
    
    global formulation_name
    formulation_name = sys.argv[1]
    
    # Set custom port if provided
    global PORT
    if len(sys.argv) > 2:
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number: {sys.argv[2]}")
            sys.exit(1)
    
    # Set the directory for the problem formulation
    import os
    web_soluzion_path = os.path.join(os.path.dirname(os.getcwd()), 'Web_SOLUZION5')
    THE_DIR = os.path.join(web_soluzion_path, formulation_name)
    
    if not os.path.exists(THE_DIR):
        print(f"Problem formulation directory not found: {THE_DIR}")
        sys.exit(1)
    
    # Add the formulation directory to Python path
    sys.path.insert(0, THE_DIR)
    
    try:
        # Import the problem formulation
        PROBLEM = __import__(formulation_name)
        
        # Debug: Check operators and their parameters
        print(f"DEBUG: Loaded {formulation_name}, found {len(PROBLEM.OPERATORS)} operators:")
        for i, op in enumerate(PROBLEM.OPERATORS):
            print(f"  Operator {i}: {op.name}")
            print(f"    hasattr params: {hasattr(op, 'params')}")
            print(f"    params value: {getattr(op, 'params', 'MISSING')}")
            print(f"    params type: {type(getattr(op, 'params', None))}")
        
        # Get roles information
        if hasattr(PROBLEM, 'ROLES'):
            ROLES = PROBLEM.ROLES
        
        # Initialize SVG visualization if available
        if hasattr(PROBLEM, 'use_BRIFL_SVG'):
            PROBLEM.use_BRIFL_SVG()
            print(f"SVG visualization initialized. BRIFL_SVG = {getattr(PROBLEM, 'BRIFL_SVG', False)}")
            print(f"render_state function available: {hasattr(PROBLEM, 'render_state')}")
        else:
            print("No use_BRIFL_SVG function found")
        
        print(f"Successfully loaded problem formulation: {formulation_name}")
        print(f"Problem description: {getattr(PROBLEM, 'PROBLEM_DESC', 'No description available')}")
        
        # Check for visualization debugging mode (only once per server start)
        if hasattr(PROBLEM, 'DEBUG_VIS') and getattr(PROBLEM, 'DEBUG_VIS', False):
            print("🔧 DEBUG_VIS=True detected - Entering Visualization Debugging Mode")
            # Only call setup once per server instance
            if not DEBUG_BROWSERS_LAUNCHED:
                setup_visualization_debugging()
            else:
                print("🔧 Debug browsers already set up, skipping duplicate setup.")
        
    except ImportError as e:
        print(f"Failed to import problem formulation '{formulation_name}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading problem formulation: {e}")
        sys.exit(1)

def main():
    """Main function to run the server"""
    import sys
    
    load_problem_formulation()
    
    print(f"Starting Web_SZ5_01.py Multi-Session Server")
    print(f"Problem formulation: {sys.argv[1]}")
    print(f"Server will run on {HOST}:{PORT}")
    print(f"Access via browser at: http://{HOST}:{PORT}")
    
    # Disable Flask auto-reloader when in debug visualization mode
    # This prevents duplicate session creation due to Flask restarting
    debug_mode = DEBUG
    use_reloader = True
    
    if DEBUG_VIS_MODE:
        print("🔧 Debug visualization mode active - disabling Flask auto-reloader")
        use_reloader = False
    
    # Run the Flask-SocketIO server
    socketio.run(app, host=HOST, port=PORT, debug=debug_mode, use_reloader=use_reloader, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
