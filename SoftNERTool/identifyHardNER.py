'''This file identifies hard NER for words in a story to prepare for training.

1. "jsonLabeledTokenizedPath" (list of strings): a list of JSON file paths referring to the soft NER JSON that the soft NER tagging tool provided.
2. "hardNERJsonStorage" (string): file path of one JSON file where you will store the labeled hard NER.
'''

import json, spacy

class labelHardNER:
    def __init__(self, sentenceTokenizedJson):

        #This file is the output json of the softNERTagging tool. The output JSON contains tokenized sentences plus labeled soft NER. This python class object only needs the tokenized sentences.
        self.sentenceTokenized = sentenceTokenizedJson


    def loadSentenceTokenized(self):
        with open(self.sentenceTokenized, "r") as storyFile:
            storyContent = json.load(storyFile)
        return storyContent["sentences"]
    
    def labelHardNER(self):
        sentTokenizedStory = self.loadSentenceTokenized()

        storageDict = {} # dictionary that stores the hard NER labels
        NERLabeler = spacy.load('en_core_web_sm')
        
        NERLabelCounter = 0

        for sentence in sentTokenizedStory:
            sent = NERLabeler(sentence)
            entityInfo = [] # Each sentence might have multiple named entities
            for ent in sent.ents:
                if ent.label_ in ["FAC", "GPE", "LOC"]: # we only need hard NER that are related to space
                    entityInfo.append({
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "text": ent.text,
                        "label": "Hard " + ent.label_,
                        "sentence": sentence
                    })
            if entityInfo != []:
                storageDict[str(NERLabelCounter)] = entityInfo
                NERLabelCounter += 1
        
        return storageDict, sentTokenizedStory
    
    def exportHardNERLabel(self, jsonPath):
        returnDict = {}
        HardNERStorageDict, allSentencesList = self.labelHardNER()
        returnDict["sentences"] = allSentencesList
        returnDict["annotations"] = HardNERStorageDict
        with open(jsonPath, "w") as destination:
            json.dump(returnDict, destination, indent=4)


if __name__ == "__main__":

    # List of JSON paths that contains the tagged soft NER created by the soft NER tagging tool that I provided.
    jsonLabeledTokenizedPath = "/Users/Jerry/Desktop/AsteXT/AsteXTCode/AsteXTCode2025-6/Data/annotationsStation4.json"

    # JSON file path to store hard NER storage
    hardNERJsonStorage = "hardNER.json"
    
    hardNERLabeler = labelHardNER(jsonLabeledTokenizedPath)
    hardNERLabeler.exportHardNERLabel(hardNERJsonStorage)