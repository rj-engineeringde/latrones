from . import global_variables as gl
from . import rules
from . import move_manager as move_mgr

from functools import cache


def create_bitboard_new_game(
        board_size_x, 
        board_size_y, 
        user_is_white=True
    ) :
    """Create a Binary Board at its initial state (new game)"""
    
    white_pieces = 0
    white_kings = 0
    black_pieces = 0
    black_kings = 0

    gl.update_global_variables(board_size_x, board_size_y)
    
    clear_cache_gameboard()
    move_mgr.clear_cache_move_mgr()
    rules.clear_cache_rules()

    for y in range(board_size_y):
        for x in range(board_size_x):
            index = get_bit_index(x, y)  # Flatten 2D to 1D

            if y == 0:
                # First row → opponent's non-king pieces
                if user_is_white:
                    black_pieces |= 1 << index
                else:
                    white_pieces |= 1 << index
            elif y == 1:
                # Second row → opponent's king in center (rounded to the left)
                center = (board_size_x - 1) // 2 if board_size_x % 2 == 0 else board_size_x // 2
                if x == center:
                    if user_is_white:
                        black_kings |= 1 << index
                    else:
                        white_kings |= 1 << index
            elif y == board_size_y - 2:
                # Second-to-last row → user's king in center (rounded to the right)
                center = (board_size_x // 2 if board_size_x % 2 == 0 else board_size_x // 2)
                if x == center:
                    if user_is_white:
                        white_kings |= 1 << index
                    else:
                        black_kings |= 1 << index
            elif y == board_size_y - 1:
                # Last row → user's non-king pieces
                if user_is_white:
                    white_pieces |= 1 << index
                else:
                    black_pieces |= 1 << index

    if gl.DEBUG_MODE:
        print('\nInitial Game State:')
        print(f"Board size: {board_size_x} x {board_size_y} = {board_size_x * board_size_y}")
        print_bitboard_matrixwise(white_pieces, white_kings, black_pieces, black_kings)

    if not no_piece_overlap(white_pieces, white_kings, black_pieces, black_kings):
        print_bitboard_bitwise(white_pieces, white_kings, black_pieces, black_kings)
        raise ValueError(f'There are overlaping pieces on the board (>1 piece per position)')

    return white_pieces, white_kings, black_pieces, black_kings


def print_bitboard_bitwise(
        white_pieces: int, 
        white_kings: int, 
        black_pieces: int, 
        black_kings: int,
        fill_zeros_left: bool = True
    ):
    """Print the bitwise values of all four pieces groups"""

    total_bits = gl.BOARD_SIZE_X * gl.BOARD_SIZE_Y

    print("")
    if fill_zeros_left:
        print(f"White Pieces : {bin(white_pieces)[2:].zfill(total_bits)}")
        print(f"White Kings  : {bin(white_kings)[2:].zfill(total_bits)}")
        print(f"Black Pieces : {bin(black_pieces)[2:].zfill(total_bits)}")
        print(f"Black Kings  : {bin(black_kings)[2:].zfill(total_bits)}")
    else:
        print(f"White Pieces : {bin(white_pieces)}")
        print(f"White Kings  : {bin(white_kings)}")
        print(f"Black Pieces : {bin(black_pieces)}")
        print(f"Black Kings  : {bin(black_kings)}")
    print("")


def print_bitmask_matrixwise(bitmask: int):
    """Print the bitmask in a matrix view."""

    def get_bit(bb, index): return (bb >> index) & 1

    print("")
    for y in range(gl.BOARD_SIZE_Y):
        row = []
        for x in range(gl.BOARD_SIZE_X):
            index = y * gl.BOARD_SIZE_X + x

            if get_bit(bitmask, index):
                row.append("1")
            else:
                row.append(".")

        print(" ".join(row))
    print()


def print_bitboard_matrixwise(
        white_pieces: int, 
        white_kings: int, 
        black_pieces: int, 
        black_kings: int
    ):
    """
    Print the full board with all four groups of pieces shown.
    Symbols:\n
      w = white piece
      W = white king
      b = black piece
      B = black king
      . = empty cell
    """

    def get_bit(bb, index): return (bb >> index) & 1

    print("")
    for y in range(gl.BOARD_SIZE_Y):
        row = []
        for x in range(gl.BOARD_SIZE_X):
            index = y * gl.BOARD_SIZE_X + x

            # Priority: kings over regular pieces
            if get_bit(white_kings, index):
                row.append("W")
            elif get_bit(white_pieces, index):
                row.append("w")
            elif get_bit(black_kings, index):
                row.append("B")
            elif get_bit(black_pieces, index):
                row.append("b")
            else:
                row.append(".")

        print(" ".join(row))
    print()


@cache
def get_bit_index(x: int, y: int):
    '''Flatten 2D to 1D\n
    Get the index in a bitwise board from its x-y-position on the matrix-like representation'''
    return y * gl.BOARD_SIZE_X + x 


def no_piece_overlap(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int
    ) -> bool:
    """
    Return True if no square has more than one piece on it.
    Otherwise, return False.
    """
    return not (
        (white_pieces & white_kings) or
        (white_pieces & black_pieces) or
        (white_pieces & black_kings) or
        (white_kings & black_pieces) or
        (white_kings & black_kings) or
        (black_pieces & black_kings)
    )


@cache
def shift_right(pos_mask: int, reverse: bool = False) -> int:
        if reverse:
            return shift_left(pos_mask)

        # If the position is in the rightmost column, can't move right
        if pos_mask & gl.RIGHT_COL_MASK:
            return 0
        return pos_mask << 1


@cache
def shift_left(pos_mask: int, reverse: bool = False) -> int:
        if reverse:
            return shift_right(pos_mask)

        # If the position is in the leftmost column, can't move left
        if pos_mask & gl.LEFT_COL_MASK:
            return 0
        return pos_mask >> 1


@cache
def shift_down(pos_mask: int, reverse: bool = False) -> int:
        if reverse:
            return shift_up(pos_mask)

        # If the position is in the bottom row, can't move down
        if pos_mask & gl.BOTTOM_ROW_MASK:
            return 0
        return pos_mask << gl.BOARD_SIZE_X


@cache
def shift_up(pos_mask: int, reverse: bool = False) -> int:
        if reverse:
            return shift_down(pos_mask)

        # If the position is in the top row, can't move up
        if pos_mask & gl.TOP_ROW_MASK:
            return 0
        return pos_mask >> gl.BOARD_SIZE_X


def clear_cache_gameboard():
    shift_right.cache_clear()
    shift_left.cache_clear()
    shift_up.cache_clear()
    shift_down.cache_clear()
    get_bit_index.cache_clear()
