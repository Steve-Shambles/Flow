""" Five Letters One Word (FLOW) V1.0
    A Wordle derivative by Steve Shambles, April 2023.

Bugs:
rare bug where clicking enter on first go does nothing.
sometimes Ent button stays depressed for a while too long.

To do:
colour in keyboard keys yellow or green as appropiate for current game word,
I failed to work out how to do this, even with chatgtp help, it is beyond me
at this time.

requirements:
pip3 install Pillow
pip3 install PyDictionary
pip3 install requests
Pip3 install sounddevice
pip3 install soundfile
"""
from datetime import datetime
import os
import random
import sys
import threading
import tkinter as tk
from tkinter import messagebox, Menu
import webbrowser as web

import requests
from PIL import Image, ImageTk
from PyDictionary import PyDictionary
import sounddevice as sd
import soundfile as sf


dictionary = PyDictionary()
c_font = ('calibri', 10, 'bold')
a_font = ('ariel', 9, 'bold')
bg_col = 'darkcyan'


class Fs():
    """ My global store of variables, its bad practice but works for me. """
    boxes = None
    clicked_key = ''
    dictionary_in_use = 'Easy 23k words'
    games_count = 0
    game_outcome = ''
    keyb_frame = None
    letter_boxes = []
    letter_count = 0
    player_attempts = 1
    players_word = ''
    secret_word = ''
    solution_meaning = ''
    used_clue = False
    won_round = None
    word_line = 0


root = tk.Tk()
root.title('FLOW V1.0 - Five Letters One Word by Steve Shambles 2023')
root.configure(bg=bg_col)

check_if_data_folder = os.path.isdir(r'data')
if not check_if_data_folder:
    messagebox.showerror('FLOW Error',
                         'The data folder appears to be missing.\n'
                         'Cannot continue, please fix or re-install.')
    root.destroy()
    sys.exit()

Fs.dictionary_in_use = 'Easy 23k words'


def play_sound(filename):
    """ Play WAV file. Supply filename when calling this function. """
    data, fs = sf.read(filename, dtype='float32')
    sd.play(data, fs)


def ask_dictionary():
    """ Ask player to choose from easy (default) or hard dictionary. """
    ask_yn = messagebox.askyesno('Question',
                                 'Play with easy dictionary?')
    if ask_yn is False:
        messagebox.showinfo('Hard dictionary',
                            'This dictionary has a mix of easy words\n'
                            'and very hard words, 90k in all.\n\n'
                            'Some clues and meanings may not\n'
                            'be available for some words.')

        Fs.dictionary_in_use = '90k_words_inc_hard_words'
        d_txt = 'Current dictionary: ' + str(Fs.dictionary_in_use)
        dict_lab.config(text=d_txt)


def save_history():
    """ Append date\time, solution, meaning, won, lost to text file."""
    time_stamp = datetime.now().strftime('%d-%b-%Y-%H.%M-%Ss')
    with open(r'data/history.txt', 'a') as contents:
        save_it = '\n\n' + str(time_stamp) + '\n' + 'Dictionary: '  \
            + str(Fs.dictionary_in_use) + '\nSolution: '  \
            + str(Fs.secret_word) + '\nMeaning : ' + str(Fs.solution_meaning)  \
            + '\nAttempts : ' + str(Fs.player_attempts)  \
            + '\nUsed clue?: ' + str(Fs.used_clue)  \
            + '\nOutcome : ' + str(Fs.game_outcome)  \
            + '\n------------------------------------------------------------'
        contents.write(save_it)


def start_new_round():
    """ After first game is over restart here redraw all gui reset vars. """
    Fs.letter_count = 0
    Fs.word_line = 0
    Fs.boxes = None
    Fs.clicked_key = ''
    Fs.secret_word = ''
    Fs.players_word = ''
    Fs.player_attempts = 1
    Fs.won_round = None
    Fs.used_clue = False
    Fs.game_outcome = ''
    Fs.solution_meaning = ''

    get_random_5_letter_word()
    create_board()
    Fs.keyb_frame.destroy()
    virtual_keyboard()


def game_over():
    """ Rather large game over with lots going on in a thread too. """
    word = Fs.secret_word
    msg = ''

    if Fs.won_round:
        msg = 'Congratulations on winning that round:\n'
        Fs.game_outcome = 'Won'
        play_sound(r'data/sfx/won.wav')
    else:
        msg = 'You failed that time, please try again\n'
        Fs.game_outcome = 'Lost'
        play_sound(r'data/sfx/lost.wav')

    ask_yn = messagebox.askyesno('FLOW solution',
                                 str(msg) + 'The secret word was: '
                                 + str(word) + '\n\n'
                                 'Look up the meaning of this word?')
    if ask_yn is False:
        save_history()
        return

    def fetch_meaning(callback):
        """ Get meaning of secret word from PyDictionary. """
        try:
            response = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}')
            response.raise_for_status()
            data = response.json()
            meaning = data[0]['meanings'][0]['definitions'][0]['definition']
            root.after(0, lambda: messagebox.showinfo('Meaning of the word is as follows', f'{word}:\n{meaning}'))
            callback(meaning)
        except requests.exceptions.RequestException:
            root.after(0, lambda: messagebox.showerror('FLOW lookup Error',
                                                       'Error looking up the meaning of this word.\n'
                                                       'Either word not found,\n'
                                                       'or a connection problem.'))
            callback('')

    def save_history_callback(meaning):
        """ Save meaning of word to history file. """
        Fs.solution_meaning = meaning
        save_history()

    threading.Thread(target=fetch_meaning,
                     args=(save_history_callback,)).start()


def game_over_thread():
    """ Start game over thread. """
    t = threading.Thread(target=game_over)
    t.start()


def end_round():
    """ Completed a game so call game over routines or exit prg. """
    game_over_thread()
    ask_yn = messagebox.askyesno('FLOW: Go Again?',
                                 'Play another game?')
    if ask_yn is False:
        root.destroy()
        sys.exit()

    start_new_round()


def colour_in_tiles():
    """colour in tiles, green correct letter in correct place,
       yellow correct letter in wrong position in word."""
    secret_letters = []
    j = 0
    i = 0
    secret_letters = list(Fs.secret_word)
    for i in range(5):
        if Fs.players_word[i] == secret_letters[i]:
            Fs.letter_boxes[Fs.word_line][i].config(bg='limegreen')
            secret_letters[i] = None  # mark the letter as matched
        elif Fs.players_word[i] in secret_letters:
            j = secret_letters.index(Fs.players_word[i])
            Fs.letter_boxes[Fs.word_line][i].config(bg='gold')
            secret_letters[j] = None


def check_words_match():
    """ player has entered 5 letters, """
    if Fs.letter_count < 5:
        return
    if Fs.dictionary_in_use == 'Easy 23k words':
        diction_ary = 'data/23k_easy_words.txt'
    else:
        diction_ary = 'data/90k_words_inc_hard_words.txt'

    Fs.players_word = Fs.players_word.lower()
    # Check entered word is in word list or it is not valid.
    with open(diction_ary, 'r') as f:
        word_list = f.read().splitlines()
    if Fs.players_word not in word_list:
        messagebox.showinfo('FLOW',
                            'Although this might be a\n'
                            'real word, it is not used\n'
                            'in this dictionary, sorry!\n\n')
        return

    colour_in_tiles()

    if Fs.players_word == Fs.secret_word:
        Fs.won_round = True
        end_round()
    else:
        # Move down to next word line as guessed wrong.
        Fs.word_line += 1
        Fs.player_attempts += 1
        Fs.letter_count = 0
        Fs.players_word = ''
        Fs.clicked_key = ''

        if Fs.word_line >= 6:
            Fs.won_round = False
            Fs.player_attempts -= 1
            end_round()


def get_random_5_letter_word():
    """ Get a random word from text file ,
        this approach doesn't load the entire file into memory at once
        it's slower but more memory effecient. """
    if Fs.dictionary_in_use == 'Easy 23k words':
        diction_ary = 'data/23k_easy_words.txt'
    else:
        diction_ary = 'data/90k_words_inc_hard_words.txt'
    file_name = diction_ary
    with open(file_name, "r") as file:
        Fs.secret_word = None
        for i, line in enumerate(file):
            if random.randrange(i + 1) == 0:
                Fs.secret_word = random.choice(line.split())
        # print(Fs.secret_word)


def delete_last_letter():
    """ Del key pressed, so delete last letter entered on board. """
    if Fs.letter_count <= 0:
        return
    Fs.letter_boxes[Fs.word_line][Fs.letter_count-1].  \
        config(text='')
    Fs.letter_count -= 1
    Fs.players_word = Fs.players_word[:-1]


def insert_letter():
    """ Auto detected using bind that a key has been pressed on virtual keyb
        so enter it onto game board. """
    if Fs.letter_count >= 5:
        return
    Fs.letter_count += 1
    Fs.letter_boxes[Fs.word_line][Fs.letter_count-1].  \
        config(text=Fs.clicked_key)
    Fs.players_word = Fs.players_word + str(Fs.clicked_key)


def key_pressed(event):
    """ Detect when a button on the virtual keyboard is clicked
        and store the letter of the pressed key in string 'clicked_key'. """
    # play_sound(r'data/sfx/click.wav')
    Fs.clicked_key = event.widget['text']
    if Fs.clicked_key == 'Del':
        delete_last_letter()
        return
    if Fs.clicked_key == 'Ent':
        check_words_match()
        return
    insert_letter()


def create_board():
    """ construct the game board. """
    Fs.letter_boxes = []
    num_rows = 6
    num_cols = 5
    i = 0
    j = 0
    vert_row = 0
    # Create the labels and add them to the list
    matrix_frame = tk.Frame(root)
    for i in range(num_rows):
        vert_row = []  # create a new empty list for each row
        for j in range(num_cols):
            Fs.boxes = tk.Label(matrix_frame, text=" ",
                                width=5, height=2, bg="powderblue",
                                relief="solid")
            Fs.boxes.grid(row=i, column=j, padx=5, pady=5)
            vert_row.append(Fs.boxes)
        Fs.letter_boxes.append(vert_row)
        matrix_frame.grid(row=num_rows+1, column=0)
    matrix_frame.grid()


def help_text():
    """Show help text file."""
    web.open(r'data\flow_help.txt')


def about_menu():
    """About program msgbox."""
    messagebox.showinfo('FLOW Program Information',
                        'Five Letters One Word V1\n\n'
                        'Freeware by Steve Shambles\n'
                        'Source code MIT Licence.\n'
                        'See help file for more details.\n\n'
                        '(c) April 2023\n')


def donate_me():
    """User splashes the cash here!"""
    web.open('https:\\paypal.me/photocolourizer')


def visit_github():
    """View source code and my other Python projects at GitHub."""
    web.open('https://github.com/Steve-Shambles?tab=repositories')


def exit_flow():
    """Yes-no requestor to exit program."""
    ask_yn = messagebox.askyesno('Question',
                                 'Quit FLOW?')
    if ask_yn is False:
        return

    root.destroy()
    sys.exit()


def give_me_a_clue():
    """ Give me a clue button clicked so get meaning of secret word
        from pydictionary and use as clue. Using in a thread makes
        this operation almost instant, without thread gui freezes
        up and long wait."""
    word = Fs.secret_word
    Fs.used_clue = True

    def fetch_clue():
        clue = 'Clue'
        try:
            response = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}')
            response.raise_for_status()
            data = response.json()
            meaning = data[0]['meanings'][0]['definitions'][0]['definition']
            root.after(10, lambda: messagebox.showinfo('Here is a clue for you', f'{clue}:\n{meaning}'))
            Fs.solution_meaning = meaning
            Fs.used_clue = True
            return
        except requests.exceptions.RequestException:
            Fs.used_clue = False
            root.after(0, lambda: messagebox.showerror('FLOW lookup Error',
                                                       'Error looking up a clue for this word.\n'
                                                       'Either word not found,\n'
                                                       'or a connection problem. Sorry!'))

    threading.Thread(target=fetch_clue).start()


def i_give_in():
    """ Player clicked i give in button, so show secret word then
        new game. """
    ask_yn = messagebox.askyesno('Question',
                                 'Do really want to give up\n'
                                 'on this word?')
    if ask_yn is False:
        return

    Fs.won_round = False
    Fs.game_outcome = 'Lost'
    end_round()


def view_history():
    """ View history.txt file stored in data folder. """
    web.open(r'data\history.txt')


def delete_history():
    """ Delete comtents of history.txt. """
    ask_yn = messagebox.askyesno('Question',
                                 'Do want to delete\n'
                                 'your game history?')
    if ask_yn is False:
        return

    with open(r'data/history.txt', 'w') as contents:
        contents.write('')
    messagebox.showinfo('FLOW Program Information',
                        'Your game history has been deleted\n\n')


def play_easy_dict():
    """ User Chose easy dictionary at start ogf game. """
    Fs.dictionary_in_use = 'Easy 23k words'


def play_hard_dict():
    """ User Chose hard dictionary at start ogf game. """
    Fs.dictionary_in_use = 'Hard 90k words'


def virtual_keyboard():
    """ create the virtual keyboard. """
    # Create the main keyboard frame.
    Fs.keyb_frame = tk.Frame(root, bg=bg_col)
    Fs.keyb_frame.grid(padx=10, pady=10)
    # keys colours
    kb_bg_col = 'black'
    kb_fg_col = 'white'
    # Create QWERTYUIOP top row frame.
    qwerty_frame = tk.Frame(Fs.keyb_frame, bg=bg_col)
    qwerty_frame.grid(row=0, column=0, columnspan=10, padx=2, pady=2)
    # Populate buttons with letters.
    for i, char in enumerate("QWERTYUIOP"):
        qwerty_btn = tk.Button(qwerty_frame, font=c_font,
                               text=char, width=5, height=2,
                               bg=kb_bg_col, fg=kb_fg_col)
        qwerty_btn.bind('<Button-1>', key_pressed)
        qwerty_btn.grid(row=0, column=i, padx=2, pady=2)

    # Create ASDFGHJKL second row.
    asd_frame = tk.Frame(Fs.keyb_frame, bg=bg_col)
    asd_frame.grid(row=1, column=0, columnspan=10, padx=2, pady=2)

    # Populate buttons with letters.
    for i, char in enumerate("ASDFGHJKL"):
        asd_btn = tk.Button(asd_frame, font=c_font,
                            text=char, width=5, height=2,
                            bg=kb_bg_col, fg=kb_fg_col)
        asd_btn.bind('<Button-1>', key_pressed)
        asd_btn.grid(row=0, column=i, padx=2, pady=2)

    # Create ZXCVBNM third row.
    zxc_frame = tk.Frame(Fs.keyb_frame, bg=bg_col)
    zxc_left = tk.Frame(zxc_frame, bg=bg_col)
    zxc_right = tk.Frame(zxc_frame, bg=bg_col)

    # Add "Del" button to the left frame, represents delete key.
    star_btn = tk.Button(zxc_left, font=c_font, text="Del",
                         width=5, height=2, bg='indianred')
    star_btn.bind('<Button-1>', key_pressed)
    star_btn.pack(side=tk.LEFT, padx=2, pady=2)

    for i, char in enumerate("ZXCVBNM"):
        zxc_btn = tk.Button(zxc_right, font=c_font, text=char,
                            width=5, height=2,
                            bg=kb_bg_col, fg=kb_fg_col)
        zxc_btn.bind('<Button-1>', key_pressed)
        zxc_btn.pack(side=tk.LEFT, padx=2, pady=2)

    # Add "Ent" button to the right frame, represents the enter button.
    enter_btn = tk.Button(zxc_right, font=c_font, text="Ent",
                          width=5, height=2, bg='lightgreen')
    enter_btn.bind('<Button-1>', key_pressed)
    enter_btn.pack(side=tk.RIGHT, padx=4, pady=2)

    # Add both frames to the main frame
    zxc_left.pack(side=tk.LEFT)
    zxc_right.pack(side=tk.LEFT)
    zxc_frame.grid(row=2, column=0, columnspan=10, padx=2, pady=2)


# ------------------Insert logo.-------------
logo_frame = tk.LabelFrame(root)
logo_image = Image.open(r'data/flow_logo.png')
logo_photo = ImageTk.PhotoImage(logo_image)
logo_label = tk.Label(logo_frame, image=logo_photo)
logo_label.logo_image = logo_photo
logo_label.grid()
logo_frame.grid(row=0, column=0, padx=8, pady=8)

create_board()

# ---------give us a clue and i give in frame and btns---------
give_in_frame = tk.LabelFrame(root, bg=bg_col)
give_in_btn = tk.Button(give_in_frame, bg=bg_col, fg='white',
                        font=c_font,
                        text='  I Give In!  ',
                        command=i_give_in)
give_in_btn.grid()
give_in_frame.grid(sticky=tk.W, row=8, column=0, padx=16)

d_txt = 'Current dictionary: ' + str(Fs.dictionary_in_use)
dict_lab = tk.Label(root, font=c_font, bg=bg_col,
                    fg='white', text=str(d_txt))
dict_lab.grid()

clue_frame = tk.LabelFrame(root, bg=bg_col)
clue_btn = tk.Button(clue_frame, bg=bg_col, fg='white',
                     font=c_font, text='Give Me A Clue',
                     command=give_me_a_clue)
clue_btn.grid()
clue_frame.grid(sticky=tk.E, row=8, column=0, padx=16)

virtual_keyboard()

# --------------------------File menu-----------------------
# Pre-load icons for drop-down menu.
try:
    help_icon = ImageTk.PhotoImage(file=r'data/icons/help-16x16.ico')
    about_icon = ImageTk.PhotoImage(file=r'data/icons/about-16x16.ico')
    exit_icon = ImageTk.PhotoImage(file=r'data/icons/exit-16x16.ico')
    donation_icon = ImageTk.PhotoImage(file=r'data/icons/donation-16x16.ico')
    github_icon = ImageTk.PhotoImage(file=r'data/icons/github-16x16.ico')
except:
    messagebox.showinfo('FLOW Program Information',
                        'There was an error\n'
                        'Icons are missing from the data folder\n'
                        'Please fix or re-install')
    root.destroy()
    sys.exit()

menu_bar = Menu(root)
file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label='Menu', menu=file_menu)

file_menu.add_command(label='Help', compound='left',
                      image=help_icon, command=help_text)
file_menu.add_command(label='About', compound='left',
                      image=about_icon, command=about_menu)
file_menu.add_separator()
file_menu.add_command(label='Python source code on GitHub', compound='left',
                      image=github_icon, command=visit_github)
file_menu.add_command(label='Make a small donation via PayPal',
                      compound='left',
                      image=donation_icon, command=donate_me)
file_menu.add_separator()
file_menu.add_command(label='Exit', compound='left',
                      image=exit_icon, command=exit_flow)
root.config(menu=menu_bar)

# menu 2.
more_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label='More', menu=more_menu)
more_menu.add_command(
    label='View My Play History',
    command=view_history)
more_menu.add_command(
    label='Delete My Play History',
    command=delete_history)
root.config(menu=menu_bar)
# -----------------------------------------

root.eval('tk::PlaceWindow . Center')
root.protocol('WM_DELETE_WINDOW', exit_flow)

# Start game.
ask_dictionary()
get_random_5_letter_word()


root.mainloop()
