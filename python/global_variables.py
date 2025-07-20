import json, os

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config(path) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file '{path}' not found.")
    with open(path, "r") as f:
        return json.load(f)



CONFIG = load_config(config_path)

DEBUG_MODE = CONFIG["debug_mode"]
DEBUG_ANALYZE_MINIMAX_TIME = CONFIG["debug_analyze_minimax_time"]

BOARD_SIZE_X = CONFIG["default_board_size_x"]
BOARD_SIZE_Y = CONFIG["default_board_size_y"]

BOARD_MASK = None
RIGHT_COL_MASK = None
LEFT_COL_MASK = None
TOP_ROW_MASK = None
BOTTOM_ROW_MASK = None

COLOR_LIGHT = 'light'
COLOR_DARK = 'dark'




def update_global_variables(board_size_x, board_size_y):
    """Updates the values of the global variables"""
    global BOARD_SIZE_X, BOARD_SIZE_Y
    global RIGHT_COL_MASK, LEFT_COL_MASK, TOP_ROW_MASK, BOTTOM_ROW_MASK
    global BOARD_MASK

    BOARD_SIZE_X = board_size_x
    BOARD_SIZE_Y = board_size_y

    BOARD_MASK = (1 << (BOARD_SIZE_X * BOARD_SIZE_Y)) - 1

    RIGHT_COL_MASK = __get_column_mask(board_size_x - 1, board_size_x, board_size_y)
    LEFT_COL_MASK = __get_column_mask(0, board_size_x, board_size_y)
    TOP_ROW_MASK = __get_top_row_mask(board_size_x)
    BOTTOM_ROW_MASK = __get_bottom_row_mask(board_size_x, board_size_y)


def __get_column_mask(col_idx: int, board_size_x: int, board_size_y: int) -> int:
    """Return a bitmask with bits set at all positions in a column."""
    mask = 0
    for row in range(board_size_y):
        mask |= 1 << (row * board_size_x + col_idx)
    return mask


def __get_top_row_mask(board_size_x: int) -> int:
    """Return a bitmask with bits set for the top row."""
    return (1 << board_size_x) - 1


def __get_bottom_row_mask(board_size_x: int, board_size_y: int) -> int:
    """Return a bitmask with bits set for the bottom row."""
    return ((1 << board_size_x) - 1) << (board_size_x * (board_size_y - 1))


