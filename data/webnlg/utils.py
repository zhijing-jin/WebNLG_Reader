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
            ('train/4triples/Food.xml', 7768, '<sentence ID="1"/>'): False,
            ('train/4triples/Food.xml', 7769,
             '<sentence ID="2">'): '<sentence ID="1">',
            ('train/4triples/Food.xml', 7773,
             '<sentence ID="3">'): '<sentence ID="2">',
            ('train/4triples/Food.xml', 7786,
             "<text>The bacon sandwich. which is found in the UK, has different names including: Bacon butty, bacon sarnie, rasher sandwich, bacon sanger, piece 'n bacon, bacon cob, bacon barm and bacon muffin. Bread is an ingredient of this sandwich, which is a variation on a BLT.</text>"): "<text>The bacon sandwich, which is found in the UK, has different names including: Bacon butty, bacon sarnie, rasher sandwich, bacon sanger, piece 'n bacon, bacon cob, bacon barm and bacon muffin. Bread is an ingredient of this sandwich, which is a variation on a BLT.</text>",
            ('train/4triples/Food.xml', 7787,
             "<template>AGENT-1 . which is found in PATIENT-2 , has different names including : PATIENT-3 . PATIENT-4 is an ingredient of AGENT-1 , which is a variation on PATIENT-1 .</template>"):
                "<template>AGENT-1 , which is found in PATIENT-2 , has different names including : PATIENT-3 . PATIENT-4 is an ingredient of AGENT-1 , which is a variation on PATIENT-1 .</template>",
            ('train/4triples/Food.xml', 7788,
             '<lexicalization>AGENT-1 . which VP[aspect=simple,tense=present,voice=passive,person=3rd,number=singular] find in PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have different names VP[aspect=progressive,tense=present,voice=active,person=null,number=null] include : PATIENT-3 . PATIENT-4 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a ingredient of AGENT-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a variation on PATIENT-1 .</lexicalization>'):
                '<lexicalization>AGENT-1 , which VP[aspect=simple,tense=present,voice=passive,person=3rd,number=singular] find in PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have different names VP[aspect=progressive,tense=present,voice=active,person=null,number=null] include : PATIENT-3 . PATIENT-4 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a ingredient of AGENT-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a variation on PATIENT-1 .</lexicalization>',

            ('train/5triples/Food.xml', 12890, '</sentence>'): False,
            ('train/5triples/Food.xml', 12891, '<sentence ID="2">'): False,
            ('train/5triples/Food.xml', 12905,
             '<text>Coming from the region of Visayas, in the Philippines, Binignit, is a type of dessert. Which banana as the main ingredient but also has sago in it.</text>'):
                '<text>Coming from the region of Visayas, in the Philippines, Binignit, is a type of dessert, which banana as the main ingredient but also has sago in it.</text>',
            ('train/5triples/Food.xml', 12906,
             '<template>Coming from the region of PATIENT-1 , in PATIENT-4 , AGENT-1 , is a type of PATIENT-3 . Which PATIENT-2 as the main ingredient but also has PATIENT-5 in AGENT-1 .</template>'):
                '<template>Coming from the region of PATIENT-1 , in PATIENT-4 , AGENT-1 , is a type of PATIENT-3 , which PATIENT-2 as the main ingredient but also has PATIENT-5 in AGENT-1 .</template>',
            ('train/5triples/Food.xml', 12907,
             '<lexicalization>VP[aspect=progressive,tense=present,voice=active,person=null,number=null] come from DT[form=defined] the region of PATIENT-1 , in PATIENT-4 , AGENT-1 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a type of PATIENT-3 . Which PATIENT-2 as DT[form=defined] the main ingredient but also VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have PATIENT-5 in AGENT-1 .</lexicalization>'):
                '<lexicalization>VP[aspect=progressive,tense=present,voice=active,person=null,number=null] come from DT[form=defined] the region of PATIENT-1 , in PATIENT-4 , AGENT-1 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a type of PATIENT-3 , which PATIENT-2 as DT[form=defined] the main ingredient but also VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have PATIENT-5 in AGENT-1 .</lexicalization>',

            ('train/5triples/SportsTeam.xml', 2913, '</sentence>'): False,
            ('train/5triples/SportsTeam.xml', 2914, '<sentence ID="2">'): False,
            ('train/5triples/SportsTeam.xml', 2929,
             "<text>Akron Summit Assault's ground is St. Vincent-St. Mary High School. Which is in the United States in Summit County, in Akron, Ohio where Dan Horrigan is the leader.</text>"):
                "<text>Akron Summit Assault's ground is St. Vincent-St. Mary High School, which is in the United States in Summit County, in Akron, Ohio where Dan Horrigan is the leader.</text>",
            ('train/5triples/SportsTeam.xml', 2930,
             "<template>AGENT-1 ground is BRIDGE-1 . Which is in PATIENT-3 in PATIENT-1 , in BRIDGE-2 where PATIENT-2 is the leader .</template>"): "<template>AGENT-1 ground is BRIDGE-1 , which is in PATIENT-3 in PATIENT-1 , in BRIDGE-2 where PATIENT-2 is the leader .</template>",
            ('train/5triples/SportsTeam.xml', 2931,
             '<lexicalization>AGENT-1 ground VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be BRIDGE-1 . Which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be in PATIENT-3 in PATIENT-1 , in BRIDGE-2 where PATIENT-2 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the leader .</lexicalization>'): '<lexicalization>AGENT-1 ground VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be BRIDGE-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be in PATIENT-3 in PATIENT-1 , in BRIDGE-2 where PATIENT-2 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the leader .</lexicalization>',

            ('train/7triples/University.xml', 31, '</sentence>'): False,
            ('train/7triples/University.xml', 32, '<sentence ID="2">'): False,
            ('train/7triples/University.xml', 46,
             '<text>The River Ganges flows through India which is the location of the AWH Engineering College which has 250 academic staff and was established in 2001 in the city of Kuttikkattoor in the state of Kerala. which is lead by Kochi.</text>'): '<text>The River Ganges flows through India which is the location of the AWH Engineering College which has 250 academic staff and was established in 2001 in the city of Kuttikkattoor in the state of Kerala, which is lead by Kochi.</text>',
            ('train/7triples/University.xml', 47,
             '<template>PATIENT-5 flows through BRIDGE-2 which is the location of AGENT-1 which has PATIENT-3 academic staff and was established in PATIENT-1 in the city of PATIENT-4 in the state of BRIDGE-1 . which is lead by PATIENT-2 .</template>'): '<template>PATIENT-5 flows through BRIDGE-2 which is the location of AGENT-1 which has PATIENT-3 academic staff and was established in PATIENT-1 in the city of PATIENT-4 in the state of BRIDGE-1 , which is lead by PATIENT-2 .</template>',
            ('train/7triples/University.xml', 48,
             '<lexicalization>PATIENT-5 VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] flow through BRIDGE-2 which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the location of AGENT-1 which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have PATIENT-3 academic staff and VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] establish in PATIENT-1 in DT[form=defined] the city of PATIENT-4 in DT[form=defined] the state of BRIDGE-1 . which VP[aspect=simple,tense=present,voice=passive,person=3rd,number=singular] lead by PATIENT-2 .</lexicalization>'): '<lexicalization>PATIENT-5 VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] flow through BRIDGE-2 which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the location of AGENT-1 which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have PATIENT-3 academic staff and VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] establish in PATIENT-1 in DT[form=defined] the city of PATIENT-4 in DT[form=defined] the state of BRIDGE-1 , which VP[aspect=simple,tense=present,voice=passive,person=3rd,number=singular] lead by PATIENT-2 .</lexicalization>',

            ('test/3triples/Athlete.xml', 408,
             '<reference entity="United_Petrotrin_F.C." number="3" tag="BRIDGE-1" type="description">the United Petrotrin F.C . club .</reference>'):
                '<reference entity="United_Petrotrin_F.C." number="3" tag="BRIDGE-1" type="description">the United Petrotrin F.C. club</reference>',

            ('test/3triples/Athlete.xml', 411,
             '<text>Akeem Adams played for W Connection F.C. and is a member of the United Petrotrin F.C. club. which play in Palo Seco.</text>'):
                '<text>Akeem Adams played for W Connection F.C. and is a member of the United Petrotrin F.C. club, which play in Palo Seco.</text>',

            ('test/3triples/WrittenWork.xml', 793, '</sentence>'): False,
            ('test/3triples/WrittenWork.xml', 794, '<sentence ID="2">'): False,

            ('test/3triples/WrittenWork.xml', 805,
             '<text>Abh.Math.Semin.Univ.Hambg is the abbreviation for Abhandlungen aus dem Mathematischen Seminar der Universität Hamburg. which has the ISSN number 1865-8784 as well as the LCCN number 32024459.</text>'):
                '<text>Abh.Math.Semin.Univ.Hambg is the abbreviation for Abhandlungen aus dem Mathematischen Seminar der Universität Hamburg, which has the ISSN number 1865-8784 as well as the LCCN number 32024459.</text>',
            ('test/3triples/WrittenWork.xml', 806,
             '<template>PATIENT-3 is the abbreviation for AGENT-1 . which has the ISSN number PATIENT-1 as well as the LCCN number PATIENT-2 .</template>'):
                '<template>PATIENT-3 is the abbreviation for AGENT-1 , which has the ISSN number PATIENT-1 as well as the LCCN number PATIENT-2 .</template>',
            ('test/3triples/WrittenWork.xml', 807,
             '<lexicalization>PATIENT-3 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the abbreviation for AGENT-1 . which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=defined] the ISSN number PATIENT-1 as well as DT[form=defined] the LCCN number PATIENT-2 .</lexicalization>'):
                '<lexicalization>PATIENT-3 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the abbreviation for AGENT-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=defined] the ISSN number PATIENT-1 as well as DT[form=defined] the LCCN number PATIENT-2 .</lexicalization>',

            ('test/4triples/Athlete.xml', 844, '</sentence>'): False,
            ('test/4triples/Athlete.xml', 845, '<sentence ID="2">'): False,
            ('test/4triples/Athlete.xml', 857,
             "<text>Alaa Abdul Zahra, whose club is Al-Zawra'a SC, is also a member of the club, AL Kharaitiyat SC @ Amar Osim is the manager of Al Kharaitiyat SC. which is located in Al Khor.</text>"):
                "<text>Alaa Abdul Zahra, whose club is Al-Zawra'a SC, is also a member of the club, AL Kharaitiyat SC @ Amar Osim is the manager of Al Kharaitiyat SC, which is located in Al Khor.</text>",
            ('test/4triples/Athlete.xml', 858,
             '<template>AGENT-1 , whose club is PATIENT-2 , is also a member of the club , BRIDGE-1 @ PATIENT-3 is the manager of BRIDGE-1 . which is located in PATIENT-1 .</template>'):
                '<template>AGENT-1 , whose club is PATIENT-2 , is also a member of the club , BRIDGE-1 @ PATIENT-3 is the manager of BRIDGE-1 , which is located in PATIENT-1 .</template>',
            ('test/4triples/Athlete.xml', 859,
             '<lexicalization>AGENT-1 , whose club VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be also DT[form=undefined] a member of DT[form=defined] the club , BRIDGE-1 PATIENT-3 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the manager of BRIDGE-1 . which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in PATIENT-1 .</lexicalization>'):
                '<lexicalization>AGENT-1 , whose club VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be also DT[form=undefined] a member of DT[form=defined] the club , BRIDGE-1 PATIENT-3 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=defined] the manager of BRIDGE-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in PATIENT-1 .</lexicalization>',

            ('test/4triples/Athlete.xml', 1021, '</sentence>'): False,
            ('test/4triples/Athlete.xml', 1022, '<sentence ID="2">'): False,
            ('test/4triples/Athlete.xml', 1025,
             '<sentence ID="3">'): '<sentence ID="2">',
            ('test/4triples/Athlete.xml', 1037,
             '<text>Alaa Abdul-Zahra, whose club is Shabab Al-Ordon Club, also plays for Al Kharaitiyat SC. which is located in Al Khor. The manager of Al Kharaitiyat SC is Amar Osim.</text>'
             ):
                '<text>Alaa Abdul-Zahra, whose club is Shabab Al-Ordon Club, also plays for Al Kharaitiyat SC, which is located in Al Khor. The manager of Al Kharaitiyat SC is Amar Osim.</text>',
            ('test/4triples/Athlete.xml', 1038,
             '<template>AGENT-1 , whose club is PATIENT-2 , also plays for BRIDGE-1 . which is located in PATIENT-1 . The manager of BRIDGE-1 is PATIENT-3 .</template>'):
                '<template>AGENT-1 , whose club is PATIENT-2 , also plays for BRIDGE-1 , which is located in PATIENT-1 . The manager of BRIDGE-1 is PATIENT-3 .</template>',
            ('test/4triples/Athlete.xml', 1039,
             '<lexicalization>AGENT-1 , whose club VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 , also VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] play for BRIDGE-1 . which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in PATIENT-1 . DT[form=defined] the manager of BRIDGE-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-3 .</lexicalization>'):
                '<lexicalization>AGENT-1 , whose club VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 , also VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] play for BRIDGE-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in PATIENT-1 . DT[form=defined] the manager of BRIDGE-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-3 .</lexicalization>',

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

            ('test/5triples/Building.xml', 910, '</sentence>'): False,
            ('test/5triples/Building.xml', 911, '<sentence ID="2">'): False,
            ('test/5triples/Building.xml', 914,
             '<sentence ID="3">'): '<sentence ID="2">',

            ('test/5triples/CelestialBody.xml', 137,
             '<reference entity="101_Helena" number="6" tag="AGENT-1" type="pronoun">He</reference>'):
                False,
            ('test/5triples/CelestialBody.xml', 138,
             '<reference entity="Madison,_Wisconsin" number="7" tag="PATIENT-4" type="name">Madison , Wisconsin</reference>'):
                '<reference entity="Madison,_Wisconsin" number="6" tag="PATIENT-4" type="name">Madison , Wisconsin</reference>',
            ('test/5triples/CelestialBody.xml', 141,
             "<template>BRIDGE-1 , who discovered AGENT-1 on PATIENT-2 , is a PATIENT-3 national who attended PATIENT-1 . AGENT-1 died in PATIENT-4 .</template>"):
                "<template>BRIDGE-1 , who discovered AGENT-1 on PATIENT-2 , is a PATIENT-3 national who attended PATIENT-1 . BRIDGE-1 died in PATIENT-4 .</template>",
            ('test/5triples/CelestialBody.xml', 142,
             "<lexicalization>BRIDGE-1 , who VP[aspect=simple,tense=past,voice=active,person=null,number=null] discover AGENT-1 on PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a PATIENT-3 national who VP[aspect=simple,tense=past,voice=active,person=null,number=null] attend PATIENT-1 . AGENT-1 VP[aspect=simple,tense=past,voice=active,person=null,number=null] die in PATIENT-4 .</lexicalization>"):
                "<lexicalization>BRIDGE-1 , who VP[aspect=simple,tense=past,voice=active,person=null,number=null] discover AGENT-1 on PATIENT-2 , VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be DT[form=undefined] a PATIENT-3 national who VP[aspect=simple,tense=past,voice=active,person=null,number=null] attend PATIENT-1 . BRIDGE-1 VP[aspect=simple,tense=past,voice=active,person=null,number=null] die in PATIENT-4 .</lexicalization>",
            ('test/5triples/CelestialBody.xml', 791,
             "<text>B. Zellner was the discoverer of 107 Camilla that has an orbital period of 2368.05 days. It's epoch is Dec. 31, 2006. The celestial body has a periapsis of 479343000.0 kilometres and an apoapsis of 560937000.0 km.</text>"):
                "<text>B. Zellner was the discoverer of 107 Camilla that has an orbital period of 2368.05 days. Its epoch is Dec. 31, 2006. Its celestial body has a periapsis of 479343000.0 kilometres and an apoapsis of 560937000.0 km.</text>",
            ('test/5triples/CelestialBody.xml', 792,
             "<template>PATIENT-1 was the discoverer of AGENT-1 that has an orbital period of PATIENT-2 . AGENT-1 epoch is PATIENT-4 . The celestial body has a periapsis of PATIENT-3 and an apoapsis of PATIENT-5 .</template>"):
                "<template>PATIENT-1 was the discoverer of AGENT-1 that has an orbital period of PATIENT-2 . PATIENT-1 epoch is PATIENT-4 . PATIENT-1 celestial body has a periapsis of PATIENT-3 and an apoapsis of PATIENT-5 .</template>",
            ('test/5triples/CelestialBody.xml', 793,
             "<lexicalization>PATIENT-1 VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=defined] the discoverer of AGENT-1 that VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-2 . AGENT-1 epoch VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-4 . DT[form=defined] the celestial body VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a periapsis of PATIENT-3 and DT[form=undefined] a apoapsis of PATIENT-5 .</lexicalization>"):
                "<lexicalization>PATIENT-1 VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=defined] the discoverer of AGENT-1 that VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-2 . PATIENT-1 epoch VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-4 . PATIENT-1 celestial body VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a periapsis of PATIENT-3 and DT[form=undefined] a apoapsis of PATIENT-5 .</lexicalization>",

            ('test/5triples/CelestialBody.xml', 888,
             "<text>107 Camilla, epoch date 31 December 2006, was discovered by C Woods and has an orbital period of 2368.05 days. The apoapsis and periapsis measurements are 560937000.0 km and 479343000.0 km respectively.</text>"):
                "<text>107 Camilla, epoch date 31 December 2006, was discovered by C Woods and has an orbital period of 2368.05 days. 107 Camilla's apoapsis and periapsis measurements are 560937000.0 km and 479343000.0 km respectively.</text>",
            ('test/5triples/CelestialBody.xml', 889,
             "<template>AGENT-1 , epoch date PATIENT-4 , was discovered by PATIENT-1 and has an orbital period of PATIENT-2 . The apoapsis and periapsis measurements are PATIENT-5 and PATIENT-3 respectively .</template>"):
                "<template>AGENT-1 , epoch date PATIENT-4 , was discovered by PATIENT-1 and has an orbital period of PATIENT-2 . AGENT-1 apoapsis and periapsis measurements are PATIENT-5 and PATIENT-3 respectively .</template>",
            ('test/5triples/CelestialBody.xml', 890,
             "<lexicalization>AGENT-1 , epoch date PATIENT-4 , VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] discover by PATIENT-1 and VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-2 . DT[form=defined] the apoapsis and periapsis measurements VP[aspect=simple,tense=present,voice=active,person=non-3rd,number=plural] be PATIENT-5 and PATIENT-3 respectively .</lexicalization>"):
                "<lexicalization>AGENT-1 , epoch date PATIENT-4 , VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] discover by PATIENT-1 and VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-2 . AGENT-1 apoapsis and periapsis measurements VP[aspect=simple,tense=present,voice=active,person=non-3rd,number=plural] be PATIENT-5 and PATIENT-3 respectively .</lexicalization>",

            ('test/5triples/CelestialBody.xml', 961,
             "<text>107 Camilla, which has the epoch date 31 December 2006, was discovered by F Vilas and has an orbital period of 2368.05 days. The apoapsis and periapsis measurements are 560937000.0 kilometres and 479343000.0 kilometres respectively.</text>"):
                "<text>107 Camilla, which has the epoch date 31 December 2006, was discovered by F Vilas and has an orbital period of 2368.05 days. 107 Camilla's apoapsis and periapsis measurements are 560937000.0 kilometres and 479343000.0 kilometres respectively.</text>",
            ('test/5triples/CelestialBody.xml', 962,
             "<template>AGENT-1 , which has the epoch date PATIENT-2 , was discovered by PATIENT-1 and has an orbital period of PATIENT-3 . The apoapsis and periapsis measurements are PATIENT-5 and PATIENT-4 respectively .</template>"):
                "<template>AGENT-1 , which has the epoch date PATIENT-2 , was discovered by PATIENT-1 and has an orbital period of PATIENT-3 . AGENT-1 apoapsis and periapsis measurements are PATIENT-5 and PATIENT-4 respectively .</template>",
            ('test/5triples/CelestialBody.xml', 963,
             "<lexicalization>AGENT-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=defined] the epoch date PATIENT-2 , VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] discover by PATIENT-1 and VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-3 . DT[form=defined] the apoapsis and periapsis measurements VP[aspect=simple,tense=present,voice=active,person=non-3rd,number=plural] be PATIENT-5 and PATIENT-4 respectively .</lexicalization>"):
                "<lexicalization>AGENT-1 , which VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=defined] the epoch date PATIENT-2 , VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] discover by PATIENT-1 and VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a orbital period of PATIENT-3 . AGENT-1 apoapsis and periapsis measurements VP[aspect=simple,tense=present,voice=active,person=non-3rd,number=plural] be PATIENT-5 and PATIENT-4 respectively .</lexicalization>",

            ('test/5triples/CelestialBody.xml', 1357,
             "<text>11264 Claudiomaccone has an epoch date of November 26th 2005, an orbital period of 1513.722 days. a periapsis of 296521000.0 km, an apoapsis of 475426000.0 km, and a temperature of 173.0 kelvins.</text>"):
                "<text>11264 Claudiomaccone has an epoch date of November 26th 2005, an orbital period of 1513.722 days. It has a periapsis of 296521000.0 km, an apoapsis of 475426000.0 km, and a temperature of 173.0 kelvins.</text>",
            ('test/5triples/CelestialBody.xml', 1358,
             "<template>AGENT-1 has an epoch date of PATIENT-1 , an orbital period of PATIENT-2 . a periapsis of PATIENT-3 , an apoapsis of PATIENT-4 , and a temperature of PATIENT-5 .</template>"):
                "<template>AGENT-1 has an epoch date of PATIENT-1 , an orbital period of PATIENT-2 . AGENT-1 has a periapsis of PATIENT-3 , an apoapsis of PATIENT-4 , and a temperature of PATIENT-5 .</template>",
            ('test/5triples/CelestialBody.xml', 1359,
             "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a epoch date of PATIENT-1 , DT[form=undefined] a orbital period of PATIENT-2 . DT[form=undefined] a periapsis of PATIENT-3 , DT[form=undefined] a apoapsis of PATIENT-4 , and DT[form=undefined] a temperature of PATIENT-5 .</lexicalization>"):
                "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a epoch date of PATIENT-1 , DT[form=undefined] a orbital period of PATIENT-2 . AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=null] have DT[form=undefined] a periapsis of PATIENT-3 , DT[form=undefined] a apoapsis of PATIENT-4 , and DT[form=undefined] a temperature of PATIENT-5 .</lexicalization>",
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

            ('test/6triples/Astronaut.xml', 461,
             '<text>Buzz Aldrin was born on 20th January 1930 in Glen Ridge New Jersey. He graduated from MIT in 1963 and was a member of the Apollo 11 crew, operated by NASA. The back up pilot was William Anders.</text>'): '<text>Buzz Aldrin was born on 20th January 1930 in Glen Ridge New Jersey. He graduated from MIT in 1963 and was a member of the Apollo 11 crew, operated by NASA. The back up pilot of Apollo 11 was William Anders.</text>',
            ('test/6triples/Astronaut.xml', 462,
             '<template>AGENT-1 was born on PATIENT-2 in PATIENT-1 . AGENT-1 graduated from PATIENT-3 and was a member of the BRIDGE-1 crew , operated by PATIENT-5 . The back up pilot was PATIENT-4 .</template>'):
                '<template>AGENT-1 was born on PATIENT-2 in PATIENT-1 . AGENT-1 graduated from PATIENT-3 and was a member of the BRIDGE-1 crew , operated by PATIENT-5 . The back up pilot of BRIDGE-1 was PATIENT-4 .</template>',
            ('test/6triples/Astronaut.xml', 463,
             '<lexicalization>AGENT-1 VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] bear on PATIENT-2 in PATIENT-1 . AGENT-1 VP[aspect=simple,tense=past,voice=active,person=null,number=null] graduate from PATIENT-3 and VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a member of DT[form=defined] the BRIDGE-1 crew , VP[aspect=simple,tense=past,voice=active,person=null,number=null] operate by PATIENT-5 . DT[form=defined] the back up pilot VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be PATIENT-4 .</lexicalization>'):
                '<lexicalization>AGENT-1 VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] bear on PATIENT-2 in PATIENT-1 . AGENT-1 VP[aspect=simple,tense=past,voice=active,person=null,number=null] graduate from PATIENT-3 and VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a member of DT[form=defined] the BRIDGE-1 crew , VP[aspect=simple,tense=past,voice=active,person=null,number=null] operate by PATIENT-5 . DT[form=defined] the back up pilot of BRIDGE-1 VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be PATIENT-4 .</lexicalization>',
            ('test/6triples/Astronaut.xml', 960,
             "<text>William Anders, retired, was a member of NASA's @ Apollo 8 after graduating from AFIT in 1962 with an MS. Buzz Aldrin was a back up pilot and Frank Borman a crew member.</text>"):
                "<text>William Anders, retired, was a member of NASA's @ Apollo 8 after graduating from AFIT in 1962 with an MS. Buzz Aldrin was a back up pilot of Apollo 8 and Frank Borman a crew member.</text>",
            ('test/6triples/Astronaut.xml', 961,
             "<template>AGENT-1 , PATIENT-5 , was a member of PATIENT-4 @ BRIDGE-1 after graduating from PATIENT-1 . PATIENT-2 was a back up pilot and PATIENT-3 a crew member .</template>"):
                "<template>AGENT-1 , PATIENT-5 , was a member of PATIENT-4 @ BRIDGE-1 after graduating from PATIENT-1 . PATIENT-2 was a back up pilot of BRIDGE-1 and PATIENT-3 a crew member .</template>",
            ('test/6triples/Astronaut.xml', 962,
             "<lexicalization>AGENT-1 , PATIENT-5 , VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a member of PATIENT-4 BRIDGE-1 after VP[aspect=progressive,tense=present,voice=active,person=null,number=null] graduate from PATIENT-1 . PATIENT-2 VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a back up pilot and PATIENT-3 DT[form=undefined] a crew member .</lexicalization>"):
                "<lexicalization>AGENT-1 , PATIENT-5 , VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a member of PATIENT-4 BRIDGE-1 after VP[aspect=progressive,tense=present,voice=active,person=null,number=null] graduate from PATIENT-1 . PATIENT-2 VP[aspect=simple,tense=past,voice=active,person=null,number=singular] be DT[form=undefined] a back up pilot of BRDIGE-1 and PATIENT-3 DT[form=undefined] a crew member .</lexicalization>",

            ('test/6triples/Monument.xml', 135, '</sentence>'): False,
            ('test/6triples/Monument.xml', 136, '<sentence ID="2">'): False,
            ('test/6triples/Monument.xml', 140,
             '<sentence ID="3">'): '<sentence ID="2">',
            ('test/6triples/Monument.xml', 144,
             '<sentence ID="4">'): '<sentence ID="3">',

            ('test/6triples/University.xml', 99,
             "<text>The Accademia Di Architettura di Mendrisio is located in the city of Mendrisio, region Ticino in Switzerland. It was founded in 1996 and the dean is Mario Botta. There is currently 100 members of staff.</text>"):
                "<text>The Accademia Di Architettura di Mendrisio is located in the city of Mendrisio, region Ticino in Switzerland. It was founded in 1996 and the dean is Mario Botta. There is currently 100 members of staff in the Accademia Di Architettura di Mendrisio.</text>",
            ('test/6triples/University.xml', 100,
             "<template>AGENT-1 is located in the city of PATIENT-3 , region PATIENT-6 in PATIENT-1 . AGENT-1 was founded in PATIENT-4 and the dean is PATIENT-2 . There is currently PATIENT-5 members of staff .</template>"):
                "<template>AGENT-1 is located in the city of PATIENT-3 , region PATIENT-6 in PATIENT-1 . AGENT-1 was founded in PATIENT-4 and the dean is PATIENT-2 . There is currently PATIENT-5 members of staff in AGENT-1 .</template>",
            ('test/6triples/University.xml', 101,
             "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in DT[form=defined] the city of PATIENT-3 , region PATIENT-6 in PATIENT-1 . AGENT-1 VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] found in PATIENT-4 and DT[form=defined] the dean VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 . There VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be currently PATIENT-5 members of staff in AGENT-1.</lexicalization>"):
                "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in DT[form=defined] the city of PATIENT-3 , region PATIENT-6 in PATIENT-1 . AGENT-1 VP[aspect=simple,tense=past,voice=passive,person=null,number=singular] found in PATIENT-4 and DT[form=defined] the dean VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 . There VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be currently PATIENT-5 members of staff in AGENT-1.</lexicalization>",

            ('test/6triples/University.xml', 601,
             "<text>The 1 Decembrie 1918 University is located in Romania. Romania's capital is Bucharest; its leader is Klaus Iohannis and its patron saint is Andrew the Apostle. The ethnic group is the Germans of Romania and the anthem is Desteapta-te, romane!</text>"):
                "<text>The 1 Decembrie 1918 University is located in Romania. Romania's capital is Bucharest; its leader is Klaus Iohannis and its patron saint is Andrew the Apostle. Romania's ethnic group is the Germans of Romania and the anthem is Desteapta-te, romane!</text>",
            ('test/6triples/University.xml', 602,
             "<template>AGENT-1 is located in BRIDGE-1 . BRIDGE-1 capital is PATIENT-4 ; BRIDGE-1 leader is PATIENT-2 and BRIDGE-1 patron saint is PATIENT-3 . The ethnic group is PATIENT-1 and the anthem is PATIENT-5</template>"):
                "<template>AGENT-1 is located in BRIDGE-1 . BRIDGE-1 capital is PATIENT-4 ; BRIDGE-1 leader is PATIENT-2 and BRIDGE-1 patron saint is PATIENT-3 . BRIDGE-1 ethnic group is PATIENT-1 and the anthem is PATIENT-5</template>",
            ('test/6triples/University.xml', 603,
             "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in BRIDGE-1 . BRIDGE-1 capital VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-4 ; BRIDGE-1 leader VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 and BRIDGE-1 patron saint VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-3 . DT[form=defined] the ethnic group VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-1 and DT[form=defined] the anthem VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-5</lexicalization>"):
                "<lexicalization>AGENT-1 VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be located in BRIDGE-1 . BRIDGE-1 capital VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-4 ; BRIDGE-1 leader VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-2 and BRIDGE-1 patron saint VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-3 . AGENT-1 ethnic group VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-1 and DT[form=defined] the anthem VP[aspect=simple,tense=present,voice=active,person=3rd,number=singular] be PATIENT-5</lexicalization>",
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
