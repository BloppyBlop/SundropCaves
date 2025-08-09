#Global Constants and Helpers
#------------------------------------------------------------------------------------
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
pickaxe_price = [50, 150]

prices = {}
prices['copper'] = (1, 3)
prices['silver'] = (5, 8)
prices['gold'] = (10, 18)

#Other Functions
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

def is_win32():
    return platform.system() == "Windows"    

def clear_screen():
    if is_win32(): 
        os.system('cls')
    else:
        os.system('clear')

def get_input(prompt="Your Choice? "):
    return input(prompt).strip().lower()

def get_key(prompt=" "):
    if is_win32():
        print(prompt)
        return msvcrt.getch().decode().lower()
    else:
        return get_input(prompt)    

def press_to_return():
    get_key("Press any key to return...")

#GAMESAVE Functions
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

# This function saves the game
def serialize_game_data(player, fog, path):
    state = {"player": player, "fog": fog}
    with open(path, "w") as f:
        json.dump(state, f)

def deserialize_game_data(path):
    with open(path, "r") as f:
        return json.load(f)

def save_game(game_map, fog, player, path="save.json"):
    if not confirm_overwrite_if_save_exists(path):
        print("Okay, didn’t save. Keeping your old file safe.")
        return
    else:
        serialize_game_data(player, fog, path) 
        print("Game saved.")                  
        
# This function loads the game
def load_game(game_map, fog, player, path="save.json"):
    try:
        state = deserialize_game_data(path)
        load_map("level1.txt", game_map)

        player.clear()
        player.update(state["player"])

        fog.clear()
        fog.extend(state["fog"])

        print("Game loaded!")
        return True
    except (FileNotFoundError, KeyError):
        print("no valid save found.")
        press_to_return()
        return False
    
def confirm_overwrite_if_save_exists(path="save.json"):
    # returns True if it's okay to start a new game (overwrite), False if user cancels
    if os.path.exists(path):
        ans = get_key("A save file already exists. Overwrite it? (Y/N): ")
        return ans == "y"
    return True

def initialize_player(player):
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


#World Generation + Exploration Functions
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

# This function loads a map structure (a nested list) from a file
# It also updates MAP_WIDTH and MAP_HEIGHT
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

    map_file.close()

# This function clears the fog of war at the 3x3 square around the player
def clear_fog(fog, player):
    px, py = player['x'], player['y']
    
    for dy in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
        for dx in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
            nx, ny = px + dx, py + dy
            if 0 <= ny < MAP_HEIGHT and 0 <= nx < MAP_WIDTH:
                fog[ny][nx] = FOG_EXPLORED

def initialize_fog(fog):
    fog.clear()
    for i in range(MAP_HEIGHT): #for 
        fog.append([FOG_UNEXPLORED] * MAP_WIDTH)

def get_tile_marker(x, y, game_map, player):
    current_coord = (x, y)
    player_coord = (player['x'], player['y'])
    portal_coord = (player.get(PORTAL_KEY_X), player.get(PORTAL_KEY_Y))
    town_coord = (TOWN_X, TOWN_Y)

    if current_coord == town_coord:
        return MAPMARKER_TOWN
    elif current_coord == player_coord:
        return MAPMARKER_PLAYER
    elif current_coord == portal_coord:
        return MAPMARKER_PORTAL
    else:
        return game_map[y][x]

def map_tile(x, y, game_map, fog, player): #what to show on the full map
    if fog[y][x] == FOG_UNEXPLORED:
        return MAPMARKER_FOG
    return get_tile_marker(x, y, game_map, player)

# This function draws the entire map, covered by the fog
def draw_map(game_map, fog, player):
    print(viewport_border(MAP_WIDTH))  # top border

    for y in range(MAP_HEIGHT):
        row = [map_tile(x, y, game_map, fog, player) for x in range(MAP_WIDTH)]
        print(BORDER_VERTICAL + "".join(row) + BORDER_VERTICAL)

    print(viewport_border(MAP_WIDTH))  # bottom border

def initialize_game(game_map, fog, player):
    # initialize map
    load_map("level1.txt", game_map)

    # TODO: initialize fog
    initialize_fog(fog)
    
    # TODO: initialize player
    initialize_player(player)
    

    clear_fog(fog, player)   

def viewport_border(inner_width):
    return BORDER_CORNER + (BORDER_HORIZONTAL * inner_width) + BORDER_CORNER

def viewport_half(size):
    return size // 2

def viewport_tile(x, y, px, py, game_map, player): #decide what to show at (x,y) in the viewport.
    if (x, y) == (px, py):
        return MAPMARKER_PLAYER
    if not in_bounds(x, y):
        return WALL_CHAR
    return get_tile_marker(x, y, game_map, player)


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

#Mining Features
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

def get_tile_under_player(player, game_map):
    return game_map[player['y']][player['x']]

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

def add_ore_to_inventory(player, ore_tile):
    if ore_tile == "C":
        player['copper'] += 1
    elif ore_tile == "S":
        player['silver'] += 1
    elif ore_tile == "G":
        player['gold'] += 1

def award_ore_gp(player, tile):
    gp_gained = ore_value(tile)
    player['GP'] += gp_gained
    print(f"You mined {mineral_names[tile]} worth {gp_gained} GP!")

def consume_tile_and_turn(game_map, player):
    game_map[player['y']][player['x']] = " "
    player['turns'] -= 1

def mine_tile(player, game_map):
    tile = get_tile_under_player(player, game_map)
    if can_mine(tile, player):
        add_ore_to_inventory(player, tile)
        award_ore_gp(player, tile)
        consume_tile_and_turn(game_map, player)
    else:
        print("Your pickaxe isn't strong enough for this ore!")

#MPlayer Movement
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

def is_walkable(x, y, game_map):
    return in_bounds(x, y) and game_map[y][x] in WALKABLE

def try_step(dir_key, game_map, fog, player):
    if dir_key not in MOVES:
        return False  # not a movement key
    
    if player['turns'] <= 0:  # already out of turns
        return False
    
    dx, dy = MOVES[dir_key]
    nx, ny = player['x'] + dx, player['y'] + dy

    if is_walkable(nx, ny, game_map):
        player['x'], player['y'] = nx, ny
        player['steps'] += 1
        player['turns'] -= 1  # use a turn when moving
        if player['turns'] <= 0:
            end_day(player)  # new helper function

    return True

#Main UI
#------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------

#checks if position is inside or outside the map
def in_bounds(x, y):
    return 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT

# This function shows the information for the player
def show_information(player):
    print()
    print("----- Player Information -----")
    print(f"Name: {player['name']} ")
    print("Portal Position: (0, 0)")
    print("Pickaxe level: 1 (copper)")
    print("------------------------------")
    print(f"Load: 0/10")
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
        press_to_return()
    else:
        print("Invalid option, just press Enter to return.")
        press_to_return()

# This function loads the shop
def show_shop_menu(player):
    global game_state
    print()
    print("----------------------- Shop Menu -------------------------")
    print("(P)ickaxe upgrade to Level 2 to mine silver ore for 50 GP")
    print("(B)ackpack upgrade to carry 12 items for 20 GP")
    print("(M)agic torch that increases view to 5x5 for 50 GP")
    print("(L)eave shop")
    print("-----------------------------------------------------------")
    print("GP:")
    print("-----------------------------------------------------------")
    playerinput = get_key()
    if playerinput == "l":
        game_state = GAMESTATE_TOWN

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
    print("How quickly can you get the 1000 GP you need to retire")
    print("  and live happily ever after?")
    print("-----------------------------------------------------------")
    print()
    print("--- Main Menu ----")
    print("(N)ew game")                
    print("(L)oad saved game")
#    print("(H)igh scores")
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
    elif playerinput == "q":
        game_state = GAMESTATE_QUIT

def show_town_menu():
    global game_state
    print()
    # TODO: Show Day
    print(f"Day {player['day']}") 
    print("----- Sundrop Town -----")
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

def post_move(fog, player, game_map):
    clear_fog(fog, player)
    mine_tile(player, game_map)

def show_mine_menu(game_map, fog, player):
    #draw_map(game_map, fog, player)
    global game_state
    print(f"Day {player['day']}")
    draw_view(game_map, fog, player, size=VIEW_SIZE)
    print("----- MINE MENU -----")
    print("(WASD) to move")
    print(f"Turns left: {player['turns']}    Load: 0 / 12    Steps: 22")
    print("P = Portal")
    print("I = Information")
    print("M = Map")
    print("Q = Quit to Main Menu")
    print()
    playerinput = get_key("Action?")
    if playerinput == "p":
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
    elif try_step(playerinput, game_map, fog, player):
        post_move(fog, player, game_map)

def end_day(player):
    print("Your day is over! Heading back to town...")
    player['day'] += 1
    player['turns'] = TURNS_PER_DAY
    global game_state
    game_state = GAMESTATE_TOWN
    press_to_return()

#--------------------------- MAIN GAME ---------------------------
# TODO: The game!
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

