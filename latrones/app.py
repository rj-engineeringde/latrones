from dataclasses import dataclass
from flask import Flask, jsonify
from flask import render_template
from flask import request, redirect, url_for
from typing import List, Optional
from python import *


# --------------------------------------------------------------------------
# Config initialization
# --------------------------------------------------------------------------

@dataclass
class GameConfig:
    board_size_x: int = gl.CONFIG["default_board_size_x"]
    board_size_y: int = gl.CONFIG["default_board_size_y"]
    user_color: str = gl.COLOR_LIGHT if gl.CONFIG["default_user_is_white"] else gl.COLOR_DARK
    play_against_bot: bool = gl.CONFIG["default_play_against_bot"]
    game_time_seconds: int = gl.CONFIG["default_game_time_seconds"]

    def is_user_light(self):
        return True if self.user_color == gl.COLOR_LIGHT else False

config = GameConfig()


# --------------------------------------------------------------------------
# Definition of Piece Class
# --------------------------------------------------------------------------

class Piece:
    def __init__(self, color, is_king=False):
        self.color = color
        if color == gl.COLOR_DARK:
            self.opponent_color = gl.COLOR_LIGHT
        else:
            self.opponent_color = gl.COLOR_DARK

        if is_king:
            self.is_king = True
        else:
            self.is_king = False

    def become_king(self):
        """Sets king flag to true."""
        
        self.is_king = True

class LightPiece(Piece):
    def __init__(self, color=gl.COLOR_LIGHT):
        super().__init__(color)

class DarkPiece(Piece):
    def __init__(self, color=gl.COLOR_DARK):
        super().__init__(color)


# --------------------------------------------------------------------------
# Flask logic
# --------------------------------------------------------------------------

# Initialize Flask
app = Flask(__name__)


@app.route('/')
def index():
    '''Main page'''
    return redirect(url_for('play'))


@app.route('/play')
def play():
    '''Begin game'''

    global config

    gl.update_global_variables(config.board_size_x, config.board_size_y)

    (white_pieces, white_kings, 
     black_pieces, black_kings) = gameboard.create_bitboard_new_game(
        board_size_x=config.board_size_x, 
        board_size_y=config.board_size_y, 
        user_is_white=config.is_user_light()
    )

    board = __bitboard_to_board(
        white_pieces, 
        white_kings, 
        black_pieces, 
        black_kings,
        config.board_size_x,
        config.board_size_y
    )
    current_turn = gl.COLOR_LIGHT

    return render_template(
        'play.html', 
        board=__switch_board_view(board), 
        current_turn=current_turn,
        play_against_bot=config.play_against_bot,
        game_time_seconds=config.game_time_seconds,
        user_color=config.user_color
    )


@app.route('/restart', methods=['POST'])
def restart():
    '''Restart game with new settings'''

    global config

    config.game_time_seconds = int(request.form.get('game_time_seconds'))
    config.board_size_x = int(request.form.get('board_size'))
    config.user_color = request.form.get('user_color')
    config.play_against_bot = True if request.form.get('play_against_bot').lower() == 'true' else False

    gl.update_global_variables(config.board_size_x, config.board_size_y)

    (white_pieces, white_kings, 
     black_pieces, black_kings) = gameboard.create_bitboard_new_game(
        board_size_x=config.board_size_x, 
        board_size_y=config.board_size_y, 
        user_is_white=config.is_user_light()
    )

    board = __bitboard_to_board(
        white_pieces, 
        white_kings, 
        black_pieces, 
        black_kings,
        config.board_size_x,
        config.board_size_y
    )
    current_turn = gl.COLOR_LIGHT

    return render_template(
        'play.html', 
        board=__switch_board_view(board), 
        current_turn=current_turn,
        play_against_bot=config.play_against_bot,
        game_time_seconds=config.game_time_seconds,
        user_color=config.user_color
    )


@app.route('/possible_moves', methods=['POST'])
def possible_moves():
    '''Click on a piece'''

    if request.method == 'POST':

        current_turn = request.form['current_turn']
        board_size_x = int(request.form['board_size_x'])
        board_size_y = int(request.form['board_size_y'])

        # gl.update_global_variables(board_size_x, board_size_y)

        board = __prepare_board(request)
        (white_pieces, white_kings, 
         black_pieces, black_kings) = __board_to_bitboard(board)
        
        if current_turn == gl.COLOR_LIGHT:
            moving_white = True
        else:
            moving_white = False
        
        current_position = {
            'x': int(request.form['cur_x']),
            'y': int(request.form['cur_y'])
        }
        cur_idx = gameboard.get_bit_index(
            current_position['x'], 
            current_position['y']
        )
        cur_mask = 1 << cur_idx

        moves_list = move_mgr.find_legal_moves_for_position(
            white_pieces, 
            white_kings, 
            black_pieces, 
            black_kings,
            cur_mask,
            moving_white
        )

        dst_list = [move[1] for move in moves_list]
        possible_moves_2Dlist = __convert_pos_list_to_2Dposlist(
            dst_list,
            board_size_x
        )

        return jsonify(possible_moves_2Dlist)


@app.route('/move', methods=['POST'])
def move_piece():
    '''Move piece by user'''

    if request.method == 'POST':

        current_turn = request.form['current_turn']
        board_size_x = int(request.form['board_size_x'])
        board_size_y = int(request.form['board_size_y'])

        board = __prepare_board(request)
        (white_pieces, white_kings, 
         black_pieces, black_kings) = __board_to_bitboard(board)
        
        if current_turn == gl.COLOR_LIGHT:
            moving_white = True
        else:
            moving_white = False

        current_position = {
            'x': int(request.form['cur_x']),
            'y': int(request.form['cur_y'])
        }
        destination = {
            'x': int(request.form['dst_x']),
            'y': int(request.form['dst_y'])
        }

        cur_idx = gameboard.get_bit_index(
            current_position['x'], 
            current_position['y']
        )
        dst_idx = gameboard.get_bit_index(
            destination['x'], 
            destination['y']
        )
        
        cur_mask = 1 << cur_idx
        dst_mask = 1 << dst_idx
        
        ((white_pieces_new, white_kings_new, 
          black_pieces_new, black_kings_new),
         (white_wins, black_wins)
          )= move_mgr.move(
            white_pieces, 
            white_kings, 
            black_pieces, 
            black_kings,
            cur_mask,
            dst_mask,
            moving_white
        )

        board_new = __bitboard_to_board(
            white_pieces_new, 
            white_kings_new, 
            black_pieces_new, 
            black_kings_new,
            board_size_x,
            board_size_y
        )
        
        winner = __get_winner_as_string(white_wins, black_wins)
        current_turn = __get_opposite_color(current_turn) # Update value of current turn color after new move
        
        return render_template('_board_table.html',
            board=board_new,
            current_turn=current_turn,
            winner=winner,
            move_result=True, 
            move_error=None
        )


@app.route('/move_bot', methods=['POST'])
def move_bot():
    '''Move piece by bot'''

    if request.method == 'POST':

        current_turn = request.form['current_turn']
        board_size_x = int(request.form['board_size_x'])
        board_size_y = int(request.form['board_size_y'])

        board = __prepare_board(request)
        (white_pieces, white_kings, 
         black_pieces, black_kings) = __board_to_bitboard(board)
        
        if current_turn == gl.COLOR_LIGHT:
            moving_white = True
        else:
            moving_white = False

        cur_mask, dst_mask = bot.find_move_for_bot(
            white_pieces, 
            white_kings, 
            black_pieces, 
            black_kings,
            moving_white
        )

        ((white_pieces_new, white_kings_new, 
          black_pieces_new, black_kings_new),
         (white_wins, black_wins)
          )= move_mgr.move(
            white_pieces, 
            white_kings, 
            black_pieces, 
            black_kings,
            cur_mask,
            dst_mask,
            moving_white
        )
        
        board_new = __bitboard_to_board(
            white_pieces_new, 
            white_kings_new, 
            black_pieces_new, 
            black_kings_new,
            board_size_x,
            board_size_y
        )
        
        winner = __get_winner_as_string(white_wins, black_wins)
        current_turn = __get_opposite_color(current_turn)

        return render_template('_board_table.html',
            board=board_new,
            current_turn=current_turn,
            winner=winner,
            move_result=True, 
            move_error=None
        )


# --------------------------------------------------------------------------
# Generation of board from existing state
# --------------------------------------------------------------------------

def __prepare_board(request) -> list:
    '''Generate board with pieces'''

    board_size_x = int(request.form['board_size_x'])
    board_size_y = int(request.form['board_size_y'])
    pieces_count = int(request.form['pieces_count'])
    prepared_board = __generate_empty_board(board_size_x, board_size_y)

    for i in range(pieces_count):
        x = int(request.form['pieces['+str(i)+'][x]'])
        y = int(request.form['pieces['+str(i)+'][y]'])
        color = request.form['pieces['+str(i)+'][color]']
        king = request.form['pieces['+str(i)+'][king]'] == 'true'

        if color == 'DarkPiece':
            prepared_piece = DarkPiece()
        if color == 'LightPiece':
            prepared_piece = LightPiece()
        if king:
            prepared_piece.become_king()

        prepared_board[y][x] = prepared_piece

    return prepared_board


def __generate_empty_board(size_x: int, size_y: int) -> list:
    '''Generate empty board'''

    board = []

    for i in range(size_y):
        board.append([None]*size_x) # Empty row

    return board


# --------------------------------------------------------------------------
# Convertions betwen bitboard and board
# --------------------------------------------------------------------------

def __bitboard_to_board(white_pieces: int,
                        white_kings: int,
                        black_pieces: int,
                        black_kings: int,
                        board_size_x: int,
                        board_size_y: int) -> List[List[Optional[Piece]]]:
    """
    Convert bitboard representation to a 2D board representation.\n
    Returns a board of shape [board_size_y][board_size_x] with Piece instances or None.
    """
    def get_bit(bb, index):
        return (bb >> index) & 1

    board = []

    for y in range(board_size_y):
        row = []
        for x in range(board_size_x):
            index = y * board_size_x + x

            if get_bit(white_kings, index):
                row.append(Piece(color=gl.COLOR_LIGHT, is_king=True))
            elif get_bit(white_pieces, index):
                row.append(Piece(color=gl.COLOR_LIGHT, is_king=False))
            elif get_bit(black_kings, index):
                row.append(Piece(color=gl.COLOR_DARK, is_king=True))
            elif get_bit(black_pieces, index):
                row.append(Piece(color=gl.COLOR_DARK, is_king=False))
            else:
                row.append(None)
        board.append(row)

    return board


def __board_to_bitboard(board: List[List[Optional[Piece]]]) -> tuple[int, int, int, int]:
    """
    Convert a 2D board of Piece instances into bitboard representation.
    
    Returns:
        - white_pieces: int
        - white_kings: int
        - black_pieces: int
        - black_kings: int
    """
    white_pieces = 0
    white_kings = 0
    black_pieces = 0
    black_kings = 0

    board_size_y = len(board)
    board_size_x = len(board[0]) if board else 0

    gl.update_global_variables(board_size_x, board_size_y)

    for y in range(board_size_y):
        for x in range(board_size_x):
            piece = board[y][x]
            if piece is None:
                continue

            index = y * board_size_x + x

            if piece.color == gl.COLOR_LIGHT:
                if piece.is_king:
                    white_kings |= (1 << index)
                else:
                    white_pieces |= (1 << index)
            elif piece.color == gl.COLOR_DARK:
                if piece.is_king:
                    black_kings |= (1 << index)
                else:
                    black_pieces |= (1 << index)

    return white_pieces, white_kings, black_pieces, black_kings


# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------

def __print_board(board):
    """
    Print the board as a grid.
    Each cell shows:
      - 'l' for light piece
      - 'L' for light king
      - 'd' for dark piece
      - 'D' for dark king
      - '.' for empty square
    """

    for row in board:
        row_str = []
        for piece in row:
            if piece is None:
                row_str.append('.')
            else:
                if piece.color == gl.COLOR_LIGHT:
                    row_str.append('L' if piece.is_king else 'l')
                else:
                    row_str.append('D' if piece.is_king else 'd')
        print(" ".join(row_str))


def __switch_board_view(board):
    """
    Flip the board vertically.
    Returns a new board with the transformed view.
    """

    return board[::-1]


def __convert_pos_list_to_2Dposlist(
        pos_mask_list: list,
        board_size_x: int
    ):
    '''Convert a list of position masks [(cur_mask, dst_mask), ...] in bitboard 
    to a list containing for each position a list [[pos_x, pos_y], ...]'''

    pos_list = []

    for pos_mask in pos_mask_list:
        pos_idx = pos_mask.bit_length() - 1
        
        pos_y, pos_x = divmod(pos_idx, board_size_x)
        pos_list.append([pos_x, pos_y])
    
    return pos_list


def __get_opposite_color(my_color: str) -> str:
    """Get opposite color (COLOR_LIGHT or COLOR_DARK) from input color"""

    if my_color == gl.COLOR_LIGHT:
        return gl.COLOR_DARK
    elif my_color == gl.COLOR_DARK:
        return gl.COLOR_LIGHT
    

def __get_winner_as_string(white_wins: bool, black_wins: bool):
    '''Get winner as string COLOR_LIGHT, COLOR_DARK or None'''
    
    if white_wins and black_wins:
        raise ValueError(f"Both colors (Light and Dark) won at the same time!")
    elif white_wins:
        return gl.COLOR_LIGHT
    elif black_wins:
        return gl.COLOR_LIGHT
    else:
        return None
