import time
import rospy
import glob
import sys
import queue
import re
import os
import ntpath

from std_msgs.msg import String
from phonex import phonex
from qt_robot_interface.srv import *

text_input = []                     # list of the expected sentences
transcript_queue = queue.Queue()    # queue of words received by GSpeech Publisher (located in QTRP)
ignore_transcript_data = False      # Flag to rise to ignore data received from GSpeech Publisher

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"


def remove_punct(text: str):
    text = text.replace(':', '')
    text = text.replace('"', '')
    text = text.replace('!', '')
    text = text.replace('?', '')
    text = text.replace('.', '')
    text = text.replace(',', '')
    words_list = text.split()
    return words_list


def init_text_input(text: str):
    sentences = split_into_sentences(text)
    for sentence in sentences:
        words_list = remove_punct(sentence)
        words_list_lower = [word.lower() for word in words_list]
        text_input.append(words_list_lower)


def split_into_sentences(text: str):
    return re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)


def on_transcript_data(data):
    """
    Callback function, triggered when data is received from GSpeech Publisher.
    Format words and populate transcript_queue.
    """
    if not ignore_transcript_data:
        word_list = remove_punct(data.data)
        for word in word_list:
            transcript_queue.put(word.lower())


def compare_words(expected_word, word, tolerance):
    """
    Compare pronunciation of two groups of french words and return result.
    This is done by comparing the float value given by the 'phonex' library.
    This allows to palliate the inaccuracies in Google Speech transcript.
    """
    result = False

    if expected_word == word:
        result = True
    else:
        hash_word_expected = phonex(expected_word)
        hash_word = phonex(word)
        difference = abs(hash_word_expected-hash_word)
        if difference < tolerance:
            result = True
        else:
            result = False

    # Logs
    str_result = 'OK' if result else 'KO'
    sys.stdout.write(GREEN if result else RED)
    sys.stdout.write(str_result)
    sys.stdout.write(YELLOW)
    sys.stdout.write(f": Attendu : '{expected_word}' Obtenu : '{word}'\n")

    return result


def compare_transcript_and_text():
    """ Iterate over the sentences of text_input and compare heard words and expected words """
    sentence_index = 0
    while sentence_index < len(text_input):
        sentence = text_input[sentence_index]
        all_words_found = True
        for word in sentence:
            transcript_word = transcript_queue.get()
            if not compare_words(word, transcript_word, 0.0001):    # test if given word matches expected word
                empty_queue = False
                try:
                    # if the word doesn't match, we try to compare the reference word to the two following words
                    transcript_word2 = transcript_queue.get(block=False)
                except queue.Empty:
                    empty_queue = True

                if empty_queue or not compare_words(transcript_word + ' ' + transcript_word2, word, 0.001):
                    # Use of 'global' keyword to assign a value to a variable in an outer scope
                    global ignore_transcript_data
                    ignore_transcript_data = True

                    # Ask the kid to start over the sentence
                    sys.stdout.write(YELLOW)
                    sys.stdout.write("==========================================\n")
                    sys.stdout.write(f"Recommence à : {' '.join(sentence[0:3])}\n")
                    sys.stdout.write("==========================================\n")
                    speechSay = rospy.ServiceProxy('/qt_robot/behavior/talkText', speech_say)
                    speechSay(f"Oups ! Je crois que tu as fait une erreur. Recommence à ")
                    speechSay(' '.join(sentence[0:3]))

                    # Wait to make sure not to put transcript words in the queue
                    time.sleep(2)

                    # Reset transcript queue
                    with transcript_queue.mutex:
                        transcript_queue.queue.clear()
                    all_words_found = False
                    ignore_transcript_data = False
                    break

        if all_words_found:
            sentence_index += 1


def get_texts_to_read():
    return glob.glob('./texts_to_read/*txt')


def print_msg_box(msg, indent=1, width=None, title=None):
    """Print message-box with optional title."""
    lines = msg.split('\n')
    space = " " * indent
    if not width:
        width = max(map(len, lines))
    box = f'╔{"═" * (width + indent * 2)}╗\n'  # upper_border
    if title:
        box += f'║{space}{title:<{width}}{space}║\n'  # title
        box += f'║{space}{"-" * len(title):<{width}}{space}║\n'  # underscore
    box += ''.join([f'║{space}{line:<{width}}{space}║\n' for line in lines])
    box += f'╚{"═" * (width + indent * 2)}╝'  # lower_border
    sys.stdout.write(box)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        rospy.init_node('reading_game', anonymous=True)
        subscriber = rospy.Subscriber("gspeech_transcript", String, on_transcript_data)
        sys.stdout.write(YELLOW)
        sys.stdout.write("=======================================================================================\n")
        sys.stdout.write("   ____ _______   _____                _ _                _____                      \n")
        sys.stdout.write("  / __ \\__   __| |  __ \\              | (_)              / ____|                     \n")
        sys.stdout.write(" | |  | | | |    | |__) |___  __ _  __| |_ _ __   __ _  | |  __  __ _ _ __ ___   ___ \n")
        sys.stdout.write(" | |  | | | |    |  _  // _ \\/ _` |/ _` | | '_ \\ / _` | | | |_ |/ _` | '_ ` _ \\ / _ \\\n")
        sys.stdout.write(" | |__| | | |    | | \\ \\  __/ (_| | (_| | | | | | (_| | | |__| | (_| | | | | | |  __/\n")
        sys.stdout.write("  \\___\\_\\ |_|    |_|  \\_\\___|\\__,_|\\__,_|_|_| |_|\\__, |  \\_____|\\__,_|_| |_| |_|\\___|\n")
        sys.stdout.write("                                                  __/ |                              \n")
        sys.stdout.write("                                                 |___/                               \n")
        sys.stdout.write("=======================================================================================\n\n")

        print_msg_box("Choisir un texte à lire", indent=2)

        # Parse sub directory and display found txt files
        text_list = get_texts_to_read()
        for i in range(len(text_list)):
            path, filename = ntpath.split(text_list[i])
            sys.stdout.write(f"{i+1}: {filename.replace('.txt', '').replace('_', ' ')}\n")

        # Let the user choose a text
        choice_index = -1
        while choice_index == -1:
            try:
                choice_index = int(input())     # Will raise an exception if input is not a number
                if choice_index not in range(1, len(text_list)+1):
                    raise Exception
            except Exception:
                choice_index = -1

        # Extract text from chosen file
        with open(text_list[choice_index-1]) as f:
            lines = f.readlines()
        text_to_read = ' '.join([line.strip() for line in lines])

        # Display text to read
        print_msg_box("Texte à lire", indent=2)
        for sentence in split_into_sentences(text_to_read):
            sys.stdout.write(sentence.strip() + '\n')
        sys.stdout.write("\n")
        print_msg_box("Début de l'exercice", indent=2)

        # Exercise loop
        init_text_input(text_to_read)
        compare_transcript_and_text()

        # Unregister to topic \gspeech_transcript
        subscriber.unregister()

        # Congratulate the kid
        gesturePlay = rospy.Publisher('qt_robot/gesture/play', String, queue_size=1)
        attempt_number = 0
        while gesturePlay.get_num_connections() == 0:   # Wait for QT subscribers to be ready
            rospy.sleep(0.1)
            attempt_number += 1
            if attempt_number > 10:
                break

        gesturePlay.publish("QT/emotions/happy")
        speechSay = rospy.ServiceProxy('qt_robot/behavior/talkText', speech_say)
        resp = speechSay("Bien joué ! Tu as réussi à lire tout le texte")
        sys.stdout.write(GREEN)
        sys.stdout.write("Bien joué ! Tu as réussi à lire tout le texte\n")

    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
