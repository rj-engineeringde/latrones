// Define static global variables
COLOR_LIGHT = 'light'
COLOR_DARK = 'dark'


// Start the function bind_events() after loading the HTML
$(document).ready(
    bind_events,
    initialize_variables(),
    reset_user_time(NewGameSettings.game_time_seconds),
);


// Initialize
function initialize_variables() {
    // Is game running?
    window.isGameRunning = false;

    // Buttons
    window.newGameBtn = document.getElementById('new_game_btn');

    // Inputs
    // window.botLevelInput = document.getElementById('bot_level'); // Bot level setting disabled
    window.boardSizeInput = document.getElementById('board_size');
    window.timeInput_sec = document.getElementById('game_time_seconds');

    // User-specific-time
    window.lightTime_sec = parseInt(NewGameSettings.game_time_seconds);
    window.darkTime_sec = parseInt(NewGameSettings.game_time_seconds);

    // Displays
    // window.botLevelDisplay = document.getElementById('bot_level_display'); // Bot level setting disabled
    window.boardSizeDisplay = document.getElementById('board_size_display');
    window.timeDisplay = document.getElementById('game_time_display');

    // Time displays for each player
    window.lightTimeDisplay = document.getElementById('light_time_display');
    window.darkTimeDisplay = document.getElementById('dark_time_display');

    // Winner display 
    window.winnerDisplay = document.getElementById("winner_display");

    // Radio buttons
    window.userColorInput = document.querySelector('input[name="user_color"]:checked');
    window.playAgainstBotInput = document.querySelector('input[name="play_against_bot"]:checked');

    // Update Setting values
    window.timeInput_sec.value = NewGameSettings.game_time_seconds;
    window.boardSizeInput.value = $('.board').find('tr').first().find('td').length;
    // window.botLevelInput.value = NewGameSettings.bot_level; // Bot level setting disabled

    // Immediately update displayed values from slider's
    window.timeDisplay.value = format_time_for_display(NewGameSettings.game_time_seconds) //(window.timeInput_sec.value);
    // window.botLevelDisplay.value = NewGameSettings.bot_level; // Bot level setting disabled
    window.boardSizeDisplay.value = window.boardSizeInput.value;

    // Update radio button for user color
    document.querySelectorAll('input[name="user_color"]').forEach(radio => {
      radio.checked = (radio.value === NewGameSettings.user_color);
    });

    // Update radio button for play against bot
    document.querySelectorAll('input[name="play_against_bot"]').forEach(radio => {
      radio.checked = (radio.value === String(NewGameSettings.play_against_bot).toLowerCase());
    });
}


// Reset user's time
function reset_user_time(time_sec) {
    // Clear and restart clock interval
    if (window.clockInterval) {
      clearInterval(window.clockInterval);
      window.clockInterval = null;
    }

    window.isGameRunning = false;

    // Reset the time values
    window.lightTime_sec = parseInt(time_sec);
    window.darkTime_sec = parseInt(time_sec);

    // Update displayed user time
    window.lightTimeDisplay.textContent = format_time_for_display(time_sec);
    window.darkTimeDisplay.textContent = format_time_for_display(time_sec);
}


// Pause user's time
function pause_user_time() {
    // Stop the clock interval
    if (window.clockInterval) {
        clearInterval(window.clockInterval);
        window.clockInterval = null;
    }

    // Mark the game as not running
    window.isGameRunning = false;
}


// Start Counting Time
function start_cnt_time() {
    // Update the time every 1000 ms
    if (!window.isGameRunning) {
      window.clockInterval = setInterval(update_user_time, 1000);
      window.isGameRunning = true;
    }
}


// Bind events
function bind_events() {

    // Define movement variables
    var current_position;
    var destination;
    var $selected_piece;

    let playAgainstBot = String(NewGameSettings.play_against_bot).toLowerCase() === 'true';
    let bot_color = (NewGameSettings.user_color === COLOR_LIGHT) ? COLOR_DARK : COLOR_LIGHT;

    // Detect Winner
    display_winner(GameConfig.winner);

    // Event: Click Start Button
    $('#start-game-btn').off('click').on('click', function () {
      // 1. Start the timer
      start_cnt_time(NewGameSettings.game_time_seconds);

      // 2. Hide the overlay
      $('#play-overlay').fadeOut(100);

      // 3. Disable the button
      $(this).prop('disabled', true);

      maybe_make_bot_move()
    });

    // Event: Hoover over valid piece
    if (GameConfig.winner !== 'light' && GameConfig.winner !== 'dark') {
      if ((playAgainstBot && GameConfig.current_turn !== bot_color) || (!playAgainstBot)) {
        $('.board__square').off('mouseenter mouseleave').hover( function () {
          // Mouse enters square
          var $selected_piece = $(this).find('.board__piece').first();

          if ($selected_piece.length) {
            var isDark = $selected_piece.hasClass('board__piece--dark');
            var isLight = $selected_piece.hasClass('board__piece--light');

            if ((isDark && GameConfig.current_turn === COLOR_DARK) ||
                (isLight && GameConfig.current_turn === COLOR_LIGHT)) {
              $(this).addClass('board__square--hovered');
            }
          }
        },
        function () {
          // Mouse leaves square — always remove visual highlight
          $(this).removeClass('board__square--hovered');
        });
      }
    }

    // Event: Click on square
    if (GameConfig.winner !== 'light' && GameConfig.winner !== 'dark') {
      if ((playAgainstBot && GameConfig.current_turn !== bot_color) || (!playAgainstBot)) {
        $('.board__square').off('click').on('click', function () {
          
          var found_piece_on_the_square = $(this).find('.board__piece').length; // Check if the selected square has a piece

          // Case 1: Square has a piece
          if (found_piece_on_the_square) {
            $piece = $(this).find('.board__piece').first();
            
            var isDark = $piece.hasClass('board__piece--dark');
            var isLight = $piece.hasClass('board__piece--light');

            // Check if piece has the correct color
            if ((isDark && GameConfig.current_turn !== COLOR_DARK) ||
                (isLight && GameConfig.current_turn !== COLOR_LIGHT)) {
              return;
            }

            // Valid piece - select it
            $selected_piece = $piece
            current_position = {
              // data-y, data-y
              x: $(this).data('x'),
              y: $(this).data('y'),

              // Actual pixel position
              offset_left: $(this).offset().left,
              offset_top: $(this).offset().top
            }

            $('.board__square').removeClass('board__square--selected'); // Remove selection layout from all squares
            $(this).addClass('board__square--selected'); // Add selection layout to the current square
            $('.board__square').removeClass('board__square--optionalmove'); // Remove all old optional move highlights

            // Highlight possible moves
            $.post('/possible_moves',
              {
                cur_x: current_position.x,
                cur_y: current_position.y,
                pieces: pieces_on_board(),
                pieces_count: pieces_on_board().length,
                board_size_x: $('tr').first().find('td').length,
                board_size_y: $('tr').length,
                current_turn: GameConfig.current_turn,
              },
              function (data, status) {
                data.forEach(function (pos) {
                  $(`.board__square[data-x="${pos[0]}"][data-y="${pos[1]}"]`).addClass('board__square--optionalmove');
                });
              }
            );

          // Case 2: Piece not selected and and square does not have a piece
          } else if (current_position === undefined) {
            return;

          // Case 3: Piece selected, destination choosen
          } else {
            // Only allow moving to a highlighted optional move square
            if (!$(this).hasClass('board__square--optionalmove')) {
              return;
            }

            // Select destination
            destination = {
              x: $(this).data('x'),
              y: $(this).data('y'),
              offset_left: $(this).offset().left,
              offset_top: $(this).offset().top
            }

            // Move piece
            var translate_x = destination.offset_left - current_position.offset_left;
            var translate_y = destination.offset_top - current_position.offset_top;

            $selected_piece.css({
              transform: 'translate(' + translate_x + 'px, ' + translate_y + 'px)',
              transition: 'transform .3s'
            });

            var pieces = pieces_on_board();

            // Send updated data to the backend [py fct. move()], update page and rerun bind_events
            $.post('/move',
              {
                cur_x: current_position.x,
                cur_y: current_position.y,
                dst_x: destination.x,
                dst_y: destination.y,
                pieces: pieces,
                pieces_count: pieces.length,
                board_size_x: $('tr').first().find('td').length,
                board_size_y: $('tr').length,
                current_turn: GameConfig.current_turn,
              },
              function (data, status) {
                setTimeout(function () {
                  // $('body').html(data); // Update boddy (returned updated board html from flask)
                  $('#board_with_figures_id').html(data);
                  
                  bind_events(); // Rerun bind_events
                  update_turn_indicators();
                  maybe_make_bot_move()
                }, 300);
              }
            );
          }
        });
      }
    }

    // Event: Click Restart Game Button
    $('#new_game_btn').off('click').on('click', function () {
      if (window.isGameRunning) {
        const confirmRestart = confirm("Do you really want to restart the game?");
        if (!confirmRestart) return;
      }

      // let botLevel = window.botLevelInput.value; // Bot level setting disabled
      let gameTime = window.timeInput_sec.value;
      let boardSize = window.boardSizeInput.value;
      let userColorInput = document.querySelector('input[name="user_color"]:checked').value;
      let playAgainstBotInput = document.querySelector('input[name="play_against_bot"]:checked').value;

      // Send settings to Flask via POST
      $.post('/restart', {
          // bot_level: botLevel, // Bot level setting disabled
          game_time_seconds: gameTime,
          board_size: boardSize,
          user_color: userColorInput,
          play_against_bot: playAgainstBotInput
        },
        function (data, status) {
          $('body').html(data);

          // Re-initialize everything
          initialize_variables();
          bind_events();
          update_turn_indicators();
          reset_user_time(NewGameSettings.game_time_seconds)
        }
      );
    });

    // Edit Settings
    // window.botLevelInput.addEventListener('input', function () { // Bot level setting disabled
    //   window.botLevelDisplay.value = this.value;
    // });
    window.timeInput_sec.addEventListener('input', function () {    
      window.timeDisplay.value = format_time_for_display(this.value);
    });
    window.boardSizeInput.addEventListener('input', function () {
      window.boardSizeDisplay.value = this.value;
    });
}


function display_winner(winner) {
    
    let winnerText = ''

    if (winner == COLOR_LIGHT){
      winnerText = 'White won!'
      pause_user_time()
    }

    if (winner == COLOR_DARK){
      winnerText = 'Black won!'
      pause_user_time()
    }

    winnerDisplay.textContent = winnerText;
}


function disable_user_interaction() {
    $('.board__square').off('click');
    $('.board__square').off('mouseenter mouseleave');
}


function pieces_on_board() {
    var board_state = [];

    $('.board__piece').each(function () {
      var color;
      if ($(this).hasClass('board__piece--dark')) {
        color = 'DarkPiece';
      }
      if ($(this).hasClass('board__piece--light')) {
        color = 'LightPiece';
      }

      board_state.push({
        x: $(this).parent().data('x'),
        y: $(this).parent().data('y'),
        color: color,
        king: $(this).hasClass('board__piece--king')
      });
    });

    return board_state;
}


function format_time_for_display(time_sec) {
    const minutes = Math.floor(time_sec / 60);
    const seconds = time_sec % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}


function update_user_time() {
    if (GameConfig.current_turn === COLOR_LIGHT && window.lightTime_sec > 0) {
      window.lightTime_sec--;
      window.lightTimeDisplay.textContent = format_time_for_display(window.lightTime_sec);
    } else if (GameConfig.current_turn === COLOR_DARK && window.darkTime_sec > 0) {
      window.darkTime_sec--;
      window.darkTimeDisplay.textContent = format_time_for_display(window.darkTime_sec);
    }

    // if (window.lightTime_sec === 0 || window.darkTime_sec === 0) {
    //   clearInterval(window.clockInterval); // Stop if anyone runs out of time
    //   alert(`${GameConfig.current_turn} player ran out of time!`);
    // }

    if (window.lightTime_sec === 0) {
        clearInterval(window.clockInterval); // Stop time if anyone runs out of time
        GameConfig.winner = COLOR_DARK;
        display_winner(COLOR_DARK);
        disable_user_interaction()
        // alert("White ran out of time! Black wins.");
    } else if (window.darkTime_sec === 0) {
        clearInterval(window.clockInterval);
        GameConfig.winner = COLOR_LIGHT;
        display_winner(COLOR_LIGHT);
        disable_user_interaction()
        // alert("Black ran out of time! White wins.");
    }
}


function update_turn_indicators() {
    if (GameConfig.current_turn === COLOR_LIGHT) {
      $('#dark_turn_indicator').removeClass('currentturn--dark').addClass('currentturn--invisible');
      $('#light_turn_indicator').removeClass('currentturn--invisible').addClass('currentturn--light');
    } else if (GameConfig.current_turn === COLOR_DARK) {
      $('#light_turn_indicator').removeClass('currentturn--light').addClass('currentturn--invisible');
      $('#dark_turn_indicator').removeClass('currentturn--invisible').addClass('currentturn--dark');
    }
}


function maybe_make_bot_move() {
    const bot_color = (NewGameSettings.user_color === COLOR_LIGHT) ? COLOR_DARK : COLOR_LIGHT;
    const playAgainstBot = String(NewGameSettings.play_against_bot).toLowerCase() === 'true';

    var pieces = pieces_on_board();

    if (GameConfig.winner !== 'light' && GameConfig.winner !== 'dark') {
      if (playAgainstBot && GameConfig.current_turn === bot_color) {
        // Automatically call the Flask backend to make a bot move
        $.post('/move_bot', {
          pieces: pieces,
          pieces_count: pieces.length,
          board_size_x: $('tr').first().find('td').length,
          board_size_y: $('tr').length,
          current_turn: GameConfig.current_turn,
        }, function (data, status) {
          // Inject updated HTML and refresh events
          setTimeout(function () {
            $('#board_with_figures_id').html(data);
            bind_events(); // Rebind to new DOM
            update_turn_indicators();
            maybe_make_bot_move()
          }, 300);
        });
      }
    }
}

