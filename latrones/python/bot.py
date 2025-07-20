from . import global_variables as gl
from . import gameboard
from . import move_manager as move_mgr 
from . import rules

import cProfile, pstats, io, time

no_minmax_calls = 0

POINTS_KING = gl.CONFIG["minimax_points_per_king_capture"] # Number of points to gain by the capture of the king
POINTS_PIECE = gl.CONFIG["minimax_points_per_piece_capture"] # Number of points to gain by any captured piece
POINTS_MOVE_OPTION = gl.CONFIG["minimax_points_per_move_option"] # Number of points to gain by posible move

MAX_DEPTH = gl.CONFIG["minimax_max_depth"] # Max depth at normal situation
MAX_DEPTH_CAPTURE = gl.CONFIG["minimax_max_depth_capture"] # Max depth if capture happens
TIMEOUT_SEC = gl.CONFIG["minimax_timeout_sec"] # Timeout - Break minimax search after X seconds


def find_move_for_bot(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        moving_white: bool
    ) -> tuple[int, int]:
    """Calculate the best bot move given a board state \n
    Return: cur_mask, dst_mask"""

    global no_minmax_calls, MAX_DEPTH, TIMEOUT_SEC, MAX_DEPTH_CAPTURE
    no_minmax_calls = 0

    if gl.DEBUG_MODE:
        start_time = time.time()

        if gl.DEBUG_ANALYZE_MINIMAX_TIME:
            profiler = cProfile.Profile()
            profiler.enable()

    max_depth = MAX_DEPTH 
    timeout_sec = TIMEOUT_SEC
    max_depth_capture = MAX_DEPTH_CAPTURE

    white_wins, black_wins = rules.check_for_winner(
        white_pieces, 
        white_kings, 
        black_pieces, 
        black_kings
    )
    if white_wins or black_wins:
        raise ValueError(f'Someone won: {white_wins=}, {black_wins=}')

    is_white_maximized = moving_white
    cur_mask, dst_mask = __iterative_deepening_minimax(
        white_pieces, white_kings,
        black_pieces, black_kings,
        moving_white,
        max_depth,
        max_depth_capture,
        is_white_maximized,
        timeout_sec
    )

    if gl.DEBUG_MODE:
        elapsed_time = time.time() - start_time

        if gl.DEBUG_ANALYZE_MINIMAX_TIME:
            print('\ncProfile:\n')
            profiler.disable()
            stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
            stats.print_stats(30)  # Print top 30 lines
            print(stream.getvalue())

        print(f"\nBot move calculation took {elapsed_time:.3f} seconds.")
        print(f'Number of Minmax Calls: {no_minmax_calls}\n')

    return cur_mask, dst_mask


def __iterative_deepening_minimax(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        moving_white: bool,
        max_depth: int,
        max_depth_capture: int,
        is_white_maximized: bool,
        timeout_sec: float
    ) -> tuple[int, int]:
    """Conduct minmax algorithm iterativaly increasing the depth\n
    Return: best move --> (cur_mask, dst_mask)
    """

    ordered_moves = move_mgr.find_legal_moves_on_bitboard(
        white_pieces, white_kings,
        black_pieces, black_kings,
        moving_white
    )
    best_move = ordered_moves[0]
    start_time = time.time()

    for depth in range(max_depth-1, -1, -1):
        best_score = float('-inf')
        temp_best_move = None
        scored_moves = []

        for move in ordered_moves:
            cur_mask, dst_mask = move
            
            if time.time() - start_time > timeout_sec and best_move is not None:
                print(f'Timeout caused stop of minmax at a depth of {depth}')
                return best_move

            (white_pieces_new, white_kings_new, 
             black_pieces_new, black_kings_new, 
             captured_mask) = move_mgr.apply_move(
                white_pieces, white_kings,
                black_pieces, black_kings,
                cur_mask, dst_mask,
            )
            moving_white_new = not moving_white

            score_captures = __minimax_alpha_beta_prune(
                white_pieces_new,
                white_kings_new,
                black_pieces_new,
                black_kings_new,
                moving_white_new,
                depth=depth + 1,  # because we just made a move
                alpha=float('-inf'),
                beta=float('inf'),
                is_white_maximized=is_white_maximized,
                max_depth = max_depth,
                max_depth_capture = max_depth_capture,
                capture_chain_active = bool(captured_mask)
            )

            score_mobility = __evaluate_move_by_mobility(
                white_pieces_new, white_kings_new,
                black_pieces_new, black_kings_new,
                is_white_maximized
            )
            total_score = score_captures + score_mobility

            scored_moves.append((move, total_score))

            if total_score > best_score:
                best_score = total_score
                temp_best_move = move

        best_move = temp_best_move
        ordered_moves = [move for move, _ in sorted(scored_moves, key=lambda x: x[1], reverse=True)]
    return best_move


def __minimax_alpha_beta_prune(
        white_pieces: int,
        white_kings: int,
        black_pieces: int,
        black_kings: int,
        moving_white: str,
        depth: int, # Depth (Increases with every iteration until reaching max_depth)
        alpha: float,
        beta: float,
        is_white_maximized: bool, # Color to maximize/minimize is white or black?
        max_depth: int, # Absolute maximum depth allowed
        max_depth_capture: int, # Extended max. depth for captures
        capture_chain_active: bool, # Extended search when capture occurs
    ) -> int:
    """Minmax algorithm applying alpha beta pruning with extended search if capture occurs\n"""
    
    global no_minmax_calls
    no_minmax_calls += 1

    white_wins, black_wins = rules.check_for_winner(
        white_pieces, white_kings, 
        black_pieces, black_kings
    )

    evaluate = False

    if white_wins or black_wins:
        evaluate = True # Evaluate if someone wins

    if not capture_chain_active and depth >= max_depth:
        evaluate = True # Max. depth reached for normal moves (not captures)

    if depth >= max_depth_capture:
        evaluate = True # Max. depth reached for captures
        capture_chain_active = False

    if capture_chain_active and not evaluate:
        if not __is_noisy_position(white_pieces, white_kings, 
                                   black_pieces, black_kings,
                                   moving_white
                                   ):
            evaluate = True # "Quiet" position reached at capture search extension
            capture_chain_active = False

    # Evaluate move
    if evaluate:
        eval = __evaluate_move_by_captures(
            white_pieces, white_kings,
            black_pieces, black_kings,
            is_white_maximized
        )
        return eval

    # Find legal moves
    legal_moves = move_mgr.find_legal_moves_on_bitboard(
        white_pieces, white_kings, 
        black_pieces, black_kings,
        moving_white,
    )

    # Iterrative moving, deepening and evaluation
    is_maximizing_turn = (moving_white == is_white_maximized)
    if is_maximizing_turn:
        max_eval = float('-inf')
        for move in legal_moves:
            cur_mask, dst_mask = move

            # Apply move
            (white_pieces_new, white_kings_new, 
             black_pieces_new, black_kings_new, 
             captured_mask) = move_mgr.apply_move(
                white_pieces, white_kings,
                black_pieces, black_kings,
                cur_mask, dst_mask
            )
            moving_white_new = not moving_white

            # Next minimax iteration
            eval = __minimax_alpha_beta_prune(
                white_pieces_new, white_kings_new,
                black_pieces_new, black_kings_new,
                moving_white_new,
                depth=depth + 1,
                alpha=alpha,
                beta=beta,
                is_white_maximized=is_white_maximized,
                max_depth = max_depth,
                max_depth_capture = max_depth_capture,
                capture_chain_active = bool(captured_mask)
            )
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            cur_mask, dst_mask = move

            # Apply move
            (white_pieces_new, white_kings_new, 
             black_pieces_new, black_kings_new, 
             captured_mask) = move_mgr.apply_move(
                white_pieces, white_kings,
                black_pieces, black_kings,
                cur_mask,
                dst_mask
            )
            moving_white_new = not moving_white

            # Next minimax iteration
            eval = __minimax_alpha_beta_prune(
                white_pieces_new, white_kings_new,
                black_pieces_new, black_kings_new,
                moving_white_new,
                depth=depth + 1,
                alpha=alpha,
                beta=beta,
                is_white_maximized=is_white_maximized,
                max_depth = max_depth,
                max_depth_capture = max_depth_capture,
                capture_chain_active = bool(captured_mask)
            )
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval


def __evaluate_move_by_captures(
        white_pieces_aftermove: int,
        white_kings_aftermove: int,
        black_pieces_aftermove: int,
        black_kings_aftermove: int,
        maximize_white: bool
    ):
    """Evaluate a move by the captures conducted"""

    score = 0
    global POINTS_KING, POINTS_PIECE

    # Define points counting pieces
    white_kings_cnt = white_kings_aftermove.bit_count()
    black_kings_cnt = black_kings_aftermove.bit_count()
    white_pieces_cnt = white_pieces_aftermove.bit_count()
    black_pieces_cnt = black_pieces_aftermove.bit_count()
    white_piece_points = white_kings_cnt * POINTS_KING + white_pieces_cnt * POINTS_PIECE
    black_piece_points = black_kings_cnt * POINTS_KING + black_pieces_cnt * POINTS_PIECE

    # Calculate Score
    score = 0
    if maximize_white:
        score += white_piece_points - black_piece_points
    else:
        score -= white_piece_points - black_piece_points

    return score


def __evaluate_move_by_mobility(
        white_pieces_aftermove: int,
        white_kings_aftermove: int,
        black_pieces_aftermove: int,
        black_kings_aftermove: int,
        is_white_maximized: bool,
    ):
    """Get a score correction based on the mobility after move"""
    
    global POINTS_MOVE_OPTION
    score = 0

    mobility_white = __estimate_mobility(
        white_pieces_aftermove,
        white_kings_aftermove,
        black_pieces_aftermove,
        black_kings_aftermove,
        mycolor_is_white=True
    )
    mobility_black = __estimate_mobility(
        white_pieces_aftermove,
        white_kings_aftermove,
        black_pieces_aftermove,
        black_kings_aftermove,
        mycolor_is_white=False
    )
    white_mobility_points = mobility_white * POINTS_MOVE_OPTION
    black_mobility_points = mobility_black * POINTS_MOVE_OPTION

    if is_white_maximized:
        score += white_mobility_points - black_mobility_points
    else:
        score -= white_mobility_points - black_mobility_points

    return score


def __estimate_mobility(
    white_pieces: int,
    white_kings: int,
    black_pieces: int,
    black_kings: int,
    mycolor_is_white: bool
) -> int:
    """Estimate number of orthogonal positions all pieces of a color can access."""

    all_pieces = white_pieces | white_kings | black_pieces | black_kings
    my_pieces = white_pieces | white_kings if mycolor_is_white else black_pieces | black_kings

    mobility = 0

    pieces = my_pieces
    while pieces:
        cur_mask = pieces & -pieces  # Isolate lowest bit

        for shift_func in (
            gameboard.shift_right, gameboard.shift_left,
            gameboard.shift_down, gameboard.shift_up,
        ):
            shifted = cur_mask
            while True:
                shifted = shift_func(shifted)
                if shifted == 0 or (shifted & gl.BOARD_MASK) == 0:
                    break  # Off board
                if shifted & all_pieces:
                    break  # Blocked by a piece
                mobility += 1

        pieces ^= cur_mask  # Remove processed piece

    return mobility


def __is_noisy_position(
    white_pieces: int,
    white_kings: int,
    black_pieces: int,
    black_kings: int,
    moving_white: bool
) -> bool:
    """
    Returns True if a capture move is available in this position.
    """

    legal_moves = move_mgr.find_legal_moves_on_bitboard(
        white_pieces,
        white_kings,
        black_pieces,
        black_kings,
        moving_white
    )

    for move in legal_moves:
        cur_mask, dst_mask = move

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

        if captured_mask:
            return True

    return False

