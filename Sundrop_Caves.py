#Lewis Ng Zheng Loong
#S10268542C IM01
#------------------------------------------------------------------------------------
#Global Constants and Helpers
#------------------------------------------------------------------------------------
from random import randint
import os
import platform
import json
import msvcrt

GAMESTATE_MAIN = 0
GAMESTATE_TOWN = 1
GAMESTATE_QUIT = 2
GAMESTATE_MINE = 3
GAMESTATE_SHOP = 4

game_state = GAMESTATE_MAIN

player = {}
game_map = []
fog = []

VIEW_RADIUS = 1   # how many squares away from player get revealed
FOG_UNEXPLORED = "?"
FOG_EXPLORED = " "

MAPMARKER_PLAYER = "M"
MAPMARKER_PORTAL = "P"
MAPMARKER_TOWN = "T"
MAPMARKER_FOG = "?"

TOWN_X, TOWN_Y = 0, 0
PORTAL_KEY_X = "portal_x"
PORTAL_KEY_Y = "portal_y"

VIEW_SIZE = 3          
WALL_CHAR = "#"
BORDER_CORNER = "+"
BORDER_HORIZONTAL = "-"
BORDER_VERTICAL = "|"

MOVES = {
    "w": (0, -1),
    "s": (0,  1),
    "a": (-1, 0),
    "d": (1,  0),
}

WALKABLE = {" ", "C", "S", "G", MAPMARKER_TOWN}

MAP_WIDTH = 0
MAP_HEIGHT = 0

TURNS_PER_DAY = 20
WIN_GP = 500

minerals = ['copper', 'silver', 'gold']
mineral_names = {'C': 'copper', 'S': 'silver', 'G': 'gold'}

pickaxe_upgrades = [
    (50, "silver"),
    (150, "gold"),
]

prices = {}
prices['copper'] = (1, 3)
prices['silver'] = (5, 8)
prices['gold'] = (10, 18)

TORCH_PRICE = 50

original_map = []

SCORES_PATH = "scores.json"

#------------------------------------------------------------------------------------
#Helpers
#------------------------------------------------------------------------------------
def is_win32(): #returns True if OS is Windows. Used to decide whether to use msvcrt for single-key input.
    return platform.system() == "Windows"    

def clear_screen(): #clears the console with cls (Windows) or clear (others).
    if is_win32(): 
        os.system('cls')
    else:
        os.system('clear')

def get_input(prompt="Your Choice? "): #custom player input prompt
    return input(prompt).strip()

def get_key(prompt=" "): #prints a prompt that on windows reads one key via msvcrt.getch(), otherwise falls back to get_input().
    if is_win32():
        print(prompt)
        return msvcrt.getch().decode().lower()
    else:
        return get_input(prompt)    

def press_to_return(): #standard "Press any key" pause using get_key().
    get_key("Press any key to return...")

def in_bounds(x, y): #returns if (x,y) is inside the current map rectangle using MAP_WIDTH/HEIGHT.
    return 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT

#------------------------------------------------------------------------------------
#GAMESAVE
#------------------------------------------------------------------------------------

def serialize_game_data(player, fog, game_map, path): #builds a dict with player and fog and writes JSON to path.
    state = {"player": player, "fog": fog, "map": game_map}
    with open(path, "w") as f:
        json.dump(state, f)

def deserialize_game_data(path): #reads JSON and returns it.
    with open(path, "r") as f:
        return json.load(f)
    
def confirm_overwrite_if_save_exists(path="save.json"): #returns True if saving is allowed (no file or user presses Y), else False.
    if os.path.exists(path):
        ans = get_key("A save file already exists. Overwrite it? (Y/N): ")
        return ans == "y"
    return True

def save_game(game_map, fog, player, path="save.json"): #asks permission via confirm_overwrite_if_save_exists() and if OK, calls serialize_game_data() and prints confirmation.
    if not confirm_overwrite_if_save_exists(path):
        print("Okay, didn’t save. Keeping your old file safe.")
        return
    else:
        serialize_game_data(player, fog, game_map, path) 
        print("Game saved.")                  
        
# This function loads the game
def load_game(game_map, fog, player, path="save.json"):
    try:
        state = deserialize_game_data(path) #Opens path and reads JSON into a Python dict called state.
        load_map("level1.txt", game_map) #Rebuilds the base cave layout from the level file into game_map. 

        player.clear() #empties the dict in-place and fills it with the saved keys/values.
        player.update(state["player"]) #Replace current player data with the saved one.

        global VIEW_SIZE
        VIEW_SIZE = 5 if player.get('has_torch') else 3 #checks if player owns torch and sets viewport accordingly

        fog.clear()
        fog.extend(state["fog"]) #Replace current fog with the saved fog grid (again, mutate in-place).

        if "map" in state: #Checks that the loaded save file actually contains a "map" entry. If it doesn’t, we skip the restore so we don’t crash.
            game_map.clear() #Empties the existing game_map in place.
            for row in state["map"]: #Loops through each saved row from the file.
                game_map.append(row[:]) #builds the new map contents into the existing game_map object.

        print("Game loaded!")
        return True
    except (FileNotFoundError, KeyError):
        print("no valid save found.")
        press_to_return()
        return False #If the save file doesn’t exist (FileNotFoundError) or the JSON is missing expected keys like "player" or "fog" (KeyError), show a message, wait for a key, and return False.

#------------------------------------------------------------------------------------
#Scores
#------------------------------------------------------------------------------------

def _score_key(rec): #sorts by fewest days, then fewest steps, then more gp because of the negative sign, then name for determining ties. 
    return (rec.get("days", 0), rec.get("steps", 0), -rec.get("gp", 0), rec.get("name","").lower())

def load_scores(path=SCORES_PATH): #reads the scores.json file (or returns empty list on first run/corruption).
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_scores(scores, path=SCORES_PATH): #overwrites scores.json with the given list.
    with open(path, "w") as f:
        json.dump(scores, f)

def add_score_from_player(player, path=SCORES_PATH): #builds a score record from the current player, appends, sorts using _score_key, and saves.
    scores = load_scores(path)
    rec = {
        "name": player.get("name","Unknown"),
        "days": player.get("day", 0),
        "steps": player.get("steps", 0),
        "gp": player.get("GP", 0),
    }
    scores.append(rec)
    scores.sort(key=_score_key)
    save_scores(scores, path)

def show_high_scores(path=SCORES_PATH): #clears screen; formats and prints top 5 records; waits for a key.
    clear_screen()
    print("----- Top Miners of Sundrop Mountain -----")
    scores = load_scores(path)
    if not scores:
        print("No scores yet. Be the first to retire rich!")
        press_to_return()
        return

    print("Rank  Name            Days  Steps     GP")
    print("-------------------------------------------")
    for i, rec in enumerate(scores[:5], start=1):
        print(f"{i:>4}  {rec['name']:<14} {rec['days']:>4}  {rec['steps']:>5}  {rec['gp']:>7}")
    press_to_return()

#------------------------------------------------------------------------------------
#Map
#------------------------------------------------------------------------------------

def load_map(filename, map_struct):
    map_file = open(filename, 'r')
    global MAP_WIDTH
    global MAP_HEIGHT
    
    map_struct.clear()
    
    # TODO: Add your map loading code here
    for line in map_file:
        row = list(line.rstrip('\n')) #it strips new line chr \n
        map_struct.append(row)
    
    MAP_WIDTH = len(map_struct[0])
    MAP_HEIGHT = len(map_struct)

    global original_map
    original_map = [row[:] for row in map_struct]

    map_file.close()

def clear_fog(fog, player): # This function clears the fog of war at the 3x3 square around the player
    px, py = player['x'], player['y']
    
    for dy in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
        for dx in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
            nx, ny = px + dx, py + dy
            if 0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH:
                fog[ny][nx] = FOG_EXPLORED

def initialize_fog(fog): #fills the fog grid with ? characters, matching map size.
    fog.clear()
    for i in range(MAP_HEIGHT): #for 
        fog.append([FOG_UNEXPLORED] * MAP_WIDTH)

def get_tile_marker(x, y, game_map, player): #decides which char to show at a coordinate, prioritizing town, portal, player, then the underlying tile from game_map.
    current_coord = (x, y)
    player_coord = (player['x'], player['y'])
    portal_coord = (player.get(PORTAL_KEY_X), player.get(PORTAL_KEY_Y))
    town_coord = (TOWN_X, TOWN_Y)

    if current_coord == town_coord:
        return MAPMARKER_TOWN
    elif current_coord == portal_coord:
        return MAPMARKER_PORTAL
    elif current_coord == player_coord:
        return MAPMARKER_PLAYER
    else:
        return game_map[y][x]

def map_tile(x, y, game_map, fog, player): #returns ? if that spot is still fogged. otherwise delegates to get_tile_marker().
    if fog[y][x] == FOG_UNEXPLORED:
        return MAPMARKER_FOG
    return get_tile_marker(x, y, game_map, player)

#------------------------------------------------------------------------------------
#Player
#------------------------------------------------------------------------------------

def initialize_player(player): #sets default stats and flags
    player['name'] = ""
    player['x'] = 0
    player['y'] = 0
    player['copper'] = 0
    player['silver'] = 0
    player['gold'] = 0
    player['GP'] = 0
    player['day'] = 1
    player['steps'] = 0
    player['turns'] = TURNS_PER_DAY
    player['pickaxe_level'] = 1
    player['capacity'] = 10
    player[PORTAL_KEY_X] = 0
    player[PORTAL_KEY_Y] = 0
    player['has_torch'] = False
    player['score_submitted'] = False

def current_load(p): #total ore pieces in the backpack.
    return p.get('copper', 0) + p.get('silver', 0) + p.get('gold', 0)

def is_full(p): #returns whether current_load >= capacity.
    return current_load(p) >= p['capacity']

def place_portal_here(player): #records current (x,y) into the player’s portal fields.
    player[PORTAL_KEY_X] = player['x']
    player[PORTAL_KEY_Y] = player['y']

#------------------------------------------------------------------------------------
#Drawing
#------------------------------------------------------------------------------------

def draw_map(game_map, fog, player): #prints a top border, then each map row with left/right borders, then the bottom border. Each row is built with map_tile() per column.
    print(viewport_border(MAP_WIDTH))  # top border

    for y in range(MAP_HEIGHT):
        row = [map_tile(x, y, game_map, fog, player) for x in range(MAP_WIDTH)]
        print(BORDER_VERTICAL + "".join(row) + BORDER_VERTICAL)

    print(viewport_border(MAP_WIDTH))  # bottom border

# This function draws the 3x3/5x5 viewport
def draw_view(game_map, fog, player, size=VIEW_SIZE):
    px, py = player['x'], player['y']
    half = viewport_half(size)

    # top border
    print(viewport_border(size))

    # each viewport row from top → bottom
    for dy in range(-half, half + 1):
        row_chars = []
        # each column from left → right
        for dx in range(-half, half + 1):
            x, y = px + dx, py + dy
            row_chars.append(viewport_tile(x, y, px, py, game_map, player))
        # side borders
        print(BORDER_VERTICAL + "".join(row_chars) + BORDER_VERTICAL)

    # bottom border
    print(viewport_border(size))

def viewport_border(inner_width): #returns the +----+ style border string.
    return BORDER_CORNER + (BORDER_HORIZONTAL * inner_width) + BORDER_CORNER

def viewport_half(size): #integer half-size; a size of 3 yields 1 (so rows are -1,0,1).
    return size // 2

def viewport_tile(x, y, px, py, game_map, player): #decide what to show at (x,y) in the viewport.
    if (x, y) == (px, py):
        return MAPMARKER_PLAYER
    if not in_bounds(x, y):
        return WALL_CHAR
    
    portal_pos = (player.get(PORTAL_KEY_X), player.get(PORTAL_KEY_Y))
    if (x, y) == portal_pos:
        return game_map[y][x]
    return get_tile_marker(x, y, game_map, player)

#------------------------------------------------------------------------------------
#Mining
#------------------------------------------------------------------------------------

def replenish_nodes(game_map, chance=0.2): 
    restored = 0
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if original_map[y][x] in ("C", "S", "G"):
                if game_map[y][x] == " ":
                    if randint(1, 100) <= int(chance * 100):
                        game_map[y][x] = original_map[y][x]
                        restored += 1
    return restored

def show_replenish_notice(player):
    pending = player.pop('pending_replenish', None)
    if pending is None:
        return  # nothing to show
    if pending:
        print(f"{pending} node(s) replenished overnight!")
    else:
        print("No nodes replenished today.")

def pieces_from_node(tile):
    if tile == "C": return randint(1, 5)
    if tile == "S": return randint(1, 3)
    if tile == "G": return randint(1, 2)
    return 0

def can_mine(tile, player):
    if tile == "C":  # copper
        return player['pickaxe_level'] >= 1
    if tile == "S":  # silver
        return player['pickaxe_level'] >= 2
    if tile == "G":  # gold
        return player['pickaxe_level'] >= 3
    return False

def ore_value(ore_type):
    if ore_type == "C":
        return randint(*prices['copper'])
    if ore_type == "S":
        return randint(*prices['silver'])
    if ore_type == "G":
        return randint(*prices['gold'])
    return 0

def add_ore_to_inventory(player, ore_tile, count):
    if ore_tile == "C":
        player['copper'] += count
    elif ore_tile == "S":
        player['silver'] += count
    elif ore_tile == "G":
        player['gold'] += count

def award_ore_info(ore_tile, node_pieces, can_carry):
    ore_name = mineral_names[ore_tile]
    print(f"You mined {node_pieces} piece(s) of {ore_name}.")
    if node_pieces > can_carry:
        if can_carry <= 0:
            print("...but your backpack is already full!")
        else:
            print(f"...but you can only carry {can_carry} more piece(s)!")
    press_to_return()

def consume_tile_and_turn(game_map, player):
    game_map[player['y']][player['x']] = " "
    player['turns'] -= 1

def mine_tile(player, game_map):
    tile = get_tile_under_player(player, game_map)

    if tile not in {"C", "S", "G"}: # only do anything if on ore
        return

    pieces = pieces_from_node(tile) # how many pieces this node gives

    remaining = player['capacity'] - current_load(player) # respect remaining backpack space
    mined = max(0, min(pieces, remaining))

    if mined == 0:
        print("You can't carry any more, so you can't go that way.")
        press_to_return()
        return

    # add to inventory and report
    add_ore_to_inventory(player, tile, mined)
    award_ore_info(tile, pieces, remaining)

    # consume the node and keep exploring
    game_map[player['y']][player['x']] = " "

#------------------------------------------------------------------------------------
#Movement
#------------------------------------------------------------------------------------

def post_move(fog, player, game_map):
    clear_fog(fog, player)
    mine_tile(player, game_map)
    if get_tile_under_player(player, game_map) == MAPMARKER_TOWN:
        global game_state
        print("You arrive at Sundrop Town.")
        press_to_return()
        game_state = GAMESTATE_TOWN
        return
    if player['turns'] <= 0:
        end_day(player)

def is_walkable(x, y, game_map, player):
    if not in_bounds(x, y):
        return False

    tile = game_map[y][x]
    
    # if it's an ore, you can only walk on it if you can mine it
    if tile in {"C", "S", "G"}:
        return can_mine(tile, player)

    return tile in WALKABLE

def get_tile_under_player(player, game_map):
    return game_map[player['y']][player['x']]

def can_attempt_move(dir_key, player):
    return dir_key in MOVES and player['turns'] > 0

def get_target_position(dir_key, player):
    dx, dy = MOVES[dir_key]
    return player['x'] + dx, player['y'] + dy

def move_player(player, x, y):
    player['x'], player['y'] = x, y
    player['steps'] += 1

def try_step(dir_key, game_map, player):
    if not can_attempt_move(dir_key, player):
        return False

    nx, ny = get_target_position(dir_key, player)

    if not in_bounds(nx, ny):
        print("You bump into the wall.")
        press_to_return()
        return False

    tile = game_map[ny][nx]

    if tile in {"C", "S", "G"}:
        if is_full(player):
            print("You can't carry any more, so you can't go that way.")
            press_to_return()
            return True  # spend a turn, no movement
        if not can_mine(tile, player):
            print("Your pickaxe isn’t strong enough for this ore!")
            press_to_return()
            return True  # spend a turn, no movement

    # success: move and spend a turn
    move_player(player, nx, ny)
    return True

def handle_turns(fog, player, game_map):
    player['turns'] -= 1
    post_move(fog, player, game_map)
    if player['turns'] <= 0:
        end_day(player)

#------------------------------------------------------------------------------------
#Shop
#------------------------------------------------------------------------------------

def sell_haul(player, announce=True):
    total = calc_sale_total(player)
    if total > 0:
        deposit_gp(player, total)
        clear_inventory(player)
        if announce:
            announce_sale(total)
    else:
        if announce:
            announce_no_sale(player)
    return total

def upgrade_price(player): #dynamic backpack price (twice current capacity).
    return player['capacity'] * 2

def can_afford_upgrade(player):
    return player['GP'] >= upgrade_price(player)

def upgrade_backpack(player): #convenience boolean.
    price = upgrade_price(player)
    if player['GP'] >= price:
        player['GP'] -= price
        player['capacity'] += 2
        print(f"Backpack upgraded! Capacity is now {player['capacity']}.")
        press_to_return()
    else:
        print(f"Not enough GP. You need {price} GP to upgrade your backpack.")
        press_to_return()

def calc_sale_total(player): #checks GP, deducts price, adds +2 capacity, pauses with a message.
    total = 0
    for _ in range(player['copper']): total += ore_value("C")
    for _ in range(player['silver']): total += ore_value("S")
    for _ in range(player['gold']):   total += ore_value("G")
    return total

def deposit_gp(player, amount): #
    player['GP'] += amount

def clear_inventory(player):
    player['copper'] = 0
    player['silver'] = 0
    player['gold']   = 0

def announce_sale(total):
    print(f"You sold your haul for {total} GP!")
    print(f"You now have {player['GP']} GP!")
    press_to_return()

def announce_no_sale(player):
    print("You have nothing to sell.")
    print(f"You still have {player['GP']} GP!")
    press_to_return()    

def get_backpack_upgrade_info(player):
    price = upgrade_price(player)
    next_cap = player['capacity'] + 2
    return price, next_cap

def shop_backpack_line(player):
    price, next_cap = get_backpack_upgrade_info(player)
    return f"(B)ackpack upgrade to carry {next_cap} items for {price} GP"

def pickaxe_name(player):
    idx = max(0, min(player['pickaxe_level'] - 1, len(minerals) - 1))
    return minerals[idx]

def get_pickaxe_upgrade_info(player):
    current_level = player['pickaxe_level']
    if current_level > len(pickaxe_upgrades):
        return None, None, None  
    price, unlocks = pickaxe_upgrades[current_level - 1]
    next_level = current_level + 1
    return next_level, price, unlocks

def upgrade_pickaxe(player):
    next_level, price, unlocks = get_pickaxe_upgrade_info(player)
    if next_level is None:
        print("Your pickaxe is already at the maximum level.")
        press_to_return()
        return

    if player['GP'] < price:
        print(f"Not enough GP. You need {price} GP to upgrade your pickaxe.")
        press_to_return()
        return

    player['GP'] -= price
    player['pickaxe_level'] = next_level
    print(f"Pickaxe upgraded to level {next_level}! You can now mine {unlocks} ore.")
    press_to_return()

def shop_pickaxe_line(player):
    next_level, price, unlocks = get_pickaxe_upgrade_info(player)
    if next_level is None:
        return "(P)ickaxe upgrade: MAX LEVEL"
    return f"(P)ickaxe upgrade to Level {next_level} to mine {unlocks} for {price} GP"

def shop_torch_line(player):
    if player.get('has_torch'):
        return "(M)agic torch: OWNED (view 5x5)"
    return f"(M)agic torch that increases view to 5x5 for {TORCH_PRICE} GP"

def torch_owned(player):
    return player.get('has_torch', False)

def buy_magic_torch(player):
    global VIEW_SIZE
    if torch_owned(player):
        print("You already own the magic torch.")
        press_to_return()
        return
    if player['GP'] < TORCH_PRICE:
        print(f"Not enough GP. You need {TORCH_PRICE} GP for the magic torch.")
        press_to_return()
        return
    player['GP'] -= TORCH_PRICE
    player['has_torch'] = True
    VIEW_SIZE = 5      # immediately expand the viewport
    print("The cavern glows! Your view is now 5x5.")
    press_to_return()

#------------------------------------------------------------------------------------
#Menus
#------------------------------------------------------------------------------------

def show_information(player):
    print()
    print("----- Player Information -----")
    print(f"Name: {player['name']} ")
    print(f"Portal Position: ({player.get(PORTAL_KEY_X)}, {player.get(PORTAL_KEY_Y)})")
    print(f"Pickaxe Level: {player['pickaxe_level']} ({pickaxe_name(player)})")
    print(f"Load: {current_load(player)} / {player['capacity']}")
    print("------------------------------")
    print(f"GP: {player['GP']}")
    print(f"Steps taken: {player['steps']} ")
    print("------------------------------")
    print()

def quit_to_main_menu():
    global game_state
    ans = get_key("Quit without saving? (Y/N): ")
    if ans in ("y", "yes"):
        game_state = GAMESTATE_MAIN
    elif ans in ("n", "no"):
        return
    else:
        print("Invalid option, just press Enter to return.")
        press_to_return()

# This function loads the shop
def show_shop_menu(player):
    global game_state
    price, next_cap = get_backpack_upgrade_info(player)
    pickaxe_line = shop_pickaxe_line(player)
    backpack_line = shop_backpack_line(player)
    torch_line = shop_torch_line(player)
    print()
    print("----------------------- Shop Menu -------------------------")
    print(pickaxe_line)
    print(backpack_line)
    print(torch_line)
    print("(L)eave shop")
    print("-----------------------------------------------------------")
    print(f"Your GP: {player['GP']}")
    print("-----------------------------------------------------------")
    playerinput = get_key("Your choice? ")
    if playerinput == "l":
        game_state = GAMESTATE_TOWN
        return
    elif playerinput == "b":
        upgrade_backpack(player)
    elif playerinput == "p":
        upgrade_pickaxe(player)
    elif playerinput == "m":
        buy_magic_torch(player)
        

def get_player_name():
    clear_screen()
    player['name'] = get_input("Greetings miner! What is your name? ")
    print(f"Pleased to meet you, {player['name']}. Welcome to Sundrop Town!")
    press_to_return()          

def show_main_menu():
    global game_state
    print("---------------- Welcome to Sundrop Caves! ----------------")
    print("You spent all your money to get the deed to a mine, a small")
    print("  backpack, a simple pickaxe and a magical portal stone.")
    print()
    print("How quickly can you get the 500 GP you need to retire")
    print("  and live happily ever after?")
    print("-----------------------------------------------------------")
    print()
    print("--- Main Menu ----")
    print("(N)ew game")                
    print("(L)oad saved game")
    print("(T)op scores")
    print("(Q)uit")    
    print("------------------")
    playerinput = get_key()
    if playerinput == "n":
        initialize_game(game_map, fog, player)
        get_player_name()
        game_state = GAMESTATE_TOWN
    elif playerinput == "l": 
        if load_game(game_map, fog, player):
            game_state = GAMESTATE_TOWN
    elif playerinput == "t":             
        show_high_scores()
    elif playerinput == "q":
        game_state = GAMESTATE_QUIT

def show_town_menu():
    global game_state
    if maybe_win(player):
        return
    print()
    # TODO: Show Day
    print("------Sundrop Town------")
    print(f"Day {player['day']}".center(len("----- Sundrop Town -----")))
    print("------------------------")
    print("(B)uy stuff")
    print("See Player (I)nformation")
    print("See Mine (M)ap")
    print("(E)nter mine")
    print("Sa(V)e game")
    print("(Q)uit to main menu")
    print("------------------------")
    playerinput = get_key()
    if playerinput == "q":
        quit_to_main_menu()
    elif playerinput == "b":
        game_state = GAMESTATE_SHOP
    elif playerinput == "i":
        clear_screen()
        show_information(player)
        press_to_return()
    elif playerinput == "m":
        clear_screen()
        draw_map(game_map, fog, player)
        press_to_return()
    elif playerinput == "e":
        game_state = GAMESTATE_MINE
    elif playerinput == "v":
        save_game(game_map, fog, player)
        press_to_return()

def show_mine_menu(game_map, fog, player):
    #draw_map(game_map, fog, player)
    global game_state
    print()
    print("--------The Mine--------")
    print(f"Day {player['day']}".center(len("---------------------")))
    print("------------------------")
    show_replenish_notice(player)
    draw_view(game_map, fog, player, size=VIEW_SIZE)
    print("----- MINE MENU -----")
    print("(WASD) to move")
    print(f"Turns left: {player['turns']}    Load: {current_load(player)}/{player['capacity']}    Steps: {player['steps']}")
    print("P = Portal")
    print("I = Information")
    print("M = Map")
    print("Q = Quit to Main Menu")
    print()
    playerinput = get_key("Action?")
    if playerinput == "p":
        place_portal_here(player)
        total = sell_haul(player, announce=True)  
        if maybe_win(player):
            return
        print("You place your portal stone here and zap back to town.")
        player['day'] += 1
        player['turns'] = TURNS_PER_DAY
        player['pending_replenish'] = replenish_nodes(game_map, 0.2)
        game_state = GAMESTATE_TOWN
    elif playerinput == "q":
        quit_to_main_menu()
    elif playerinput == "i":
        clear_screen()
        show_information(player)
        press_to_return()
    elif playerinput == "m":
        clear_screen()
        draw_map(game_map, fog, player)
        press_to_return()
    elif try_step(playerinput, game_map, player):
        handle_turns(fog, player, game_map)

#------------------------------------------------------------------------------------
#Gameflow
#------------------------------------------------------------------------------------

def initialize_game(game_map, fog, player):
    # initialize map
    load_map("level1.txt", game_map)

    # TODO: initialize fog
    initialize_fog(fog)
    
    # TODO: initialize player
    initialize_player(player)
    

    clear_fog(fog, player)  

def end_day(player):
    place_portal_here(player)
    earned = sell_haul(player, announce=False)

    if maybe_win(player):   # already_paused defaults to True
        return

    print("You are exhausted.")
    print("You place your portal stone here and zap back to town.")

    if earned > 0:
        announce_sale(earned)
    else:
        announce_no_sale(player)

    player['pending_replenish'] = replenish_nodes(game_map, 0.2)
    player['day'] += 1
    player['turns'] = TURNS_PER_DAY
    global game_state
    game_state = GAMESTATE_TOWN


def maybe_win(player, already_paused=True):
    global game_state
    if player['GP'] >= WIN_GP:
        clear_screen()
        print("-----------------------------------------------------------")
        print(f"Woo-hoo! Well done, {player['name']}, you have {player['GP']} GP!")
        print("You now have enough to retire and play video games every day.")
        print(f"And it only took you {player['day']} days and {player['steps']} steps! You win!")
        print("-----------------------------------------------------------")
        if not player.get('score_submitted'):
            add_score_from_player(player)
            player['score_submitted'] = True

        if already_paused:  # only pause if we didn't pause elsewhere
            press_to_return()
        game_state = GAMESTATE_MAIN
        return True
    return False
#--------------------------- MAIN GAME ---------------------------
# TODO: The game! Main loop using a finite state machine. 
clear_screen()
while game_state != GAMESTATE_QUIT:
    if game_state == GAMESTATE_MAIN:
        show_main_menu()
    elif game_state == GAMESTATE_TOWN:
        show_town_menu()
    elif game_state == GAMESTATE_SHOP:
        show_shop_menu(player)
    elif game_state == GAMESTATE_MINE:
        show_mine_menu(game_map, fog, player)
    
    clear_screen()

print("quitting game")


 

