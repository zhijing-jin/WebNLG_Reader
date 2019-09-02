from itertools import chain
from os import listdir, path
from os.path import isdir

import xmltodict
import os
import re
import sys
import json

sys.path.append(os.path.abspath('.'))
from utils import Cleaner, misspelling, rephrase, rephrase_if_must, DataReader, \
    DataSetType

from efficiency.log import show_var, fwrite
from efficiency.nlp import NLP
from efficiency.function import shell


class RDFFileReader:
    def __init__(self, file_name):
        self.cleaner = Cleaner()
        self.cleaner.clean(file_name)

        self.nlp = NLP()

        self.data = []
        self.file_name = file_name
        self.cnt_dirty_data = 0

        content = open(file_name, encoding="utf-8").read()

        structure = xmltodict.parse(content)
        for entry_ix, entry in enumerate(
                self.triplets_from_object(structure["benchmark"]["entries"],
                                          "entry")):
            self.entry_ix = entry['@eid']

            triplets = [tuple(map(str.strip, r.split("|"))) for r in
                        self.triplets_from_object(entry["modifiedtripleset"],
                                                  "mtriple")]

            entitymaps = dict([tuple(map(str.strip, entitymap.split("|")))
                               for entitymap in
                               self.triplets_from_object(entry['entitymap'],
                                                         'entity')])

            sentences = list(self.extract_sentences(entry["lex"]))

            for s_tripleset, text, template in sentences:
                s_tripleset, template, text, ner2ent = \
                    self._tokenize(s_tripleset, template, text, entitymaps)

                tripleset_str = ['\t'.join(triple) for triple in s_tripleset]
                tripleset_str = ';;\t'.join(tripleset_str)
                self.data.append(
                    {
                        # 'rdfs': triplets,
                        'triples': tripleset_str,
                        'target': template,
                        'target_txt': text,
                        'ner2ent': ner2ent,
                    })
        if self.cnt_dirty_data: show_var(["self.cnt_dirty_data"])

    def _tokenize(self, s_tripleset, template, text, entitymaps):
        '''
        :param s_tripleset: strips quotes, replaces "-" to "_" for each party
        :param template: replaces "-" to "_", then tokenization
        :param text: tokenization
        :param ner2ent: strips quotes, replaces "-" to "_"
        :return:
        '''

        def _clean_term(term):
            return term.replace('-', '_').strip('\"')

        template = self.fix_template(template)

        all_phrases = list(
            chain.from_iterable([triple for triple in s_tripleset]))
        ner2ent = {k: v for k, v in entitymaps.items() if (k in template) or
                   ({k, v} & set(all_phrases))}
        entities = set(ner2ent.keys())
        ner2ent = {_clean_term(k): _clean_term(v) for k, v in ner2ent.items()}

        # replaces '-' with '_' only in entity types
        for enti in entities:
            template = template.replace(enti, _clean_term(enti))
        template = template.replace('BRIDGE-', 'BRIDGE_')
        template = template.replace('AGENT-', 'AGENT_')
        template = template.replace('PATIENT-', 'PATIENT_')

        # tokenization
        text = self.nlp.word_tokenize(text)
        template = self.nlp.word_tokenize(template)
        s_tripleset = [(_clean_term(subj), _clean_term(predi), _clean_term(obj))
                       for subj, predi, obj in s_tripleset]

        # all_phrases += list(
        #     chain.from_iterable([item for item in entitymaps.items()]))
        # punctuations = re.sub(r'[a-zA-Z0-9_\s,ü(İ)Æğ]', '', ''.join(all_phrases))
        # if punctuations: import pdb;pdb.set_trace()
        return s_tripleset, template, text, ner2ent

    def extract_sentences(self, lex):
        sentences = lex
        if not isinstance(sentences, list):
            sentences = [sentences]

        for s in sentences:
            if s['@comment'] == 'bad': continue

            s_tripleset_raw = [[tuple(map(str.strip, r.split("|")))
                                for r in
                                self.triplets_from_object(s_triples, 'striple')]
                               for s_triples in
                               self.triplets_from_object(s["sortedtripleset"],
                                                         'sentence') if
                               s_triples]
            s_tripleset = [s for s in s_tripleset_raw if s]
            self.cnt_dirty_data += len(s_tripleset_raw) - len(s_tripleset)

            if not s_tripleset: continue
            if len(s_tripleset) <= 1:
                text = [self.fix_sent(s["text"])]
                template = [s["template"]]
            else:
                text = self.nlp.sent_tokenize(self.fix_sent(s["text"]))
                text = self.fix_tokenize(text)
                template = self.nlp.sent_tokenize(s["template"])

            if len(set([len(template), len(text), len(s_tripleset)])) != 1:
                # import pdb;
                # pdb.set_trace()
                self.cnt_dirty_data += 1
                continue

            for s_t, te, tem in zip(s_tripleset, text, template):
                if not s_t: import pdb;pdb.set_trace()
                yield s_t, te, tem

    def fix_template(self, template):
        template = template.replace('AEGNT-1', 'AGENT-1')
        template = template.replace('AAGENT-1', 'AGENT-1')
        template = template.replace('AGENT-1(area', 'AGENT-1 (area')
        template = template.replace('AGENT-1(has', 'AGENT-1 (has')
        template = template.replace('AGENT-1(mass', 'AGENT-1 (mass')
        template = template.replace('AGENT-1is', 'AGENT-1 is')

        template = template.replace('BRUDGE-1', 'BRIDGE-1')
        template = template.replace('BRIDGE-1which', 'BRIDGE-1 which')
        template = template.replace(' RIDGE-2', ' BRIDGE-2')

        template = template.replace('PATIENTI-2', 'PATIENT-2')
        template = template.replace('havePATIENT-3', 'have PATIENT-3')
        template = template.replace('byPATIENT-1', 'by PATIENT-1')
        template = template.replace('PATIENT-1.AGENT-1', 'PATIENT-1 . AGENT-1')
        template = template.replace('PATIENT-2.AGENT-1', 'PATIENT-2 . AGENT-1')
        template = template.replace('PATIENT-4.BRIDGE-1',
                                    'PATIENT-4 . BRIDGE-1')
        template = template.replace('PATIENT-2-operated', 'PATIENT-2 -operated')
        return template

    def fix_sent(self, sentence):
        sentence = sentence.replace(
            'Sour cream, chopped fruits, condensed milk. granola, raisins and shredded coconut are the main ingredients in Bionico.',
            'Sour cream, chopped fruits, condensed milk, granola, raisins and shredded coconut are the main ingredients in Bionico.')
        sentence = sentence.replace(' (abbrv. Acta Palaeontol. Pol)',
                                    ' (abbrv Acta Palaeontol Pol)')
        return sentence

    def fix_tokenize(self, sentences):
        if sentences == [
            'The 11th Mississippi INfantry Monument is located in the municipality of Gettysburg, Adams County, Pa. It is categorized as a Contributing Property and was established in 2000.',
            'Carrol County, Maryland is southeast of Adams County, Pennsylvania.']:
            sentences = [
                'The 11th Mississippi INfantry Monument is located in the municipality of Gettysburg, Adams County, Pa.',
                'It is categorized as a Contributing Property and was established in 2000.',
                'Carrol County, Maryland is southeast of Adams County, Pennsylvania.']
        elif sentences == [
            'The 11th Mississipi Infantry Monument was established in 2000 and it is located in Adams County, Pa. The Monument is categorised as a contributing property.',
            'To the north of Adams County is Cumberland County (Pa), to its west is Franklin County (Pa) and to its southeast is Carrol County (Maryland).']:
            sentences = [
                'The 11th Mississipi Infantry Monument was established in 2000 and it is located in Adams County, Pa.',
                'The Monument is categorised as a contributing property.',
                'To the north of Adams County is Cumberland County (Pa), to its west is Franklin County (Pa) and to its southeast is Carrol County (Maryland).']
        elif sentences == [
            'United States @ test pilot @ Alan Bean was born in Wheeler, Texas.',
            'In 1955, he graduated from UT Austin with a B.S. Chosen by NASA in 1963, he managed a total space time of 100305.0 minutes.']:
            sentences = [
                'United States @ test pilot @ Alan Bean was born in Wheeler, Texas.',
                'In 1955, he graduated from UT Austin with a B.S.',
                'Chosen by NASA in 1963, he managed a total space time of 100305.0 minutes.']
        elif sentences == [
            'Alan Bean was originally from Wheeler, Texas and graduated from UT Austin in 1955 with a B.S. He went on to work as a test pilot and became a crew member of the Apollo 12 mission before he @ retired .']:
            sentences = [
                'Alan Bean was originally from Wheeler, Texas and graduated from UT Austin in 1955 with a B.S.',
                'He went on to work as a test pilot and became a crew member of the Apollo 12 mission before he @ retired .']
        elif sentences == [
            'Alan Bean is originally from Wheeler in Texas and graduated from UT Austin in 1955 with a B.S. He then went on to become a test pilot and became a member of the Apollo 12 crew where he spent 100305.0 minutes in space.']:
            sentences = [
                'Alan Bean is originally from Wheeler in Texas and graduated from UT Austin in 1955 with a B.S.',
                'He then went on to become a test pilot and became a member of the Apollo 12 crew where he spent 100305.0 minutes in space.']

        elif sentences == [
            'The American @ Alan Bean was born on the 15th of March 1932 in Wheeler, Texas.',
            'He graduated in 1955 from UT Austin with a B.S. He worked as a test pilot.']:
            sentences = [
                'The American @ Alan Bean was born on the 15th of March 1932 in Wheeler, Texas.',
                'He graduated in 1955 from UT Austin with a B.S.',
                'He worked as a test pilot.']
        elif sentences == [
            'Alan Bean was born in Wheeler, Texas and graduated in 1955 from UT Austin with a B.S. He performed as a test pilot and was chosen by NASA in 1963 to be the crew of Apollo 12.']:
            sentences = [
                'Alan Bean was born in Wheeler, Texas and graduated in 1955 from UT Austin with a B.S.',
                'He performed as a test pilot and was chosen by NASA in 1963 to be the crew of Apollo 12.']
        elif sentences == [
            'Alan Bean (born on March 15, 1932) graduated from UT Austin in 1955 with a B.S. Alan Bean who was chosen by NASA in 1963 is an American born in Wheeler, Texas.']:
            sentences = [
                'Alan Bean (born on March 15, 1932) graduated from UT Austin in 1955 with a B.S.',
                'Alan Bean who was chosen by NASA in 1963 is an American born in Wheeler, Texas.']
        elif sentences == [
            'Alan Shepherd born in New Hampshire, United States, graduated from NWC in 1957 with a M.A. He served as a crew member on Apollo 12 and retired in 1974.']:
            sentences = [
                'Alan Shepherd born in New Hampshire, United States, graduated from NWC in 1957 with a M.A.',
                'He served as a crew member on Apollo 12 and retired in 1974.']
        elif sentences == [
            'Alan Shepard was born in New Hampshire and graduated from NWC in 1957 with a M.A. Alan went on to become a test pilot and joined NASA in 1959.',
            'He later died in California.']:
            sentences = [
                'Alan Shepard was born in New Hampshire and graduated from NWC in 1957 with a M.A.',
                'Alan went on to become a test pilot and joined NASA in 1959.',
                'He later died in California.']
        elif sentences == [
            'Buzz Aldrin was born on Jan 20th, 1930 and his full name is Edwin E. Aldrin Jr. He graduated from MIT in 1963 with a doctorate in Science.',
            'He was a fighter pilot and a crew member of Apollo 11.',
            'He is now retired.']:
            sentences = [
                'Buzz Aldrin was born on Jan 20th, 1930 and his full name is Edwin E. Aldrin Jr.',
                'He graduated from MIT in 1963 with a doctorate in Science.',
                'He was a fighter pilot and a crew member of Apollo 11.',
                'He is now retired.']
        elif sentences == [
            'American @ Buzz Aldrin was born in Glen Ridge, New Jersey on January 20th, 1930.',
            'In 1963 he graduated from MIT with a Sc.',
            'D then became a fighter pilot and later a member of the Apollo 11 crew.']:
            sentences = [
                'American @ Buzz Aldrin was born in Glen Ridge, New Jersey on January 20th, 1930.',
                'In 1963 he graduated from MIT with a Sc. D then became a fighter pilot and later a member of the Apollo 11 crew.']
        elif sentences == [
            'Edwin E. Aldrin Jr. (more commonly known as Buzz) was born on January 20th, 1930.',
            'He graduated in 1963 from MIT with a Sc.',
            'D. befor becoming a fighter pilot and later a crew member of Apollo 11.']:
            sentences = [
                'Edwin E. Aldrin Jr. (more commonly known as Buzz) was born on January 20th, 1930.',
                'He graduated in 1963 from MIT with a Sc. D. befor becoming a fighter pilot and later a crew member of Apollo 11.']
        elif sentences == [
            'Buzz Aldrin was an American, who was born in Glen Ridge, NJ and graduated from MIT, Sc.',
            'D. in 1963.',
            'He was a fighter pilor and a member of the Apollo 11 crew.']:
            sentences = [
                'Buzz Aldrin was an American, who was born in Glen Ridge, NJ and graduated from MIT, Sc. D. in 1963.',
                'He was a fighter pilor and a member of the Apollo 11 crew.']
        elif sentences == [
            'Buzz Aldrin was a United States national who was born in Glen Ridge, New Jersey.',
            'He graduated from MIT with a Sc.', 'D in 1963.',
            'He served as a fighter pilot and became a crew member on Apollo 11.']:
            sentences = [
                'Buzz Aldrin was a United States national who was born in Glen Ridge, New Jersey.',
                'He graduated from MIT with a Sc. D in 1963.',
                'He served as a fighter pilot and became a crew member on Apollo 11.']
        elif sentences == [
            'Buzz Aldrin who was originally from New Jersey graduated from MIT with a Sc.',
            'D in 1963.',
            'He then went on to join NASA in 1963 and became a member of the Apollo 11 crew.']:
            sentences = [
                'Buzz Aldrin who was originally from New Jersey graduated from MIT with a Sc. D in 1963.',
                'He then went on to join NASA in 1963 and became a member of the Apollo 11 crew.']
        elif sentences == [
            'Buzz Aldrin is originally from Glen Ridge , New Jersey and graduated from MIT with a Sc.',
            'D in 1963.',
            'Buzz then went on to join NASA in 1963 and became a crew member of Apollo 11.']:
            sentences = [
                'Buzz Aldrin is originally from Glen Ridge , New Jersey and graduated from MIT with a Sc. D in 1963.',
                'Buzz then went on to join NASA in 1963 and became a crew member of Apollo 11.']
        elif sentences == [
            'Buzz Aldrin was born on the 20th of January, 1930 in Glen Ridge, New Jersey.',
            'He graduated from Massachusetts Institute of Technology, Sc.',
            'D. in 1963 and was selected to work for NASA the same year.',
            'He served as a crew member on Apollo 11.']:
            sentences = [
                'Buzz Aldrin was born on the 20th of January, 1930 in Glen Ridge, New Jersey.',
                'He graduated from Massachusetts Institute of Technology, Sc. D. in 1963 and was selected to work for NASA the same year.',
                'He served as a crew member on Apollo 11.']
        elif sentences == ['Buzz Aldrin graduated from MIT with a Sc.',
                           'D in 1963.',
                           'He was a fighter pilot and crew member of Apollo 11, which was organized by NASA.',
                           'William Anders was a back up pilot on the Apollo 11 mission.']:
            sentences = ['Buzz Aldrin graduated from MIT with a Sc. D in 1963.',
                         'He was a fighter pilot and crew member of Apollo 11, which was organized by NASA.',
                         'William Anders was a back up pilot on the Apollo 11 mission.']
        elif sentences == ['Buzz Aldrin graduated from MIT with a Sc.',
                           'D in 1963 and went on to become a fighter pilot with NASA .',
                           'He also became a part of the Apollo 11 crew.']:
            sentences = [
                'Buzz Aldrin graduated from MIT with a Sc. D in 1963 and went on to become a fighter pilot with NASA .',
                'He also became a part of the Apollo 11 crew.']
        elif sentences == [
            'William Anders who was born on October 17th 1933 in Hong Kong graduated in 1962 with a M.S. William Anders went on to become a member of the Apollo 8 crew and retired in 1969.']:
            sentences = [
                'William Anders who was born on October 17th 1933 in Hong Kong graduated in 1962 with a M.S.',
                'William Anders went on to become a member of the Apollo 8 crew and retired in 1969.']
        elif sentences == [
            'Elliot See was originally from Dallas and graduated from the University of Texas at Austin.',
            'He worked as a test pilot and died in St.',
            'Louis on the 28th February 1966.']:
            sentences = [
                'Elliot See was originally from Dallas and graduated from the University of Texas at Austin.',
                'He worked as a test pilot and died in St. Louis on the 28th February 1966.']
        elif sentences == [
            'Elliot See graduated from the University of Texas at Austin who are competing in the Big 12 Conference.',
            'Elliot See died in St.', 'Louis on February 28, 1966.']:
            sentences = [
                'Elliot See graduated from the University of Texas at Austin who are competing in the Big 12 Conference.',
                'Elliot See died in St. Louis on February 28, 1966.']
        elif sentences == [
            'Elliot See attended the University of Texas at Austin.',
            'The university is affiliated with the University of Texas System and it competed in the Big 12 Conference in Austin.',
            'The president of the university was Gregory L. Fenves.',
            'Elliot See died in St Louis.', 'The leader of St.',
            'Louis was Francis G. Slay.']:
            sentences = [
                'Elliot See attended the University of Texas at Austin.',
                'The university is affiliated with the University of Texas System and it competed in the Big 12 Conference in Austin.',
                'The president of the university was Gregory L. Fenves.',
                'Elliot See died in St Louis.',
                'The leader of St. Louis was Francis G. Slay.']
        elif sentences == [
            'Elliot See is originally from Dallas and joined NASA in 1962 where he flew as a test pilot.',
            'Elliot See died in St.', 'Louis.']:
            sentences = [
                'Elliot See is originally from Dallas and joined NASA in 1962 where he flew as a test pilot.',
                'Elliot See died in St. Louis.']
        elif sentences == [
            'B.M.Reddy is the President of the Acharya Institute of Technology which was founded in 2000 in India.',
            'The institute is also strongly connected to the Visvesvaraya Technological University which is located in Belgaum.',
            'The exact location for the Acharya Institute of Technology is " In Soldevanahalli, Acharya Dr.',
            'Sarvapalli Radhakrishnan Road, Hessarghatta Main Road, Bangalore - 560090.']:
            sentences = [
                'B.M.Reddy is the President of the Acharya Institute of Technology which was founded in 2000 in India.',
                'The institute is also strongly connected to the Visvesvaraya Technological University which is located in Belgaum.',
                'The exact location for the Acharya Institute of Technology is In Soldevanahalli, Acharya Dr. Sarvapalli Radhakrishnan Road, Hessarghatta Main Road, Bangalore - 560090.']
        elif sentences == [
            '1 Decembrie 1918 University is in the country of Romania, the capital of which is Bucharest.',
            "Romania's leader (who has the title Prime Minister) is Klaus Iohannis.",
            'The national anthem of Romania is Deșteaptă-te, române!',
            'and the country has an ethnic group called Germans of Romania.']:
            sentences = [
                '1 Decembrie 1918 University is in the country of Romania, the capital of which is Bucharest.',
                "Romania's leader (who has the title Prime Minister) is Klaus Iohannis.",
                'The national anthem of Romania is Deșteaptă-te, române! and the country has an ethnic group called Germans of Romania.']
        elif sentences == [
            'The Acharya Institute of Technology was founded in 2000 in the country India and has 700 postgraduate students.',
            'The institute has connections with the Visvesvaraya Technological University which is located in Belgaum.',
            'The exact location for the Acharya Institute of Technology is " In Soldevanahalli, Acharya Dr.',
            'Sarvapalli Radhakrishnan Road, Hessarghatta Main Road, Bangalore - 560090.".']:
            sentences = [
                'The Acharya Institute of Technology was founded in 2000 in the country India and has 700 postgraduate students.',
                'The institute has connections with the Visvesvaraya Technological University which is located in Belgaum.',
                'The exact location for the Acharya Institute of Technology is " In Soldevanahalli, Acharya Dr. Sarvapalli Radhakrishnan Road, Hessarghatta Main Road, Bangalore - 560090.".']
        elif sentences == [
            'The city of Aarhus in Denmark is served by an airport callled Aarhus Airport operated by Aarhus Lufthavn A/S. Runway 10L/28R is the longest runway there at a length of 2702 and is 25m above sea level.']:
            sentences = [
                'The city of Aarhus in Denmark is served by an airport callled Aarhus Airport operated by Aarhus Lufthavn A/S.',
                'Runway 10L/28R is the longest runway there at a length of 2702 and is 25m above sea level.']
        elif sentences == [
            'Aarhus Airport, which serves the city of Aarhus in Denmark, has a runway length of 2,776 and is named 10R/28L. Aktieselskab operates the airport which is 25 metres above sea level.']:
            sentences = [
                'Aarhus Airport, which serves the city of Aarhus in Denmark, has a runway length of 2,776 and is named 10R/28L.',
                'Aktieselskab operates the airport which is 25 metres above sea level.']
        elif sentences == [
            'Aarhus Airport in Denmark is operated by Aarhus Lufthavn A/S. The airport lies 25 metres above sea level and has a runway named 10R/28L which is 2776.0 metres long.']:
            sentences = [
                'Aarhus Airport in Denmark is operated by Aarhus Lufthavn A/S.',
                'The airport lies 25 metres above sea level and has a runway named 10R/28L which is 2776.0 metres long.']
        elif sentences == [
            'Aarhus Airport is located in Aarhus, Denmark and is operated by Aarhus Lufthavn A/S. The airport lies 25 metres above sea level and has a runway named 10L/28R which is 2777 metres long.']:
            sentences = [
                'Aarhus Airport is located in Aarhus, Denmark and is operated by Aarhus Lufthavn A/S.',
                'The  airport lies 25 metres above sea level and has a runway named 10L/28R which is 2777 metres long.']
        elif sentences == [
            'Aarhus airport services the city of Aarhus, Denmark and operated by Aarhus Lufthaven A/S. The airport is 25 meters above sea level and the 10L/28R runway is 2777.0 in length.']:
            sentences = [
                'Aarhus airport services the city of Aarhus, Denmark and operated by Aarhus Lufthaven A/S.',
                'The airport is 25 meters above sea level and the 10L/28R runway is 2777.0 in length.']
        elif sentences == [
            'The runway length of Adolfo Suárez Madrid–Barajas Airport is 3,500 and has the name 14L/32R. It is located at 610 metres above sea level in Madrid and is operated by ENAIRE.']:
            sentences = [
                'The runway length of Adolfo Suárez Madrid–Barajas Airport is 3,500 and has the name 14L/32R.',
                'It is located at 610 metres above sea level in Madrid and is operated by ENAIRE.']
        elif sentences == [
            'Aarhus Airport is located in Aarhus, Denmark, and is operated by Aarhus Lufthavn A/S. The airport is 25 meters above sea level, measuring 2777.0 in length, dubbed 10R/28L.']:
            sentences = [
                'Aarhus Airport is located in Aarhus, Denmark, and is operated by Aarhus Lufthavn A/S.',
                'The airport is 25 meters above sea level, measuring 2777.0 in length, dubbed 10R/28L.']
        elif sentences == [
            'Abilene Regional airport has a runway length of 1121.0 and is named 17L/35R. The airport serves Abilene in Texas, has the ICAO location identifier of KABI and is 546 metres above sea level.']:
            sentences = [
                'Abilene Regional airport has a runway length of 1121.0 and is named 17L/35R.',
                'The airport serves Abilene in Texas, has the ICAO location identifier of KABI and is 546 metres above sea level.']
        elif sentences == [
            'Abilene, Texas is served by the Abilene regional airport which is 546 metres above sea level.',
            'The airport has the ICAO Location Identifier, KABI, as well as having the runway name 17R/35L. One of the runways is 1121.0 metres long.']:
            sentences = [
                'Abilene, Texas is served by the Abilene regional airport which is 546 metres above sea level.',
                'The airport has the ICAO Location Identifier, KABI, as well as having the runway name 17R/35L.',
                'One of the runways is 1121.0 metres long.']
        elif sentences == [
            'Adolfo Suárez Madrid–Barajas Airport can be found in Madrid, Paracuellos de Jarama, San Sebastián de los Reyes and Alcobendas.',
            'It is operated by the ENAIRE organization.',
            "The airports's runway name is 18L/36R and its length is 3500 m. It is 610 m above sea level."]:
            sentences = [
                'Adolfo Suárez Madrid–Barajas Airport can be found in Madrid, Paracuellos de Jarama, San Sebastián de los Reyes and Alcobendas.',
                'It is operated by the ENAIRE organization.',
                "The airports's runway name is 18L/36R and its length is 3500 m.",
                "It is 610 m above sea level."]
        elif sentences == [
            'Operated by the United States Air Force, Al Asad Airbase is located in Al Anbar Province, Iraq.',
            "The Airbase's runway name is 09L/27R. Its ICAO Location Identifier is ORAA and 3992.88 is the length of the runway."]:
            sentences = [
                'Operated by the United States Air Force, Al Asad Airbase is located in Al Anbar Province, Iraq.',
                "The Airbase's runway name is 09L/27R.",
                "Its ICAO Location Identifier is ORAA and 3992.88 is the length of the runway."]
        elif sentences == [
            'Alpena County Regional Airport is located in Maple Ridge Township, Alpena County, Michigan and serves Alpena, Michigan.',
            'Its runway length is 1,533 and is named is 1/19/. The airport is 210 metres above sea level.']:
            sentences = [
                'Alpena County Regional Airport is located in Maple Ridge Township, Alpena County, Michigan and serves Alpena, Michigan.',
                'Its runway length is 1,533 and is named is 1/19/.',
                'The airport is 210 metres above sea level.']
        elif sentences == [
            'Alpena County Regional Airport city serves Alpena, Michigan in Wilson Township in the U.S. The airport is 210 m above sea level and 1533 m long.']:
            sentences = [
                'Alpena County Regional Airport city serves Alpena, Michigan in Wilson Township in the U.S.',
                'The airport is 210 m above sea level and 1533 m long.']
        elif sentences == [
            "Alpena County Regional Airport, which serves the city of Alpena, is located in Wilson Township, Alpena County, Michigan in the U.S.A. It's runway is 2,744 metres long and the facility is 210 metres above sea level."]:
            sentences = [
                "Alpena County Regional Airport, which serves the city of Alpena, is located in Wilson Township, Alpena County, Michigan in the U.S.A.",
                "It's runway is 2,744 metres long and the facility is 210 metres above sea level."]
        elif sentences == [
            'Andrews County Airport is located in Texas, U.S. The inhabitants of Texas have the demonym of Tejano and Spanish is spoken.',
            'The capital is Austin.']:
            sentences = ['Andrews County Airport is located in Texas, U.S.',
                         'The inhabitants of Texas have the demonym of Tejano and Spanish is spoken.',
                         'The capital is Austin.']
        elif sentences == [
            'Texas maintains the capital as Austin and is the home of Houston (the largest city in TX.)',
            'and the Andrews County Airport.', 'Tejanos are people of Texas.']:
            sentences = [
                'Texas maintains the capital as Austin and is the home of Houston (the largest city in TX.) and the Andrews County Airport.',
                'Tejanos are people of Texas.']
        elif sentences == [
            'Andrews County Airport is located in Texas in the U.S. The capital of Texas is Austin and its largest city is Houston.',
            'English is spoken in that state.']:
            sentences = [
                'Andrews County Airport is located in Texas in the U.S.',
                'The capital of Texas is Austin and its largest city is Houston.',
                'English is spoken in that state.']
        elif sentences == [
            "Atlantic City International Airport in Egg Harbor Township, N.J. serves Atlantic City in the U.S.A. The city's leader is Don Guardian."]:
            sentences = [
                "Atlantic City International Airport in Egg Harbor Township, N.J. serves Atlantic City in the U.S.A.",
                "The city's leader is Don Guardian."]
        elif sentences == [
            'Atlantic City International Airport serves the city of Atlantic City, New Jersey in the U.S.A. The airport is in Egg Harbor Township, New Jersey.',
            'The Atlantic City, New Jersey leader is Don Guardian.']:
            sentences = [
                'Atlantic City International Airport serves the city of Atlantic City, New Jersey in the U.S.A.',
                'The airport is in Egg Harbor Township, New Jersey.',
                'The Atlantic City, New Jersey leader is Don Guardian.']
        elif sentences == [
            'Atlantic City International Airport in Egg Harbor Township, New Jersey is in the U.S.A. The airport has a runway that is 1,873 long.']:
            sentences = [
                'Atlantic City International Airport in Egg Harbor Township, New Jersey is in the U.S.A.',
                'The airport has a runway that is 1,873 long.']
        elif sentences == [
            'Bacon Explosion which has bacon and sausage in it comes from Kansas City metro area in the U.S. The Bacon Explosion is a main course.']:
            sentences = [
                'Bacon Explosion which has bacon and sausage in it comes from Kansas City metro area in the U.S.',
                'The Bacon Explosion is a main course.']
        elif sentences == [
            'The bacon explosion took place in the U.S.A. where Paul Ryan is leader.',
            "The country's capital is Washington, D.C. The president leads the U.S. and among its ethnic groups are white Americans."]:
            sentences = [
                'The bacon explosion took place in the U.S.A. where Paul Ryan is leader.',
                "The country's capital is Washington, D.C.",
                "The president leads the U.S. and among its ethnic groups are white Americans."]
        elif sentences == [
            'The Bacon Explosion comes from the United States, a country whose leader has the title of President and whose capital is Washington, D.C. One of the leaders of the U.S. is Barack Obama and one of the ethnic groups is the African Americans.']:
            sentences = [
                'The Bacon Explosion comes from the United States, a country whose leader has the title of President and whose capital is Washington, D.C.',
                'One of the leaders of the U.S. is Barack Obama and one of the ethnic groups is the African Americans.']
        elif sentences == [
            'Bacon Explosion comes from the United States where Asian Americans are an ethnic group and the capital is Washington, D.C. The leader of the United States is called the President and this is Barack Obama.']:
            sentences = [
                'Bacon Explosion comes from the United States where Asian Americans are an ethnic group and the capital is Washington, D.C.',
                'The leader of the United States is called the President and this is Barack Obama.']
        elif sentences == [
            'White Americans are one of the ethnic groups in the United States, a country where the the leader is called the President and Washington, D.C. is the capital city.',
            'Joe Biden is a political leader in the U.S. The country is also the origin of Bacon Explosion.']:
            sentences = [
                'White Americans are one of the ethnic groups in the United States, a country where the the leader is called the President and Washington, D.C. is the capital city.',
                'Joe Biden is a political leader in the U.S.',
                'The country is also the origin of Bacon Explosion.']
        elif sentences == [
            '200 Public Square is in Cleveland, Ohio (part of Cuyahoga County) in the U.S. It has 45 floors.']:
            sentences = [
                '200 Public Square is in Cleveland, Ohio (part of Cuyahoga County) in the U.S.',
                'It has 45 floors.']
        elif sentences == [
            '300 North LaSalle is in Chicago which is part of Cook County, Illinois in the U.S. The leader is Susana Mendoza.']:
            sentences = [
                '300 North LaSalle is in Chicago which is part of Cook County, Illinois in the U.S.',
                'The leader is Susana Mendoza.']
        elif sentences == [
            "300 North LaSalle, with 60 floors, is located in Chicago, Illinois, U.S.. Chicago's leader is called Rahm Emanuel."]:
            sentences = [
                "300 North LaSalle, with 60 floors, is located in Chicago, Illinois, U.S.",
                "Chicago's leader is called Rahm Emanuel."]
        elif sentences == [
            'The address of Amdavad ni Gufa is Lalbhai Dalpatbhai Campus, near CEPT University, opp.',
            'Gujarat University, University Road, Gujarat, Ahmedabad, India.',
            'Amdavad ni Gufa was completed in 1995.']:
            sentences = [
                'The address of Amdavad ni Gufa is Lalbhai Dalpatbhai Campus, near CEPT University, opp. Gujarat University, University Road, Gujarat, Ahmedabad, India.',
                'Amdavad ni Gufa was completed in 1995.']
        elif sentences == [
            'Asilomar Conference Grounds which was constructed in 1913 in the architectural style of American Craftsman is located at Asilomar Blvd.,',
            'Pacific Grove, California.',
            'It was added to the National Register of Historic Places on 27 February 1987 with the reference number 87000823.']:
            sentences = [
                'Asilomar Conference Grounds which was constructed in 1913 in the architectural style of American Craftsman is located at Asilomar Blvd., Pacific Grove, California.',
                'It was added to the National Register of Historic Places on 27 February 1987 with the reference number 87000823.']
        elif sentences == [
            'The location of Asilomar Conference Grounds which were constructed in 1913 is Asilomar Blvd.,',
            'Pacific Grove, California.',
            'They were added to the National Register of Historic Places on 27 February 1987 with the reference number "87000823", and were built in the Arts and Crafts Movement architectural style.']:
            sentences = [
                'The location of Asilomar Conference Grounds which were constructed in 1913 is Asilomar Blvd., Pacific Grove, California.',
                'They were added to the National Register of Historic Places on 27 February 1987 with the reference number "87000823", and were built in the Arts and Crafts Movement architectural style.']
        elif sentences == [
            'Asser Levy Public Baths are found in New York City, Manhattan, New York, in the U.S.. Cyrus Vance Jr. is one of the leaders of Manhattan.']:
            sentences = [
                'Asser Levy Public Baths are found in New York City, Manhattan, New York, in the U.S..',
                'Cyrus Vance Jr. is one of the leaders of Manhattan.']
        elif sentences == [
            'Baymax is a character in the film Big Hero 6 which stars Damon Wayans Jr. He was created by Steven t Seagle and the American, Duncan Rouleau.']:
            sentences = [
                'Baymax is a character in the film Big Hero 6 which stars Damon Wayans Jr.',
                'He was created by Steven t Seagle and the American, Duncan Rouleau.']
        elif sentences == [
            'Stuart Parker plays for KV Mechelen and the Blackburn Rovers F.C. AFC Blackpool(Blackpool) had Stuart Parker as their manager.',
            'The Conservative Party U.K. is the leader of Blackpool.']:
            sentences = [
                'Stuart Parker plays for KV Mechelen and the Blackburn Rovers F.C.',
                'AFC Blackpool(Blackpool) had Stuart Parker as their manager.',
                'The Conservative Party U.K. is the leader of Blackpool.']
        elif sentences == [
            'A.S. Gubbio 1910 (Italy) play in Serie D. S.S. Robur Siena are champions of that serie.',
            'Pietro Grasso leads Italy.',
            'Italian is the language spoken in Italy.']:
            sentences = ['A.S. Gubbio 1910 (Italy) play in Serie D. S.S.',
                         'Robur Siena are champions of that serie.',
                         'Pietro Grasso leads Italy.',
                         'Italian is the language spoken in Italy.']
        elif sentences == ['St. Vincent-St.',
                           'Mary High School, which is in Akron, Ohio, in the United States, is the ground of Akron Summit Assault.',
                           'They play in the Premier Development League, where the champions have been K-W United FC.']:
            sentences = [
                'St. Vincent-St. Mary High School, which is in Akron, Ohio, in the United States, is the ground of Akron Summit Assault.',
                'They play in the Premier Development League, where the champions have been K-W United FC.']
        elif sentences == [
            'K-W United FC have been champions of the Premier Development League, which Akron Summit Assault play in.',
            'their ground is St. Vincent-St.',
            'Mary High School in Akron, Ohio, in the U.S.']:
            sentences = [
                'K-W United FC have been champions of the Premier Development League, which Akron Summit Assault play in.',
                'their ground is St. Vincent-St. Mary High School in Akron, Ohio, in the U.S.']
        elif sentences == ['St. Vincent–St.',
                           'Mary High School is located in the city of Akron, Ohio, USA.',
                           'The school is the ground of Akron Summit Assault.',
                           'The city is part of Summit County, Ohio.',
                           'It is led by Dan Horrigan.']:
            sentences = [
                'St. Vincent–St. Mary High School is located in the city of Akron, Ohio, USA.',
                'The school is the ground of Akron Summit Assault.',
                'The city is part of Summit County, Ohio.',
                'It is led by Dan Horrigan.']
        elif sentences == ['St. Vincent-St.',
                           'Mary High School is located in Akron, Summit County, Ohio @ USA.',
                           'St Vincent-St Mary High School is the ground of Akron Summit Assault.',
                           'The leader of Akron, Ohio is a one Dan Horrigan.']:
            sentences = [
                'St. Vincent-St. Mary High School is located in Akron, Summit County, Ohio @ USA.',
                'St Vincent-St Mary High School is the ground of Akron Summit Assault.',
                'The leader of Akron, Ohio is a one Dan Horrigan.']
        elif sentences == ["Akron Summit Assault's ground is St. Vincent-St.",
                           'Mary High School.',
                           'Which is in the United States in Summit County, in Akron, Ohio where Dan Horrigan is the leader.']:
            sentences = [
                "Akron Summit Assault's ground is St. Vincent-St. Mary High School, Which is in the United States in Summit County, in Akron, Ohio where Dan Horrigan is the leader."]
        elif sentences == ['St. Vincent St.',
                           'Mary High School is located in Summit County, Ohio, Akron, Ohio, United States.',
                           'Its leader is Dan Horrigan and it is the ground of Akron Summit Assault.']:
            sentences = [
                'St. Vincent St. Mary High School is located in Summit County, Ohio, Akron, Ohio, United States.',
                'Its leader is Dan Horrigan and it is the ground of Akron Summit Assault.']
        elif sentences == [
            'K-W United FC have been champions of the Premier Development League, which is the league Akron Summit Assault play in.',
            "Akron Summit Assault's ground is St. Vincent-St.",
            'Mary High School, in Akron, Ohio, in the United States.']:
            sentences = [
                'K-W United FC have been champions of the Premier Development League, which is the league Akron Summit Assault play in.',
                "Akron Summit Assault's ground is St. Vincent-St. Mary High School, in Akron, Ohio, in the United States."]
        elif sentences == ["Akron Summit Assault's ground is St. Vincent-St.",
                           'Mary High School, Akron, Ohio, United States.',
                           'The team play in the Premier Development League, which has previously been won by K-W United FC.']:
            sentences = [
                "Akron Summit Assault's ground is St. Vincent-St. Mary High School, Akron, Ohio, United States.",
                'The team play in the Premier Development League, which has previously been won by K-W United FC.']
        elif sentences == ['St. Vincent-St.',
                           'Mary High School is in Akron, Ohio @ U.S and is the home ground for Akron Summit Assault.',
                           'Dan Horrigan is the leader of Akron, Ohio.']:
            sentences = [
                'St. Vincent-St. Mary High School is in Akron, Ohio @ U.S and is the home ground for Akron Summit Assault.',
                'Dan Horrigan is the leader of Akron, Ohio.']
        elif sentences == [
            "The Akron Summit Assault's ground is St. Vincent-St.",
            'Mary High School.',
            'The School is located in Akron, Ohio, United States which currently has Dan Horrigan as a leader.']:
            sentences = [
                "The Akron Summit Assault's ground is St. Vincent-St. Mary High School.', 'The School is located in Akron, Ohio, United States which currently has Dan Horrigan as a leader."]
        elif sentences == ['St. Vincent St.',
                           'Mary High School is located in Summit County, Ohio in the United States.',
                           'The Akron Summit Assault ground is at this high school.']:
            sentences = [
                'St. Vincent St. Mary High School is located in Summit County, Ohio in the United States.',
                'The Akron Summit Assault ground is at this high school.']
        elif sentences == [
            'The Olympic Stadium (in Athens) is the home ground of AEK Athens FC.',
            'That football team is managed by Gus Poyet who played for Chelsea F.C. Gus Poyet is also associated with the Real Zaragoza football club.']:
            sentences = [
                'The Olympic Stadium (in Athens) is the home ground of AEK Athens FC.',
                'That football team is managed by Gus Poyet who played for Chelsea F.C.',
                'Gus Poyet is also associated with the Real Zaragoza football club.']
        elif sentences == [
            'The Acharya Institute of Technology is located in the city of Bangalore in India and was established in 2000.',
            "The Institute's President is B.M. Reddy and the Director is Dr.",
            'G.P.Prabhukumar.']:
            sentences = [
                'The Acharya Institute of Technology is located in the city of Bangalore in India and was established in 2000.',
                "The Institute's President is B.M. Reddy and the Director is Dr. G.P.Prabhukumar."]
        elif sentences == [
            'Bangalore was founded by Kempe Gowda I. Located in the city is the Acharya Institute of Technology, an affiliate of Visvesvaraya Technological University.',
            'The institute offers tennis, as governed by the International Tennis Federation, as a sport.']:
            sentences = ['Bangalore was founded by Kempe Gowda I.',
                         'Located in the city is the Acharya Institute of Technology, an affiliate of Visvesvaraya Technological University.',
                         'The institute offers tennis, as governed by the International Tennis Federation, as a sport.']
        elif sentences == ['Acta Palaeontologica Polonica (abbr.',
                           'Acta Palaeontol.',
                           'Pol) is published by the Institute of Paleobiology, Polish Academy of Sciences.',
                           'Code information: ISSN number 0567-7920, LCCN number of 60040714, CODEN code APGPAC.']:
            sentences = [
                'Acta Palaeontologica Polonica (abbr. Acta Palaeontol Pol) is published by the Institute of Paleobiology, Polish Academy of Sciences.',
                'Code information: ISSN number 0567-7920, LCCN number of 60040714, CODEN code APGPAC.']
        elif sentences == [
            'English is spoken in Great Britain and Alcatraz Versus the Evil Librarians was written in it but comes from the U.S. Native Americans are one of the ethnic groups of the United States and the capital city is Washington D.C.']:
            sentences = [
                'English is spoken in Great Britain and Alcatraz Versus the Evil Librarians was written in it but comes from the U.S.',
                'Native Americans are one of the ethnic groups of the United States and the capital city is Washington D.C.']
        elif sentences == [
            'A Loyal Character Dancer is published by Soho Press in the U.S. The language spoken there is English, which was originated in Great Britain.',
            'One ethnic group of the U.S. is African American.']:
            sentences = [
                'A Loyal Character Dancer is published by Soho Press in the U.S.',
                'The language spoken there is English, which was originated in Great Britain.',
                'One ethnic group of the U.S. is African American.']
        elif sentences == [
            '1634 The Ram Rebellion (preceded by 1634: The Galileo Affair) comes from the United States, where Barack Obama is the President, and its capital city is Washington D.C. Native Americans are one of the ethnic groups of the United States.']:
            sentences = [
                '1634 The Ram Rebellion (preceded by 1634: The Galileo Affair) comes from the United States, where Barack Obama is the President, and its capital city is Washington D.C.',
                'Native Americans are one of the ethnic groups of the United States.']
        return sentences

    def triples_fix(self, triplets):
        if not isinstance(triplets, list):
            return [triplets]
        else:
            return map(lambda t: t, triplets)

    def triplets_from_object(self, obj, t_name):
        if not isinstance(obj, list):
            if obj is not None:
                if t_name in obj:
                    return self.triples_fix(obj[t_name])
            return []
        else:
            return [self.triples_fix(o[t_name]) for o in obj]


class WebNLGDataReader(DataReader):
    DATASET = "DelexWebNLG"

    def __init__(self, set: DataSetType):
        self.data_set_type = set.value
        files = self.recurse_files(
            path.join(path.dirname(path.realpath(__file__)), "raw", set.value))
        data = list(
            chain.from_iterable([RDFFileReader(f).data for f in files]))

        super().__init__(data, misspelling=misspelling,
                         rephrase=(rephrase, rephrase_if_must))

    def recurse_files(self, folder):
        if isdir(folder):
            return chain.from_iterable(
                [self.recurse_files(folder + '/' + f) for f in listdir(folder)
                 if not f.startswith('.')])
        return [folder]

    def save(self):
        show_var(["len(self.data)"])
        writeout = json.dumps(self.data, indent=4)
        data_set_type = 'valid' if self.data_set_type == 'dev' else self.data_set_type
        save_f = path.join(path.dirname(path.realpath(__file__)),
                           data_set_type + '.json')
        fwrite(writeout, save_f)


def download():
    cmd = 'git clone https://github.com/ThiagoCF05/webnlg.git data_webnlg\n' \
          'cp -a data_webnlg/data/v1.5/en/ data/webnlg/raw\n' \
          'rm -rf data_webnlg\n'
    print('[Info] Downloading enriched WebNLG data...')
    shell(cmd)


def main():
    # download()
    for typ in DataSetType:
        data_reader = WebNLGDataReader(typ)
        data_reader.save()


if __name__ == "__main__":
    main()

    # show_var(["DelexWebNLGDataReader(DataSetType.TRAIN).data[100]"])
    # len(DelexWebNLGDataReader(DataSetType.TRAIN).data)
    # len(DelexWebNLGDataReader(DataSetType.DEV).data)
    # len(DelexWebNLGDataReader(DataSetType.TEST).data)
