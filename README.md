This is an easy-to-use Python reader for the [enriched WebNLG](https://github.com/ThiagoCF05/webnlg) data.

### How to run
```bash
python data/webnlg/reader.py
```
The resulted file structure is like this (partially):
```bash
.
├── data
│   └── webnlg
│       ├── reader.py
│       ├── test.json
│       ├── train.json
│       ├── utils.py
│       └── valid.json
└── README.md
```

### Contributions
1. Made the reader for WebNLG dataset v1.5, runnable by 2019-SEP-02. (Debugged and adapted the reader in repo [chimera](https://github.com/AmitMY/chimera).)
1. Made the KG-to-text dataset WebNLG from document-level into sentence-level
1. Manually fixed badly tokenized sentences by [spaCy](https://spacy.io/)
1. Deleted irrelevant triples manually
1. Manually fixed all wrong templates (e.g. `template.replace('AEGNT-1', 'AGENT-1')`), made it convenient for template-based models.
1. Carefully replaces `-` with `_` in types, such as `AGENT-1` to `AGENT_1`. This provides convenience for tokenization.

### Overview of dataset
- Dataset sizes: train 24526, valid 3019, test 6622
- Vocab of entities: 3227
- Vocab of ner: 12 (`['agent_1', 'bridge_1', 'bridge_2', 'bridge_3', 'bridge_4', 'patient_1', 'patient_2', 'patient_3', 'patient_4', 'patient_5', 'patient_6', 'patient_7']`)
- Vocab of relations: 726
- Vocab of txt: 6671
- Vocab of tgt: 1897


### Todo
- There are dirty, unaligned (stripleset, template) pairs. Align them by tracking the `self.cnt_dirty_data` variable when running `reader.py`.



