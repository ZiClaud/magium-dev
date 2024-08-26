from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

root_folder = Path("./chapters")


class Lexer:
    def __init__(self,data):
        self.data = data
        self.pos = 0
        self.peek = data[0]

    def next(self):
        line = self.peek
        self.pos += 1
        self.peek = data[self.pos]
        print(line)
        return line

    def eof(self):
        return self.pos >= len(data) - 1


def is_condition(line):
    return line[0] in ["+","*"]

def transform_var_name(var_name):
    return "v_"+var_name.lower().replace(" ","_")

def parse_condition(t: str):
    if t in [">","<"]:
        return t
    elif t == "=":
        return "=="
    elif t == "<>":
        return "!="
    else:
        raise ValueError(t)

@dataclass
class Event:
    type: str = ""
    conditions: dict[str,Any] = field(default_factory=lambda:{"variables":{}})
    results: dict[str,Any] = field(default_factory=lambda:{"add_buttons":[],"set_variables":{}})


@dataclass
class Comparison:
    type: str
    value: int

@dataclass
class Paragraph:
    id: int
    version: int
    conditions: dict = field(default_factory=dict)

@dataclass
class Response:
    text: str = field(default_factory=str)
    new_scene: str = field(default_factory=str)
    set_variables: dict = field(default_factory=dict)

@dataclass
class Scene:
    id: str
    paragraphs: list = field(default_factory=list) 
    responses: list = field(default_factory=list) 

    def to_json(self,paragraphs):
        text = ""
        for par in self.paragraphs:
            if par.conditions != {}:
                condition_string = ' && '.join([f"{var} {parse_condition(cond.type)} {cond.value}" for var,cond in par.conditions.items()])
                text += f"<% if({condition_string}) {{%>"
            text += paragraphs[par.version][par.id]
            if par.conditions != {}:
                text += "<% } %>"
        text = text.replace("\n","<br/>")
        val = {
            "id": self.id,
            "text": text,
            "responses": [
                {
                    "code": response.text,
                    "text": response.text,
                    "target": response.new_scene,
                    "set_variables": response.set_variables,
                }
                for response in self.responses
            ]
        }
        return val


class Parser:
    def __init__(self, lexer) -> None:
        self.lexer = lexer

    def parse_event(self):
        print("New event")
        print(self.lexer.peek)
        assert self.lexer.peek.startswith("*")
        event = Event()
        while len(current:=self.lexer.next()) > 1 and not self.lexer.eof():
            if is_condition(current):
                if match := re.search('current scene = "(?P<scene>.*)"',current):
                    event.conditions["scene"] = match.group("scene")
                elif match := re.search('current scene <> "(?P<scene>.*)"',current):
                    continue
                elif "Mouse pointer is over" in current:
                    event.type = "button"
                elif match := re.search('Button ID of Group.Buttons = (?P<button>.*)',current):
                    event.conditions["button_id"] = int(match.group("button"))-1
                elif match := re.search('(?P<variable>.*) (?P<comparison>=|<|>|<>) (?P<value>.*)',current[2:]):
                    if "counter" not in match.group("variable").lower():
                        event.conditions["variables"][transform_var_name(match.group("variable"))] = Comparison(match.group("comparison"),int(match.group("value")))

            else:
                if match := re.search('List : Add line "(?P<button_name>.*)"',current):
                    event.type = "scene_load"
                    event.results["add_buttons"].append(match.group("button_name"))
                elif match := re.search('Special : Set current scene to "(?P<scene>.*)"',current):
                    event.results["new_scene"] = match.group("scene")
                elif match := re.search('Special : Set (?P<variable>.*) to (?P<value>.*)',current):
                    event.results["set_variables"][transform_var_name(match.group("variable"))] = match.group("value")
                elif match := re.search('Scene text : Display paragraph (?P<paragraph>.*)',current):
                    event.results["paragraph"] = int(match.group("paragraph"))
                    event.results["paragraph_version"] = 1
                elif match := re.search('Scene text 2 : Display paragraph (?P<paragraph>.*)',current):
                    event.results["paragraph"] = int(match.group("paragraph"))
                    event.results["paragraph_version"] = 2
                elif match := re.search('scene 3 : Display paragraph (?P<paragraph>.*)',current):
                    event.results["paragraph"] = int(match.group("paragraph"))
                    event.results["paragraph_version"] = 3

        return event

    def parse(self):
        events = []
        while not self.lexer.eof():
            while not self.lexer.peek.startswith("*") and not self.lexer.eof():
                self.lexer.next()
            events.append(self.parse_event())
        return events
            

for chapter in [f"ch{i}" for i in range(1,7)]:
    filename = root_folder/chapter/"logic.txt"

    events = []
    current_event = {}
    with open(filename,"r") as f:
        data = list(f.readlines())
    lexer = Lexer(data)
    parser = Parser(lexer)

    events = parser.parse()
    scenes = {}

    for event in [e for e in events if e.type == "scene_load"]:
        print(event)
        if "scene" not in event.conditions:
            continue
        scene = event.conditions["scene"]
        if scene not in scenes:
            scenes[scene] = Scene(scene)

        for button in event.results["add_buttons"]:
            if button not in [resp.text for resp in scenes[scene].responses]:
                scenes[scene].responses.append(Response(button))
        if "paragraph" in event.results:
            if event.results["paragraph"] not in [par.id for par in scenes[scene].paragraphs]:
                scenes[scene].paragraphs.append(Paragraph(event.results["paragraph"],event.results["paragraph_version"],event.conditions["variables"])) 

    for event in [e for e in events if e.type == "button"]:
        print(event)
        if "scene" not in event.conditions:
            continue
        scene = event.conditions["scene"]
            
        for var,value in event.results["set_variables"].items():
            scenes[scene].responses[event.conditions["button_id"]].set_variables[var] = value 
            
        if "new_scene" in event.results: 
            scenes[scene].responses[event.conditions["button_id"]].new_scene = event.results["new_scene"]


    for id,scene in scenes.items():
        print(id)
        print(scene)


    paragraphs = {1:{},2:{},3:{}}

    for i in [1,2,3]:
        with open(root_folder/chapter/f"paragraphs{i}.txt","r") as f:
            data = f.readlines()

        current_par_index = 0
        current_par = ""
        for line in data:
            if match := re.match("\[(?P<par_num>[0-9]*)\](?P<text>.*)",line):
                paragraphs[i][current_par_index] = current_par
                current_par = match.group("text")
                current_par_index = int(match.group("par_num"))
            else:
                current_par += line
        paragraphs[i][current_par_index] = current_par

    json_vals = {id:scene.to_json(paragraphs) for id,scene in scenes.items()}
    with open(root_folder/f"{chapter}.json","w") as f:
        json.dump(json_vals,f,indent=4)
