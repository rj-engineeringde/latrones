
from . import global_variables as gl
from . import gameboard as gameboard
from . import move_manager as move_mgr
from functools import cache


def check_for_winner(
        white_pieces: int, 
        white_kings: int, 
        black_pieces: int, 
        black_kings: int
    ) -> tuple[bool, bool]:
    """Check if someone won\n
    Return: Tuple[white_wins: Bool, black_wins: Bool]
    """
    white_loses = white_pieces == 0 or white_kings == 0
    black_loses = black_pieces == 0 or black_kings == 0

    return (black_loses, white_loses)


def is_legal_move(
        white_pieces: int, # pieces before moving
        white_kings: int, 
        black_pieces: int, 
        black_kings: int,
        cur_mask: int, 
        dst_mask: int,
        moving_white: bool,
        captured_mask: int = None
    ) -> bool:
    '''Check if a given move is legal'''
            
    all_pieces = white_pieces | white_kings | black_pieces | black_kings

    # Get mask of moving and opponent pieces and kings
    if (white_pieces | white_kings) & cur_mask and moving_white:
        moving_kings = white_kings
        moving_pieces = white_pieces
        opponent_kings = black_kings
        opponent_pieces = black_pieces
    elif not moving_white:
        moving_kings = black_kings
        moving_pieces = black_pieces
        opponent_kings = white_kings
        opponent_pieces = white_pieces
    else:
        return False # Not current turn of moving piece
    
    if not __is_valid_board_move_geometry(cur_mask, dst_mask):
        return False

    if not all_pieces & cur_mask: # Check if there's a piece at current index
        return False
    
    if all_pieces & dst_mask: # Check if destination is empty
        return False
    
    cur_y, cur_x = divmod(cur_mask.bit_length()-1, gl.BOARD_SIZE_X)
    dst_y, dst_x = divmod(dst_mask.bit_length()-1, gl.BOARD_SIZE_X)

    cnt_obstructing_pieces = __count_obstructing_pieces(
        all_pieces,
        cur_x, cur_y,
        dst_x, dst_y
    )
    
    # Is legal move?
    # -- Path free (No figures between cur and dst)
    if cnt_obstructing_pieces == 0:
        # Check if my king is orthogonaly touching the moved piece. 

        for shift_func in (
            gameboard.shift_right, gameboard.shift_left,
            gameboard.shift_down, gameboard.shift_up,
        ):
            shifted_mask = shift_func(dst_mask)
            
            if shifted_mask == 0:
                continue  # Out of bounds, e.g. tried to shift off the board

            if __is_within_bounds_of_board(shifted_mask):
                if moving_kings & shifted_mask:
                    if captured_mask == None:
                        (white_pieces_new, white_kings_new,
                         black_pieces_new, black_kings_new, 
                         captured_mask) = move_mgr.apply_move(
                            white_pieces,
                            white_kings,
                            black_pieces,
                            black_kings,
                            cur_mask,
                            dst_mask
                        )

                    if captured_mask & moving_kings:
                        return False # Moving captures my own king
        return True

    # -- Path full with pieces and moved piece is a king
    elif cnt_obstructing_pieces == ( abs(dst_x - cur_x) + abs(dst_y - cur_y) - 1 ) and ( (white_kings | black_kings) & cur_mask ): 
        if captured_mask == None:
            (white_pieces_new, white_kings_new,
             black_pieces_new, black_kings_new, captured_mask) = move_mgr.apply_move(
                white_pieces,
                white_kings,
                black_pieces,
                black_kings,
                cur_mask,
                dst_mask
            )
        
        # Is any opponent piece/king captured AND my own king is not captured
        if (captured_mask & (opponent_kings | opponent_pieces)) and not (captured_mask & moving_kings): 
            return True
        else:
            return False
    else:
        return False


def find_captures_after_move(
        white_pieces_aftermove: int,
        white_kings_aftermove: int,
        black_pieces_aftermove: int,
        black_kings_aftermove: int,
        dst_mask: int,
    ) -> int:
    """
    Returns a bitmask of all captured pieces and kings.
    """

    all_pieces_aftermove = white_pieces_aftermove | white_kings_aftermove | black_pieces_aftermove | black_kings_aftermove
    captured_mask = 0

    # Get moving color
    moving_white = bool((white_pieces_aftermove | white_kings_aftermove) & dst_mask)

    # Opponent line-trap capture - Capture opponent pieces if trapped between two own figures
    trapped = __find_trapped_along_line( 
            white_pieces_aftermove, 
            white_kings_aftermove, 
            black_pieces_aftermove, 
            black_kings_aftermove,
            moving_white,
            dst_mask,
        )
    captured_mask |= trapped

    # Opponent king capture
    opp_king_mask = black_kings_aftermove if moving_white else white_kings_aftermove
    if __is_king_trapped(opp_king_mask, all_pieces_aftermove):
        captured_mask |= opp_king_mask

    # Opponent corner group capture
    my_mask = (white_pieces_aftermove | white_kings_aftermove) if moving_white else (black_pieces_aftermove | black_kings_aftermove)
    opp_mask = (black_pieces_aftermove | black_kings_aftermove) if moving_white else (white_pieces_aftermove | white_kings_aftermove)

    # Find captured groups
    for shift_func in (
        gameboard.shift_right, gameboard.shift_left,
        gameboard.shift_down, gameboard.shift_up,
    ):
        shifted_mask = shift_func(dst_mask)
        if (opp_mask & shifted_mask) != 0:
            group = __find_trapped_group(
                opponent_mask=opp_mask,
                all_pieces=all_pieces_aftermove,
                to_explore=shifted_mask
            )
            captured_mask |= group

    # My own king capture
    all_pieces_aftermove ^= captured_mask # Eliminate opponent captured pieces
    my_king_mask = white_kings_aftermove if moving_white else black_kings_aftermove
    if __is_king_trapped(my_king_mask, all_pieces_aftermove):
        captured_mask |= my_king_mask

    return captured_mask


def __find_trapped_group(
        opponent_mask: int, # Kings and normal pieces of the group
        all_pieces: int, # All piecees on bitboard
        to_explore: int
    ) -> int:
    """
    Performs a flood fill starting from `opponent_mask` to find all connected opponent pieces.
    Returns a bitmask of the connected group (0 if group not trapped).
    """
    visited = 0
    group = 0

    if not (opponent_mask & to_explore):
        raise ValueError('start_idx not in opponent_mask')

    while to_explore:
        current = to_explore & -to_explore  # isolate lowest set bit
        to_explore ^= current             # remove it from to_explore
        current_idx = current.bit_length() - 1
        current_mask = 1 << current_idx

        if visited & current:
            continue

        visited |= current
        group |= current

        for shift_func in (
            gameboard.shift_right, gameboard.shift_left,
            gameboard.shift_down, gameboard.shift_up,
        ):
            neighbor_mask = shift_func(current_mask)
            if neighbor_mask == 0:
                continue  # Shift moved outside the board

            if (opponent_mask & neighbor_mask) and not (visited & neighbor_mask):
                to_explore |= neighbor_mask # opponent on neighbor
            elif not (all_pieces & neighbor_mask):
                return 0  # Group not fully trapped
    
    return group


def __is_king_trapped(
        king_mask: int,
        all_pieces: int
    ) -> bool:
    """
    Check if a king is surrounded on all orthogonal sides.
    A king is trapped if every orthogonal neighbor is occupied.
    """

    for shift_func in (
        gameboard.shift_right, gameboard.shift_left,
        gameboard.shift_down, gameboard.shift_up,
    ):
        neighbor_mask = shift_func(king_mask)
        if neighbor_mask != 0 and (all_pieces & neighbor_mask) == 0:
            return False  # Found at least one empty adjacent square → not trapped

    return True  # All orthogonal directions blocked


def __find_trapped_along_line(
        white_pieces_aftermove: int,
        white_kings_aftermove: int,
        black_pieces_aftermove: int,
        black_kings_aftermove: int,
        moving_white: bool,
        dst_mask: int,    # Dastination of the move
    ) -> int:
    """Find all opponent pieces (not Kings) in one direction that are captured 
    because being trapped between two own figures in a line"""

    trapped_mask = 0

    all_pieces_aftermove = white_pieces_aftermove | white_kings_aftermove | black_pieces_aftermove | black_kings_aftermove
    if moving_white:
        opponent_pieces = black_pieces_aftermove
        opponent_kings = black_kings_aftermove
        my_pieces_and_kings = white_pieces_aftermove | white_kings_aftermove
        opponent_pieces_and_kings = opponent_pieces | opponent_kings
    else:
        opponent_pieces = white_pieces_aftermove
        opponent_kings = white_kings_aftermove
        my_pieces_and_kings = black_pieces_aftermove | black_kings_aftermove
        opponent_pieces_and_kings = opponent_pieces | opponent_kings


    for shift_func in (
        gameboard.shift_right, gameboard.shift_left,
        gameboard.shift_down, gameboard.shift_up,
    ):
        buffer = 0
        forward_mask = shift_func(dst_mask)
        backward_mask = shift_func(dst_mask, reverse=True)

        if forward_mask == 0:
            continue  # Forward direction out of bounds

        # Check if both neighbors are opponents
        if (
            (opponent_pieces_and_kings & forward_mask) and
            (opponent_pieces_and_kings & backward_mask)
        ):
            continue

        # Lineary trapped?
        while forward_mask:
            if not (all_pieces_aftermove & forward_mask):
                break  # Found empty square - not captured

            if (opponent_pieces & forward_mask):
                buffer |= forward_mask  # Potential capture
            elif (my_pieces_and_kings & forward_mask):
                trapped_mask |= buffer  # Surrounded: confirm capture
                break
            
            # Next Iteration
            forward_mask = shift_func(forward_mask)
            if forward_mask == 0:
                break  # Out of bounds

    return trapped_mask


@cache
def __is_within_bounds_of_board(pos_mask: int) -> bool:
    """Check if dst_mask is fully within the board_mask (i.e., a valid square)."""
    return (pos_mask & gl.BOARD_MASK) == pos_mask


@cache
def __is_orthogonal_move(cur_mask: int, dst_mask: int) -> bool:
    """
    Check if the move from cur_idx to dst_idx is orthogonal (same row or same column)
    in a flattened bitboard representation.
    """
    cur_y, cur_x = divmod(cur_mask.bit_length()-1, gl.BOARD_SIZE_X)
    dst_y, dst_x = divmod(dst_mask.bit_length()-1, gl.BOARD_SIZE_X)

    return cur_x == dst_x or cur_y == dst_y


@cache
def __is_valid_board_move_geometry(cur_mask: int, dst_mask: int) -> bool:
    """Helper function: Check if...
    - cur == dst
    - cur is in bounds of board
    - dst is in bounds of board
    - is orthogonal move
    """

    if cur_mask == dst_mask:
        return False
    
    if not __is_within_bounds_of_board(cur_mask):
        return False
    
    if not __is_within_bounds_of_board(dst_mask):
        return False
    
    if not __is_orthogonal_move(cur_mask, dst_mask):
        return False
    
    return True


def __count_obstructing_pieces(
        all_pieces: int,
        cur_x: int,
        cur_y:int,
        dst_x: int,
        dst_y: int
    ) -> int:
    """
    Count how many pieces lie between cur and dst on an orthogonal path
    """

    mask = __inbetween_squares_mask(
        cur_x,
        cur_y,
        dst_x,
        dst_y
    )
    return (all_pieces & mask).bit_count()


@cache
def __inbetween_squares_mask(
        cur_x: int, 
        cur_y: int,
        dst_x: int,
        dst_y: int
    ):
    """Helper function: Get bit-mask of all squares between two positions
    (excluding the start and end positions)"""

    # Vertical move 
    if cur_x == dst_x:
        if cur_y > dst_y:
            cur_y, dst_y = dst_y, cur_y
        mask = sum(1 << (y * gl.BOARD_SIZE_X + cur_x) for y in range(cur_y + 1, dst_y))

    # Horizontal move
    elif cur_y == dst_y:
        if cur_x > dst_x:
            cur_x, dst_x = dst_x, cur_x
        start = cur_y * gl.BOARD_SIZE_X + cur_x + 1
        end = cur_y * gl.BOARD_SIZE_X + dst_x
        width = end - start
        mask = ((1 << width) - 1) << start if width > 0 else 0

    # Not Orthogonal Move
    else:
        raise ValueError(f'cur_idx, dst_idx are not orthogonal!')
    
    return mask


def clear_cache_rules():
    __is_within_bounds_of_board.cache_clear()
    __is_orthogonal_move.cache_clear()
    __is_valid_board_move_geometry.cache_clear()
    __inbetween_squares_mask.cache_clear()
