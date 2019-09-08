# -*- coding: utf-8 -*-
from __future__ import division, unicode_literals, print_function

import itertools
import re
import json

from enum import Enum
from typing import List, Tuple, Dict, Callable

import sys
import os.path

try:
    import spacy
except ImportError:
    os.system('pip install spacy')
    os.system('python -m spacy download en')
    import spacy

    os.system('python -m spacy download en')


class DataSetType(Enum):
    TEST = "test"
    TRAIN = "train"
    DEV = "dev"


misspelling = {
    "accademiz": "academia",
    "withreference": "with reference",
    "thememorial": "the memorial",
    "unreleated": "unrelated",
    "varation": "variation",
    "variatons": "variations",
    "youthclub": "youth club",
    "oprated": "operated",
    "originaly": "originally",
    "origintes": "originates",
    "poacea": "poaceae",
    "posgraduayed": "postgraduate",
    "prevously": "previously",
    "publshed": "published",
    "punlished": "published",
    "recor": "record",
    "relgiion": "religion",
    "runwiay": "runway",
    "sequeled": "runway",
    "sppoken": "spoken",
    "studiies": "studies",
    "sytle": "style",
    "tboh": "both",
    "whic": "which",
    "identfier": "identifier",
    "idenitifier": "identifier",
    "igredient": "ingredients",
    "ingridient": "ingredients",
    "inclusdes": "includes",
    "indain": "indian",
    "leaderr": "leader",
    "legue": "league",
    "lenght": "length",
    "loaction": "location",
    "locaated": "located",
    "locatedd": "located",
    "locationa": "location",
    "managerof": "manager of",
    "manhattern": "manhattan",
    "memberrs": "members",
    "menbers": "members",
    "meteres": "metres",
    "numbere": "number",
    "numberr": "number",
    "notablework": "notable work",
    "7and": "7 and",
    "abbreivated": "abbreviated",
    "abreviated": "abbreviated",
    "abreviation": "abbreviation",
    "addres": "address",
    "abbreviatedform": "abbreviated form",
    "aerbaijan": "azerbaijan",
    "azerbijan": "azerbaijan",
    "affilaited": "affiliated",
    "affliate": "affiliate",
    "aircfrafts": "aircraft",
    "aircrafts": "aircraft",
    "aircarft": "aircraft",
    "airpor": "airport",
    "in augurated": "inaugurated",
    "inagurated": "inaugurated",
    "inaugrated": "inaugurated",
    "ausitin": "austin",
    "coccer": "soccer",
    "comanded": "commanded",
    "constructionof": "construction of",
    "counrty": "country",
    "countyof": "county of",
    "creater": "creator",
    "currecncy": "currency",
    "denonym": "demonym",
    "discipine": "discipline",
    "engish": "english",
    "establishedin": "established in",
    "ethinic": "ethnic",
    "ethiopa": "ethiopia",
    "ethipoia": "ethiopia",
    "eceived": "received",
    "ffiliated": "affiliated",
    "fullname": "full name",
    "grop": "group"
}

rephrasing = {
    # Add an acronym database
    "united states": ["u.s.", "u.s.a.", "us", "usa", "america", "american"],
    "united kingdom": ["u.k.", "uk"],
    "united states air force": ["usaf", "u.s.a.f"],
    "new york": ["ny", "n.y."],
    "new jersey": ["nj", "n.j."],
    "f.c.": ["fc"],
    "submarine": ["sub"],
    "world war ii": ["ww ii", "second world war"],
    "world war i": ["ww i", "first world war"],

    "greece": ["greek"],
    "canada": ["canadian"],
    "italy": ["italian"],
    "america": ["american"],
    "india": ["indian"],
    "singing": ["sings"],
    "conservative party (uk)": ["tories"],
    "ethiopia": ["ethiopian"],
}

rephrasing_must = {
    # Add a rephrasing database
    " language": "",
    " music": "",
    "kingdom of ": "",
    "new york city": "new york",
    "secretary of state of vermont": "secretary of vermont"
}


def rephrase(entity):
    phrasings = {entity}

    for s, rephs in rephrasing.items():
        for p in filter(lambda p: s in p, set(phrasings)):
            for r in rephs:
                phrasings.add(p.replace(s, r))

    # Allow rephrase "a/b/.../z" -> every permutation
    for p in set(phrasings):
        for permutation in itertools.permutations(p.split("/")):
            phrasings.add("/".join(permutation))

    # Allow rephrase "number (unit)" -> "number unit", "number unit-short"
    for p in set(phrasings):
        match = re.match("^(-?(\d+|\d{1,3}(,\d{3})*)(\.\d+)?)( (\((.*?)\)))?$",
                         p)
        if match:
            groups = match.groups()
            number = float(groups[0])
            unit = groups[6]

            number_phrasing = [
                str(number),
                str("{:,}".format(number))
            ]
            if round(number) == number:
                number_phrasing.append(str(round(number)))
                number_phrasing.append(str("{:,}".format(round(number))))

            if unit:
                couple = None
                words = [unit]

                if unit == "metres":
                    couple = "m"
                    words = [unit, "meters"]
                elif unit == "millimetres":
                    couple = "mm"
                elif unit == "centimetres":
                    couple = "cm"
                elif unit == "kilometres":
                    couple = "km"
                elif unit == "kilograms":
                    couple = "kg"
                elif unit == "litres":
                    couple = "l"
                elif unit == "inches":
                    couple = "''"
                elif unit in ["degreecelsius", "degreeklsius"]:
                    words = ["degrees celsius"]
                elif unit == "grampercubiccentimetres":
                    words = ["grams per cubic centimetre"]
                elif unit == "kilometreperseconds":
                    words = ["kilometres per second", "km/s", "km/sec",
                             "km per second", "km per sec"]
                elif unit in ["squarekilometres", "square kilometres"]:
                    words = ["square kilometres", "sq km"]
                elif unit == "cubiccentimetres":
                    couple = "cc"
                    words = ["cubic centimetres"]
                elif unit in ["cubic inches", "days", "tonnes", "square metres",
                              "inhabitants per square kilometre", "kelvins"]:
                    pass
                else:
                    raise ValueError(unit + " is unknown")

                for np in number_phrasing:
                    if couple:
                        phrasings.add(np + " " + couple)
                        phrasings.add(np + couple)
                    for word in words:
                        phrasings.add(np + " " + word)
            else:
                for np in number_phrasing:
                    phrasings.add(np)

    # Allow rephrase "word1 (word2)" -> "word2 word1"
    for p in set(phrasings):
        match = re.match("^(.* ?) \((.* ?)\)$", p)
        if match:
            groups = match.groups()
            s = groups[0]
            m = groups[1]
            phrasings.add(s + " " + m)
            phrasings.add(m + " " + s)

    return set(phrasings)


def rephrase_if_must(entity):
    phrasings = {entity}

    for s, rephs in rephrasing_must.items():
        for p in filter(lambda p: s in p, set(phrasings)):
            for r in rephs:
                phrasings.add(p.replace(s, r))

    # Allow removing parenthesis "word1 (word2)" -> "word1"
    for p in set(phrasings):
        match = re.match("^(.* ?) \((.* ?)\)$", p)
        if match:
            groups = match.groups()
            phrasings.add(groups[0])

    # Allow rephrase "word1 (word2) word3?" -> "word1( word3)"
    for p in set(phrasings):
        match = re.match("^(.*?) \((.*?)\)( .*)?$", p)
        if match:
            groups = match.groups()
            s = groups[0]
            m = groups[2]
            phrasings.add(s + " " + m if m else "")

    # Allow rephrase "a b ... z" -> every permutation
    # for p in set(phrasings):
    #     for permutation in itertools.permutations(p.split(" ")):
    #         phrasings.add(" ".join(permutation))

    phrasings = set(phrasings)
    if "" in phrasings:
        phrasings.remove("")
    return phrasings


class Cleaner():
    def __init__(self):
        self.filter_dic = self._filter_dic()
        self.fname_ends = [k[0] for k in self.filter_dic]

    def clean(self, filename):
        fname_end = '/'.join(filename.rsplit('/', 3)[1:])

        if fname_end not in self.fname_ends: return

        with open(filename, encoding="utf-8", errors='ignore') as f:
            lines = []
            content = f.readlines()
            for line_ix, line in enumerate(content):
                line = self.filter(fname_end, line_ix, line)
                if line: lines.append(line)
        if lines != content:
            # import pdb;
            # pdb.set_trace()
            fwrite(''.join(lines), filename)

    def _filter_dic(self):
        return {
            ('test/5triples/MeanOfTransportation.xml', 137,
             '<text>AIDAstella was built by Meyer Werft and is operated by AIDA Cruise Line. The AIDAstella has a beam of 32.2 m, is 253260.0 millimetres in length and has a beam of 32.2 m.</text>'):
                '<text>AIDAstella was built by Meyer Werft. The AIDAstella has a beam of 32.2 m, is 253260.0 millimetres in length and has a beam of 32.2 m.</text>',
            ('test/5triples/MeanOfTransportation.xml', 138,
             '<template>AGENT-1 was built by PATIENT-4 and is operated by BRIDGE-1 . AGENT-1 has a beam of PATIENT-2 , is PATIENT-5 in length and has a beam of PATIENT-2 .</template>'):
                '<template>AGENT-1 was built by PATIENT-4 . AGENT-1 has a beam of PATIENT-2 , is PATIENT-5 in length and has a beam of PATIENT-2 .</template>',
            ('test/5triples/MeanOfTransportation.xml', 161,
             '<text>The AIDAstella was built by Meyer Werft and operated by the AIDA Cruise Line. It is 253260.0 millimetres long with a beam of 32.2 metres and a top speed of 38.892 km/h.</text>'):
                '<text>The AIDAstella was built by Meyer Werft. It is 253260.0 millimetres long with a beam of 32.2 metres and a top speed of 38.892 km/h.</text>',
            ('test/5triples/MeanOfTransportation.xml', 162,
             '<template>AGENT-1 was built by PATIENT-4 and operated by BRIDGE-1 . AGENT-1 is PATIENT-5 long with a beam of PATIENT-2 and a top speed of PATIENT-3 .</template>'):
                '<template>AGENT-1 was built by PATIENT-4 . AGENT-1 is PATIENT-5 long with a beam of PATIENT-2 and a top speed of PATIENT-3 .</template>',

            ('test/4triples/CelestialBody.xml', 34,
             '<text>The epoch of (19255) 1994 VK8 is on 31 December 2006. It has an orbital period of 8788850000.0, a periapsis of 6155910000000.0 and an apoapsis of 6603633000.0 km.</text>'):
                '<text>The epoch of (19255) 1994 VK8 is on 31 December 2006. It has an orbital period of 8788850000.0 and a periapsis of 6155910000000.0 .</text>',
            ('test/4triples/CelestialBody.xml', 35,
             '<template>The epoch of AGENT-1 is on PATIENT-1 . AGENT-1 has an orbital period of PATIENT-2 , a periapsis of PATIENT-3 and an apoapsis of PATIENT-5 .</template>'):
                '<template>The epoch of AGENT-1 is on PATIENT-1 . AGENT-1 has an orbital period of PATIENT-2 and a periapsis of PATIENT-3 .</template>',

            ('test/4triples/MeanOfTransportation.xml', 293,
             '<text>Costa Crociere is the owner of the AIDAstella which is 25326.0 millimetres long. It was built by Meyer Werft and operated by AIDA Cruise Line.</text>'):
                '<text>Costa Crociere is the owner of the AIDAstella which is 25326.0 millimetres long. It was built by Meyer Werft .</text>',
            ('test/4triples/MeanOfTransportation.xml', 294,
             '<template>PATIENT-4 is the owner of AGENT-1 which is PATIENT-2 long . AGENT-1 was built by PATIENT-3 and operated by BRIDGE-1 .</template>'):
                '<template>PATIENT-4 is the owner of AGENT-1 which is PATIENT-2 long . AGENT-1 was built by PATIENT-3 .</template>',

            ('test/4triples/Monument.xml', 381,
             '<text>Ahmet Davutoglu is the leader of Turkey where the capital is Ankara. The Ataturk monument (Izmir) which is made of bronze is located within the country.</text>'):
                '<text>Ahmet Davutoglu is the leader of Turkey where the capital is Ankara. The Ataturk monument (Izmir) is located within the country.</text>',
            ('test/4triples/Monument.xml', 382,
             '<template>PATIENT-1 is the leader of BRIDGE-1 where the capital is PATIENT-2 . AGENT-1 which is made of PATIENT-4 is located within BRIDGE-1 .</template>'):
                '<template>PATIENT-1 is the leader of BRIDGE-1 where the capital is PATIENT-2 . AGENT-1 is located within BRIDGE-1 .</template>',

        }

    def filter(self, fname_end, line_ix, line):

        text = line.strip()
        key = (fname_end, line_ix, text)
        if key in self.filter_dic:
            new_text = self.filter_dic[key]
            if not new_text: return False
            line = line.replace(text, new_text)

        return line


ALPHA = chr(2)  # Start of text
OMEGA = chr(3)  # End of text
SPLITABLES = {ALPHA, OMEGA, " ", ".", ",", ":", "-", "'", "(", ")", "?", "!",
              "&", ";", '"'}


class DataReader:

    def __init__(self, data: List[dict],
                 misspelling: Dict[str, str] = None,
                 rephrase: Tuple[Callable, Callable] = (None, None)):
        self.data = data
        self.misspelling = misspelling
        self.rephrase = rephrase

    def fix_spelling(self):
        if not self.misspelling:
            return self

        regex_splittable = "(\\" + "|\\".join(SPLITABLES) + ".)"

        for misspelling, fix in self.misspelling.items():
            source = regex_splittable + misspelling + regex_splittable
            target = "\1" + fix + "\2"

            self.data = [d.set_text(re.sub(source, target, d.text)) for d in
                         self.data]

        return self


class NLP:
    def __init__(self):

        self.nlp = spacy.load('en', disable=['ner', 'parser', 'tagger'])
        self.nlp.add_pipe(self.nlp.create_pipe('sentencizer'))

    def sent_tokenize(self, text):
        doc = self.nlp(text)
        sentences = [sent.string.strip() for sent in doc.sents]
        return sentences

    def word_tokenize(self, text, lower=False):  # create a tokenizer function
        if text is None: return text
        text = ' '.join(text.split())
        if lower: text = text.lower()
        toks = [tok.text for tok in self.nlp.tokenizer(text)]
        return ' '.join(toks)


def show_var(expression,
             joiner='\n', print=print):
    '''
    Prints out the name and value of variables.
    Eg. if a variable with name `num` and value `1`,
    it will print "num: 1\n"

    Parameters
    ----------
    expression: ``List[str]``, required
        A list of varible names string.

    Returns
    ----------
        None
    '''

    var_output = []

    for var_str in expression:
        frame = sys._getframe(1)
        value = eval(var_str, frame.f_globals, frame.f_locals)

        if ' object at ' in repr(value):
            value = vars(value)
            value = json.dumps(value, indent=2)
            var_output += ['{}: {}'.format(var_str, value)]
        else:
            var_output += ['{}: {}'.format(var_str, repr(value))]

    if joiner != '\n':
        output = "[Info] {}".format(joiner.join(var_output))
    else:
        output = joiner.join(var_output)
    print(output)
    return output


def fwrite(new_doc, path, mode='w', no_overwrite=False):
    if not path:
        print("[Info] Path does not exist in fwrite():", str(path))
        return
    if no_overwrite and os.path.isfile(path):
        print("[Error] pls choose whether to continue, as file already exists:",
              path)
        import pdb
        pdb.set_trace()
        return
    with open(path, mode) as f:
        f.write(new_doc)


def shell(cmd, working_directory='.', stdout=False, stderr=False):
    import subprocess
    from subprocess import PIPE, Popen

    subp = Popen(cmd, shell=True, stdout=PIPE,
                 stderr=subprocess.STDOUT, cwd=working_directory)
    subp_stdout, subp_stderr = subp.communicate()

    if stdout and subp_stdout:
        print("[stdout]", subp_stdout, "[end]")
    if stderr and subp_stderr:
        print("[stderr]", subp_stderr, "[end]")

    return subp_stdout, subp_stderr
