import os
import sys
import csv
import math
import requests
import argparse
from time import sleep
from pyfiglet import Figlet
from tabulate import tabulate
import matplotlib.pyplot as plt
from dataclasses import dataclass
import xml.etree.ElementTree as ET


# Where permanant constants live, though alas no type annotation for this--the disadvantages of Python :(
PLAY_XML_URL = "https://www.ibiblio.org/xml/examples/shakespeare/"


@dataclass
class Speech:
    speaker: str
    lines: int
    scene: int


# Play class with associated functions
class Play:
    # Assigns values and gets variables when initializing class
    def __init__(self, getter):
        # save inputs permanantly
        self.getter = getter
        id = self.getter.id
        self.id = id
        self.name = self.getter.get_play_list()[id]
        self.slug = self.getter.get_slug_list()[id]
        self.xml = self.getter.get_xml(id)
        self.root = ET.fromstring(self.xml)
        self.get_scenes()
        self.get_lines()
        self.get_characters()

    # Parse XML for characters and save base tree to class
    def get_chars(self):
        # Search XML for players
        players = []
        for player in self.root.findall("./PERSONAE/PERSONA"):
            players.append(player.text)
        for subplayer in self.root.findall("./PERSONAE/PGROUP/PERSONA"):
            players.append(subplayer.text)
        self.characters = players

    # Get structure of play as scenes
    def get_scenes(self):
        act_list = []
        acts = self.root.findall("ACT")
        # iterate through acts
        for act in acts:
            scenes = act.findall("SCENE")
            act = act.text
            scene_num = 0
            # iterate through scenes within an act
            for scene in scenes:
                scene_num += 1
            act_list.append(scene_num)
        scenes = []
        for act, scene in enumerate(act_list):
            act = intToRoman(act + 1)
            for i in range(scene):
                scene = intToRoman(int(i + 1))
                scenes.append(act + "." + scene.lower())
        self.scenes = scenes

    # Get and sort speeches
    def get_lines(self):
        speech_list = []
        cur_scene = 0
        acts = self.root.findall("ACT")
        # iterate through acts
        for act_num, act in enumerate(acts):
            scenes = act.findall("SCENE")
            act = act.text
            # iterate through scenes within an act
            for scene_num, scene in enumerate(scenes):
                cur_scene += 1
                tally = dict()
                speeches = scene.findall("SPEECH")
                scene = scene.text
                # iterate through speeches within a scene
                for speech in speeches:
                    speaker_name = speech.find("SPEAKER").text
                    line_count = len(speech.findall("LINE"))
                    # add num of lines to tally
                    if speaker_name in tally.keys():
                        tally[speaker_name] += line_count
                    else:
                        tally[speaker_name] = line_count

                # save speeches
                for character, line_count in zip(tally.keys(), tally.values()):
                    payload = Speech(character, line_count, cur_scene)
                    speech_list.append(payload)
                self.speeches = speech_list
        # Sort speeches by name
        self.speeches.sort(key=lambda x: x.speaker, reverse=True)

    # Analyze characters by speeches
    def get_characters(self):
        self.characters = dict()
        for speech in self.speeches:
            if speech.speaker in self.characters.keys():
                self.characters[speech.speaker] += speech.lines
            else:
                self.characters[speech.speaker] = speech.lines
        self.characters = dict(
            sorted(self.characters.items(), key=lambda item: item[1], reverse=True)
        ).items()

    # print total number of lines per character
    def print_lines(self):
        print(play.name + ":")
        data = []
        for char, lines in self.characters:
            data.append([char, lines])
        print(tabulate(data, headers=("Character", "Lines"), tablefmt="fancy_grid"))

    # Saves line frequency as a graph
    def plot_lines(self):
        if not self.speeches:
            UnboundLocalError(
                "Invalid variable: Must first fetch play XML before attempting parsing."
            )
            return
        big_line = sorted(self.speeches, key=lambda x: x.lines, reverse=True)[0].lines
        high = int(math.ceil(big_line / 100.0)) * 100
        plt.figure(figsize=(26, 17))
        for char in self.characters:
            x = list(range(len(self.scenes)))
            y = [0] * (len(self.scenes))
            for speech in self.speeches:
                if speech.speaker == str(char[0]):
                    y[int(speech.scene - 1)] = speech.lines
            plt.plot(x, y, label=str(char[0]))
        plt.title("Line frequency graph for " + self.name)
        plt.xticks(range(len(self.scenes)), self.scenes)
        plt.legend(loc="best", bbox_to_anchor=(1.1, 1.05), fancybox=True, shadow=True)
        plt.savefig(self.name + ".jpg")
        print("Graphed line frequency of " + self.name + " as " + self.name + ".jpg")

    # Saves line frequency as a CSV file
    def save_csv(self):
        file = self.name + ".csv"
        csv_rows = []
        for char in self.characters:
            row = [None] * (len(self.scenes) + 1)
            row[0] = char[0]
            for speech in self.speeches:
                if speech.speaker == str(char[0]):
                    row[int(speech.scene)] = speech.lines
            row.append(char[1])
            csv_rows.append(row)
        scenes = [None]
        for scene in self.scenes:
            scenes.append(scene)
        scenes.append("TOTAL LINES")
        with open(file, "w") as f:
            write_csv = csv.writer(f)
            write_csv.writerow(scenes)
            write_csv.writerows(csv_rows)
        print("Saved line frequency of " + self.name + " as " + self.name + ".csv")

# file reading class
class Getter:
    def __init__(self, play_file):
        self.read_plays(play_file)

    # cli to ask for plays
    def ask(self):
        f = Figlet(font="slant")
        print(f.renderText("Shakespearean Stats"))
        sleep(1)
        print("Select play to analyze:")
        sleep(0.3)
        for i, play in enumerate(self.get_play_list()):
            sleep(0.05)
            print(str(i) + ". " + play)
        id: int = int(input(">>> "))
        os.system("clear")
        # ^ fancy type declaration as of a recent Python version
        if type(id) is not int:
            raise ValueError("Invalid input: must be a number")
        if not id <= 36:
            raise IndexError("Invalid play selection: must be within range 0-36")
        self.id = id
        return id

    # opens "plays.txt" and saves play names and slug names in a list of lists
    def read_plays(self, play_file):
        with open(play_file, "r") as f:
            raw_plays = f.read().splitlines()
            play_list = []
            for play in raw_plays:
                name = play.split(",")[0]
                slug = play.split(",")[1]
                play_list.append([name, slug])
        self.play_list = play_list

    # returns list of just play names
    def get_play_list(self):
        return [i[0] for i in self.play_list]

    # converts play_list into list of slugs
    def get_slug_list(self):
        return [i[1] for i in self.play_list]

    # converts play_list into list of play names
    def get_play(self, id):
        return self.get_play_list()[id]

    # returns slug of current id
    def get_slug(self, id):
        return self.get_slug_list()[id]

    # Get the XML and store as a variable instead of messing with local files
    def get_xml(self, id):
        slug = self.get_slug(id)
        url = PLAY_XML_URL + slug + ".xml"
        # The owners of that website might not like us downloading their xml every single time we run our program
        # :/ maybe store it as a file again?
        return requests.get(url).content


# For pretty scene printing; seems out of place in one of the other classes
def intToRoman(num):
    # Roman values of digits from 0-9
    m = ["", "M", "MM", "MMM"]
    c = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM "]
    x = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
    i = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
    # Converting to numerals
    thousands = m[num // 1000]
    hundreds = c[(num % 1000) // 100]
    tens = x[(num % 100) // 10]
    ones = i[num % 10]
    ans = thousands + hundreds + tens + ones
    return ans


if __name__ == "__main__":
    # Parse arguemnts 
    parser = argparse.ArgumentParser(
        description="Script to fetch and parse line statistics of Shakespeare plays"
    )
    parser.add_argument(
        "-g",
        action="store_true",
        dest="graph",
        default=False,
        help="Graph lines over scenes",
    )
    parser.add_argument(
        "-s",
        action="store_true",
        dest="save",
        default=False,
        help="Save lines over scenes as a CSV file",
    )
    parser.add_argument(
        "-p",
        action="store_true",
        dest="print",
        default=False,
        help="Print stats to terminal",
    )
    getter = Getter("plays.txt")
    results = parser.parse_args()
    # Prompt for some input
    if not results.graph and not results.save and not results.print:
        print("Pass some arguments! Use -h")
        exit()
    # Initalize file and play
    getter.ask()
    play = Play(getter)
    # Check for desired functions
    if results.print:
        play.print_lines()
    if results.graph:
        play.plot_lines()
    if results.save:
        play.save_csv()
