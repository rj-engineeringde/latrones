from . import rules as rules
from . import gameboard as gameboard
from . import global_variables as gl
from functools import cache


def find_legal_moves_on_bitboard(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        moving_white: bool
    ):

    my_pieces = white_pieces if moving_white else black_pieces
    my_kings = white_kings if moving_white else black_kings
    my_all = my_pieces | my_kings

    legal_moves = []

    while my_all:
        cur_mask = my_all & -my_all  # Isolate lowest set bit
        legal_moves.extend(
            find_legal_moves_for_position(
                white_pieces,
                white_kings,
                black_pieces,
                black_kings,
                cur_mask,
                moving_white
            )
        )
        my_all ^= cur_mask  # Remove that bit from the bitboard

    return legal_moves


def find_legal_moves_for_position(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        cur_mask: int,
        moving_white: bool,
    ) -> list[tuple[int, int]]:
    """
    Returns a list of legal moves (cur_mask, dst_mask) for a piece at `cur_mask`.
    """

    all_pieces = white_pieces | white_kings | black_pieces | black_kings
    my_pieces = white_pieces if moving_white else black_pieces
    my_kings = white_kings if moving_white else black_kings
    opp_pieces = black_pieces if moving_white else white_pieces
    opp_kings = black_kings if moving_white else white_kings
    king_moving = bool(my_kings & (cur_mask))

    legal_moves = []

    for shift_func in (
        gameboard.shift_right, gameboard.shift_left,
        gameboard.shift_down, gameboard.shift_up,
    ):
        step_mask = cur_mask
        first_step = True
        first_step_occupied = False

        while True:
            step_mask = shift_func(step_mask, gl.BOARD_SIZE_X)
            if step_mask == 0:
                break  # Off board

            occupied = bool(all_pieces & step_mask)

            if first_step:
                if occupied:
                    first_step_occupied = True

            if king_moving:
                if occupied and first_step_occupied:
                    continue  # Blocked by second piece
                elif occupied and not first_step_occupied:
                    break
                elif not occupied and first_step_occupied:
                    if rules.is_legal_move(
                        white_pieces, white_kings,
                        black_pieces, black_kings,
                        cur_mask, step_mask,
                        moving_white
                    ):
                        legal_moves.append((cur_mask, step_mask))
                    break
                elif not occupied and not first_step_occupied:
                    legal_moves.append((cur_mask, step_mask))
                else:
                    raise ValueError(f"{occupied=}, {first_step_occupied=}")
            else:
                if occupied:
                    break
                else:
                    if rules.is_legal_move(
                        white_pieces, white_kings,
                        black_pieces, black_kings,
                        cur_mask, step_mask,
                        moving_white
                    ):
                        legal_moves.append((cur_mask, step_mask))

            first_step = False

    return legal_moves


def move(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        cur_mask: int,
        dst_mask: int,
        moving_white: bool
    ) -> tuple[tuple[int, int, int, int],# New bitboard
               tuple[int, int]]:         # Winner
    """Moves piece from current position to destination on the bitboard
    
    Return:
    - Tupple[white_pieces, white_kings, black_pieces, black_kings], Tupple[white_wins, black_wins]
    """

    all_pieces = white_pieces | white_kings | black_pieces | black_kings

    # Check if index out of bounds
    if not rules.__is_within_bounds_of_board(cur_mask) or not rules.__is_within_bounds_of_board(cur_mask):
        print('\nMoving failed\n')
        print(f'Move Error: Index out of board bounds.')
        gameboard.print_bitboard_matrixwise(white_pieces, white_kings, black_pieces, black_kings)
        gameboard.print_bitmask_matrixwise((cur_mask | dst_mask))
        raise ValueError(f'Move Error: Index out of board bounds.')

    # Check if there's a piece at current index
    if not all_pieces & cur_mask:
        print('\nMoving failed\n')
        print(f'Move Error: No piece at current position.')
        gameboard.print_bitboard_matrixwise(white_pieces, white_kings, black_pieces, black_kings)
        gameboard.print_bitmask_matrixwise((cur_mask | dst_mask))
        raise ValueError(f'Move Error: No piece at current position.')

    # Check if destination is empty
    if all_pieces & dst_mask:
        print('\nMoving failed\n')
        print(f'Move Error: Destination square is occupied.')
        gameboard.print_bitboard_matrixwise(white_pieces, white_kings, black_pieces, black_kings)
        gameboard.print_bitmask_matrixwise((cur_mask | dst_mask))
        raise ValueError(f'Move Error: Destination square is occupied.')

    # Apply Move
    (white_pieces_new, white_kings_new, 
     black_pieces_new, black_kings_new, captured_mask) = apply_move(
            white_pieces, 
            white_kings, 
            black_pieces, 
            black_kings,
            cur_mask,
            dst_mask
        )
    all_pieces_new = white_pieces | white_kings | black_pieces | black_kings

    # Was the move legal?
    if rules.is_legal_move(
        white_pieces, # pieces before moving
        white_kings, 
        black_pieces,
        black_kings,
        cur_mask,
        dst_mask,
        moving_white,
        captured_mask
    ):
        # Check for winner
        white_wins, black_wins = rules.check_for_winner(
                white_pieces_new,
                white_kings_new,
                black_pieces_new,
                black_kings_new
            )

        return (white_pieces_new, white_kings_new, 
               black_pieces_new, black_kings_new), (white_wins, black_wins)
    else:
        print('\nMoving failed\n')
        print(f'Move Error: Ilegal move.')
        gameboard.print_bitboard_matrixwise(white_pieces, white_kings, black_pieces, black_kings)
        gameboard.print_bitmask_matrixwise((cur_mask | dst_mask))
        raise ValueError(f'Move Error: Ilegal move.')
    

def apply_move(
        white_pieces: int, 
        white_kings: int, 
        black_pieces: int, 
        black_kings: int,
        cur_mask: int,
        dst_mask: int,
    ) -> tuple[tuple[int, int, int, int, int]]:
    """Applies the move from current position to destination on the bitboard.
    This function does NOT check if the move is legal, which turn it is, etc. 
    It only applies the operation of conducting the move itself.\n
    Return: white_pieces, white_kings, black_pieces, black_kings, captured_mask
    """

    # Relocate pieces (apply move)
    if white_kings & cur_mask:
        white_kings = __relocate_piece_on_bitmask(white_kings, cur_mask, dst_mask)
    elif white_pieces & cur_mask:
        white_pieces = __relocate_piece_on_bitmask(white_pieces, cur_mask, dst_mask)
    elif black_kings & cur_mask:
        black_kings = __relocate_piece_on_bitmask(black_kings, cur_mask, dst_mask)
    elif black_pieces & cur_mask:
        black_pieces = __relocate_piece_on_bitmask(black_pieces, cur_mask, dst_mask)

    # Get captured pieces
    captured_mask = rules.find_captures_after_move(
        white_pieces,
        white_kings,
        black_pieces,
        black_kings,
        dst_mask,
    )

    # Remove captured pieces from all relevant bitboards
    white_pieces &= ~captured_mask
    white_kings  &= ~captured_mask
    black_pieces &= ~captured_mask
    black_kings  &= ~captured_mask

    return white_pieces, white_kings, black_pieces, black_kings, captured_mask


@cache
def __relocate_piece_on_bitmask(
        pieces_bitmask: int,
        cur_mask: int,
        dst_mask: int
    ):
    """Helper function: Apply transformation on bitmask (e.g. white_kings) to relocate piece"""
    return (pieces_bitmask ^ cur_mask) | dst_mask


def clear_cache_move_mgr():
    __relocate_piece_on_bitmask.cache_clear()

