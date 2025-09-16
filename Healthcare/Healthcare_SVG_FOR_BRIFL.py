# Author: Generated for Coverage Clash
# Purpose: Provide the player's "visualizations" of the Coverage Clash healthcare game
# in the web browser using SVG graphics.
# Based on OCCLUEdo_SVG_VIS_FOR_BRIFL.py structure

import svgwrite
import Healthcare as prob  # Import the main game module

DEBUG = True
W = 1000  # Width of visualization region
H = 620  # Increased height to accommodate larger cards
PANEL_WIDTH = W // 3
PANEL_HEIGHT = H // 2

# Color scheme for healthcare theme
ROLE_COLORS = [
    "rgb(70, 130, 180)",   # Steel Blue for Policy Maker
    "rgb(220, 20, 60)",    # Crimson for Insurance Company
    "rgb(128, 128, 128)"   # Gray for observers
]

BACKGROUND_COLOR = "rgb(245, 248, 250)"  # Light medical blue-gray
ACCENT_COLOR = "rgb(25, 135, 84)"        # Medical green
WARNING_COLOR = "rgb(220, 53, 69)"       # Medical red
SUCCESS_COLOR = "rgb(40, 167, 69)"       # Success green

# Font sizes
LARGE_FS = "24"
MEDIUM_FS = "18"
SMALL_FS = "14"
TINY_FS = "12"

session = None

def render_state(s, roles=None):
    global session
    if DEBUG: print("In Coverage_SVG.py, roles = "+str(roles))

    # Accessibility text
    alt_text = "Coverage Clash game state visualization for "
    
    session = prob.SESSION
    
    dwg = svgwrite.Drawing(filename="coverage_clash_vis.svg",
                          id="state_svg",
                          size=(str(W)+"px", str(H)+"px"),
                          debug=True)
    
    # Background
    dwg.add(dwg.rect(insert=(0,0),
                    size=(str(W)+"px", str(H)+"px"),
                    fill=BACKGROUND_COLOR,
                    stroke="none"))
    
    if roles is None or roles == []:
        # No role assigned
        label = "Observer View - No Active Role"
        dwg.add(dwg.text(label, insert=(W//2, H//2),
                        text_anchor="middle",
                        font_size=LARGE_FS,
                        fill=WARNING_COLOR))
        alt_text += "observer with no active role"
    else:
        # Determine current role to display
        if s.current_role_num in roles:
            role = s.current_role_num
        else:
            role = roles[0]
        
        alt_text += prob.int_to_name(role)
        
        # Main title
        title = f"Coverage Clash - {prob.int_to_name(role)} View"
        dwg.add(dwg.text(title, insert=(W//2, 30),
                        text_anchor="middle",
                        font_size=LARGE_FS,
                        fill="rgb(51, 51, 51)",
                        font_weight="bold"))
        
        # Current turn indicator
        current_player = prob.int_to_name(s.whose_turn)
        turn_text = f"Current Turn: {current_player}"
        if s.whose_turn == role:
            turn_text += " (YOUR TURN)"
            turn_color = SUCCESS_COLOR
        else:
            turn_color = "rgb(108, 117, 125)"
        
        dwg.add(dwg.text(turn_text, insert=(W//2, 55),
                        text_anchor="middle",
                        font_size=MEDIUM_FS,
                        fill=turn_color))
        
        # Draw main dashboard panels - removed metrics panel, expanded status
        draw_goals_panel(dwg, s, role, 20, 80)
        draw_status_panel(dwg, s, 350, 80)  # Expanded status panel
        
        # Draw progress bars with extra metrics
        draw_progress_bars(dwg, s, 35, 350)
        
        
        
        if role == prob.POLICY_MAKER:
            r_insert(dwg)
        elif role == prob.INSURANCE_COMPANY:
            i_insert(dwg)
        else:
            if s.whose_turn == prob.POLICY_MAKER:
                r_insert(dwg)
            else:
                i_insert(dwg)
        
        # Win/lose status
        if s.win:
            draw_game_over(dwg, s)
    
    dwg.add(svgwrite.base.Title(alt_text))
    svg_string = dwg.tostring()
    return svg_string

def draw_goals_panel(dwg, s, role, x, y):
    """Draw the goals and win conditions panel"""
    panel_width = 320
    panel_height = 210

    # Panel background
    dwg.add(dwg.rect(insert=(x, y),
        size=(panel_width, panel_height),
        fill="white",
        stroke="rgb(200, 200, 200)",
        stroke_width="1",
        rx="5"))

    # Panel title
    role_name = prob.int_to_name(role)
    dwg.add(dwg.text(f"{role_name} Goals", insert=(x + panel_width//2, y + 20),
        text_anchor="middle",
        font_size=MEDIUM_FS,
        font_weight="bold",
        fill=ROLE_COLORS[role]))

    y_offset = 45

    if role == prob.POLICY_MAKER:
        goals = [
            ("WIN CONDITION:", ""),
            ("Access Gap < 13", f"(currently {s.access_gap_index})", SUCCESS_COLOR if s.access_gap_index < 12 else WARNING_COLOR),
            ("", ""),
            ("AVOID LOSING:", ""),
            ("Uninsured > 17.8%", f"(currently {s.uninsured_rate:.1f}%)", WARNING_COLOR if s.uninsured_rate > 15.5 else SUCCESS_COLOR),
            ("Public Health Index < 30", f"(currently {s.public_health_index})", WARNING_COLOR if s.public_health_index < 40 else SUCCESS_COLOR),
            ("Access Gap Index > 45", f"(currently {s.access_gap_index})", WARNING_COLOR if s.access_gap_index > 40 else SUCCESS_COLOR),
            ("Public Trust Meter < 30%", f"(currently {s.public_trust_meter}%)", WARNING_COLOR if s.public_trust_meter < 37 else SUCCESS_COLOR),
            ("Insurer Profit > $85B", f"", WARNING_COLOR if s.profit > 78 else SUCCESS_COLOR),
            ("(Insurer wins)", f"(currently ${s.profit}B)", WARNING_COLOR if s.profit > 78 else SUCCESS_COLOR)
        ]
    elif role == prob.INSURANCE_COMPANY:
        goals = [
            ("WIN CONDITION:", ""),
            ("Profit > $85B", f"(currently ${s.profit}B)", SUCCESS_COLOR if s.profit > 80 else WARNING_COLOR),
            ("Access Gap > 45", f"", SUCCESS_COLOR if s.access_gap_index > 40 else WARNING_COLOR),
            ("(Policymaker loses)", f"(currently {s.access_gap_index})", SUCCESS_COLOR if s.access_gap_index > 40 else WARNING_COLOR),
            ("", ""),
            ("AVOID LOSING:", ""),
            ("Uninsured > 14%", f"(currently {s.uninsured_rate:.1f}%)", WARNING_COLOR if s.uninsured_rate > 12 else SUCCESS_COLOR),
            ("Public Health < 30", f"(currently {s.public_health_index})", WARNING_COLOR if s.public_health_index < 40 else SUCCESS_COLOR)
        ]
    else:
        goals = [("Observer", "No specific goals", "rgb(108, 117, 125)")]

    for goal_item in goals:
        if len(goal_item) == 3:
            label, value, color = goal_item
        else:
            label, value, color = goal_item[0], goal_item[1], "rgb(51, 51, 51)"
        if label == "":
            y_offset += 10
            continue
        dwg.add(dwg.text(label, insert=(x + 10, y + y_offset),
            font_size=SMALL_FS,
            fill="rgb(51, 51, 51)" if color == "" else color,
            font_weight="bold" if "CONDITION" in label or "LOSING" in label else "normal"))
        if value:
            dwg.add(dwg.text(value, insert=(x + panel_width - 10, y + y_offset),
                text_anchor="end",
                font_size=SMALL_FS,
                fill=color))
        y_offset += 18

def draw_status_panel(dwg, s, x, y):
    """Draw current status and special conditions panel with extra metrics"""
    panel_width = 260
    panel_height = 260
    
    # Panel background
    dwg.add(dwg.rect(insert=(x, y),
                    size=(panel_width, panel_height),
                    fill="white",
                    stroke="rgb(200, 200, 200)",
                    stroke_width="1",
                    rx="5"))
    
    # Panel title
    dwg.add(dwg.text("Current Status & Metrics", insert=(x + panel_width//2, y + 20),
                    text_anchor="middle",
                    font_size=MEDIUM_FS,
                    font_weight="bold",
                    fill="rgb(51, 51, 51)"))
    
    y_offset = 45
    
    # Game metrics that were removed from separate panel - made more compact
    metrics = [
        ("Uninsured Rate", f"{s.uninsured_rate:.1f}%", get_health_color(s.uninsured_rate, 25, True)),
        ("Public Health Index", f"{s.public_health_index}", get_health_color(s.public_health_index, 30, False)),
        ("Access Gap Index", f"{s.access_gap_index}", get_health_color(s.access_gap_index, 50, True)),
        ("Insurance Profit", f"${s.profit}B", "rgb(51, 51, 51)"),
        ("Policy Budget", f"${s.budget}B", get_budget_color(s.budget))
    ]

    for label, value, color in metrics:
        dwg.add(dwg.text(f"{label}:", insert=(x + 10, y + y_offset),
            font_size=SMALL_FS,
            fill="rgb(108, 117, 125)"))
        dwg.add(dwg.text(value, insert=(x + panel_width - 10, y + y_offset),
            text_anchor="end",
            font_size=SMALL_FS,
            font_weight="bold",
            fill=color))
        y_offset += 20  # Reduced spacing
    
    y_offset += 10
    
    # Add warnings section - ensure it stays within bounds
    warnings = []
    if s.uninsured_rate > 20:
        warnings.append("High Uninsured Rate!")
    if s.public_health_index < 40:
        warnings.append("Poor Public Health!")
    if s.budget < 15:
        warnings.append("Low Budget!")
    if s.access_gap_index > 40:
        warnings.append("High Access Gap!")

     # Special conditions
    if s.premium_cap_turns_left > 0:
        dwg.add(dwg.text("Premium Cap Active:", insert=(x + 10, y + y_offset),
                        font_size=SMALL_FS,
                        fill=ACCENT_COLOR,
                        font_weight="bold"))
        dwg.add(dwg.text(f"{s.premium_cap_turns_left} turns left", insert=(x + panel_width - 10, y + y_offset),
                        text_anchor="end",
                        font_size=SMALL_FS,
                        fill=ACCENT_COLOR))
        y_offset += 18
    
    if warnings and y_offset < y + panel_height - 60:  # Check if there's space
        dwg.add(dwg.text("⚠ WARNINGS:", insert=(x + 10, y + y_offset),
                        font_size=SMALL_FS,
                        fill=WARNING_COLOR,
                        font_weight="bold"))
        y_offset += 16
        for warning in warnings:
            if y_offset < y + panel_height - 20:  # Ensure each warning fits
                dwg.add(dwg.text(f"• {warning}", insert=(x + 20, y + y_offset),
                                font_size=SMALL_FS,
                                fill=WARNING_COLOR))
                y_offset += 14  # Reduced spacing
        y_offset += 5  # Add some spacing after warnings

    messages = []
    if s.access_gap_index < 20 and s.access_gap_index >= 12:
        messages.append(("Policy Maker close to victory!", SUCCESS_COLOR))
    if s.profit > 80 and s.profit <= 85:
        messages.append(("Insurance Company close to victory!", WARNING_COLOR))
    if s.uninsured_rate > 15.5:
        messages.append(("Approaching failure condition!", WARNING_COLOR))
    if s.public_health_index < 35:
        messages.append(("Health crisis approaching!", WARNING_COLOR))

    if messages and y_offset < y + panel_height - 60:
        dwg.add(dwg.text("⚡ ALERTS:", insert=(x + 10, y + y_offset),
                        font_size=SMALL_FS,
                        fill="rgb(51, 51, 51)",
                        font_weight="bold"))
        y_offset += 16
        for message, color in messages:
            if y_offset < y + panel_height - 20:
                dwg.add(dwg.text(f"• {message}", insert=(x + 20, y + y_offset),
                                font_size=SMALL_FS,
                                font_weight="bold",
                                fill=color))
                y_offset += 14
        y_offset += 5
    # Special conditions - only add if there's space remaining
    if y_offset < y + panel_height - 40:
        if s.premium_cap_turns_left > 0:
            dwg.add(dwg.text("Premium Cap Active:", insert=(x + 10, y + y_offset),
                            font_size=SMALL_FS,
                            fill=ACCENT_COLOR,
                            font_weight="bold"))
            dwg.add(dwg.text(f"{s.premium_cap_turns_left} turns left", insert=(x + panel_width - 10, y + y_offset),
                            text_anchor="end",
                            font_size=SMALL_FS,
                            fill=ACCENT_COLOR))
            y_offset += 16
        
        if s.public_expansion_cap_turns_left > 0 and y_offset < y + panel_height - 20:
            dwg.add(dwg.text("Public Expansion Blocked:", insert=(x + 10, y + y_offset),
                            font_size=SMALL_FS,
                            fill=WARNING_COLOR,
                            font_weight="bold"))
            dwg.add(dwg.text(f"{s.public_expansion_cap_turns_left} turns left", insert=(x + panel_width - 10, y + y_offset),
                            text_anchor="end",
                            font_size=SMALL_FS,
                            fill=WARNING_COLOR))
            y_offset += 16
        
        if s.skip_next_turn and y_offset < y + panel_height - 20:
            dwg.add(dwg.text("Next Turn Skipped:", insert=(x + 10, y + y_offset),
                            font_size=SMALL_FS,
                            fill=WARNING_COLOR,
                            font_weight="bold"))
            dwg.add(dwg.text("Lobbying Effect", insert=(x + panel_width - 10, y + y_offset),
                            text_anchor="end",
                            font_size=SMALL_FS,
                            fill=WARNING_COLOR))
            y_offset += 16

        # Lobbying benchmark info
        if s.influence_meter >= 75 and s.last_lobbied >= 3 and y_offset < y + panel_height - 20:
            dwg.add(dwg.text("Lobbying Available!", insert=(x + 10, y + y_offset),
                            font_size=SMALL_FS,
                            fill=SUCCESS_COLOR,
                            font_weight="bold"))
            y_offset += 16
        elif s.influence_meter >= 75 and y_offset < y + panel_height - 20:
            dwg.add(dwg.text(f"Lobbying in {3 - s.last_lobbied} turns", insert=(x + 10, y + y_offset),
                            font_size=SMALL_FS,
                            fill="rgb(255, 193, 7)"))
            y_offset += 16

def draw_progress_bars(dwg, s, x, y):
    """Draw visual progress bars for key metrics"""
    bar_width = 200
    bar_height = 18
    bar_spacing = 45
    
    # Progress bars for key metrics - added extra metrics from removed panel
    bars = [
        ("Public Health", s.public_health_index, 100, SUCCESS_COLOR),
        ("Public Trust", s.public_trust_meter, 100, ACCENT_COLOR),
        ("Insurer Influence", s.influence_meter, 100, WARNING_COLOR),
        ("Budget Level", min(s.budget, 100), 100, "rgb(13, 110, 253)"),
        ("Access Gap", 100 - s.access_gap_index, 100, SUCCESS_COLOR),  # Inverted so lower gap = higher bar
        ("Coverage Rate", 100 - s.uninsured_rate, 100, SUCCESS_COLOR)  # Inverted so lower uninsured = higher bar
    ]
    
    dwg.add(dwg.text("Key Indicators", insert=(x, y - 25),
                    font_size=MEDIUM_FS,
                    font_weight="bold",
                    fill="rgb(51, 51, 51)"))
    
    y_offset = 0
    for label, value, max_val, color in bars:
        # Background bar
        dwg.add(dwg.rect(insert=(x, y + y_offset + 2.5),
                        size=(bar_width, bar_height),
                        fill="rgb(233, 236, 239)",
                        stroke="rgb(200, 200, 200)",
                        stroke_width="1"))
        
        # Progress fill
        fill_width = (value / max_val) * bar_width
        dwg.add(dwg.rect(insert=(x, y + y_offset + 2.5),
                        size=(fill_width, bar_height),
                        fill=color))
        
        # Label and value
        dwg.add(dwg.text(label, insert=(x, y + y_offset - 5),
                        font_size=SMALL_FS,
                        fill="rgb(51, 51, 51)"))
        
        # Show actual values for inverted metrics
        if "Access Gap" in label:
            display_value = s.access_gap_index
        elif "Coverage Rate" in label:
            display_value = f"{100 - s.uninsured_rate:.1f}%"
        elif "Insurer Influence" in label or "Public Trust" in label:
            display_value = f"{value:}%"
        elif "Budget Level" in label:
            display_value = f"${s.profit}B"
        else:
            display_value = f"{value:.0f}"
            
        dwg.add(dwg.text(str(display_value), insert=(x + bar_width + 10, y + y_offset + 15),
                        font_size=SMALL_FS,
                        fill="rgb(51, 51, 51)"))
        
        y_offset += bar_spacing



def draw_game_over(dwg, s):
    """Draw game over screen"""
    # Semi-transparent overlay
    dwg.add(dwg.rect(insert=(0, 0),
                    size=(str(W), str(H)),
                    fill="rgba(0, 0, 0, 0.7)"))
    
    # Game over box
    box_width = 400
    box_height = 150
    box_x = (W - box_width) // 2
    box_y = (H - box_height) // 2
    
    dwg.add(dwg.rect(insert=(box_x, box_y),
                    size=(box_width, box_height),
                    fill="white",
                    stroke="rgb(200, 200, 200)",
                    stroke_width="3",
                    rx="10"))
    
    # Game over text
    dwg.add(dwg.text("GAME OVER", insert=(W//2, box_y + 40),
                    text_anchor="middle",
                    font_size="32",
                    font_weight="bold",
                    fill=WARNING_COLOR))
    
    dwg.add(dwg.text(s.win, insert=(W//2, box_y + 80),
                    text_anchor="middle",
                    font_size=MEDIUM_FS,
                    fill="rgb(51, 51, 51)"))
    
    if s.winner >= 0:
        winner_text = f"Winner: {prob.int_to_name(s.winner)}"
        dwg.add(dwg.text(winner_text, insert=(W//2, box_y + 110),
                        text_anchor="middle",
                        font_size=MEDIUM_FS,
                        font_weight="bold",
                        fill=SUCCESS_COLOR)) 

# Utility functions for color coding
def get_health_color(value, threshold, higher_is_worse):
    """Get color based on health metric"""
    if higher_is_worse:
        if value > threshold * 0.8:
            return WARNING_COLOR
        elif value > threshold * 0.6:
            return "rgb(255, 193, 7)"  # Warning yellow
        else:
            return SUCCESS_COLOR
    else:
        if value < threshold * 1.2:
            return WARNING_COLOR
        elif value < threshold * 1.5:
            return "rgb(255, 193, 7)"  # Warning yellow
        else:
            return SUCCESS_COLOR

def get_trust_color(value):
    """Get color for trust meter"""
    if value < 30:
        return WARNING_COLOR
    elif value < 60:
        return "rgb(255, 193, 7)"
    else:
        return SUCCESS_COLOR

def get_influence_color(value):
    """Get color for influence meter"""
    if value > 80:
        return WARNING_COLOR
    elif value > 60:
        return "rgb(255, 193, 7)"
    else:
        return SUCCESS_COLOR

def get_budget_color(value):
    """Get color for budget"""
    if value < 15:
        return WARNING_COLOR
    elif value < 30:
        return "rgb(255, 193, 7)"
    else:
        return SUCCESS_COLOR

CARD_IMAGES=\
    {("r",0): "Cap Premiums.jpg",
     ("r",1): "Expand Public Coverage.jpg",
     ("r",2): "Invest in Clinics.jpg",
     ("r",3): "Mandate Coverage.jpg",
     ("r",4): "Request Funds.jpg",
     ("r",5): "Subsidize Coverage.jpg",
     ("i",0): "Lobby Government.jpg",
     ("i",1): "Misinformation.jpg",
     ("i",2): "Narrow Network.jpg",
     ("i",3): "Funds Intercepted.png",
     ("i",4): "Raise Premiums.jpg",
     ("i",5): "Risk Selection.jpg"\
    }

IMAGE_WIDTH = 360
IMAGE_HEIGHT = 400

def insert_card(dwg, card, x, y):
    global session
    try:
      filename = CARD_IMAGES[card]
    except Exception as e:
        print("Could not access card filename from card object.")
        print(e)
    try:
        url = "http://"+session['HOST']+":"+str(session['PORT'])+"/get_image/"+filename
    except Exception as e2:
        print("A problem creating the URL. ", e2)
    scale_factor = 0.65
    w = IMAGE_WIDTH*scale_factor
    h = IMAGE_HEIGHT*scale_factor
    image = dwg.image(url, insert=(x, y), size=(w, h))
    dwg.add(image)


def r_insert(dwg):
    insert_card(dwg,("r",0),260,350)
    insert_card(dwg,("r",1),440,350)
    insert_card(dwg,("r",2),620,350)
    insert_card(dwg,("r",3),800,350)
    insert_card(dwg,("r",4),620,80)
    insert_card(dwg,("r",5),800,80)


def i_insert(dwg):
    insert_card(dwg,("i",0),260,350)
    insert_card(dwg,("i",1),440,350)
    insert_card(dwg,("i",2),620,350)
    insert_card(dwg,("i",3),800,350)
    insert_card(dwg,("i",4),620,80)
    insert_card(dwg,("i",5),800,80)
