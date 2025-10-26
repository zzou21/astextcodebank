'''This file builds testing data for soft ner identification.

Underneath the main function block ("if __name__ == "__main__":"), find:

1. "txtStoryPathList" (list of strings): put in the TXT file paths of short stories that you want to use as testing data.
2. "jsonTestDataStoragePath" (string): put in the file path of the JSON where you will store the testing data.

For ""jsonTestDataStoragePath", you can create a blank JSON file in your IDE (either VSCode or PyCharm) by creating a new file and end it with ".json", and then you can copy and paste the file path (not the file name) of the blank JSON file this variable.
'''

import json, nltk

def buildTestData(txtStoryPathList, jsonTestingDataOutputPath):

    allSentences = []

    #Iterating through the list of TXT story content
    for txtStoryPath in txtStoryPathList:
        with open(txtStoryPath, "r") as storyContent:
            storyString = storyContent.read()

        storyString = storyString.replace("\n", " ")
        
        sentTokenized = nltk.sent_tokenize(storyString)
        allSentences = allSentences + sentTokenized

    # Turning into a dictionary for JSON dump.
    trainingDict = {i: sentence for i, sentence in enumerate(allSentences)}

    with open(jsonTestingDataOutputPath, "w") as trainingStorage:
        json.dump(trainingDict, trainingStorage, indent=4)
    
    print(f"Finished creating testing data at {jsonTestingDataOutputPath}")

if __name__ == "__main__":

    # A list of txts that each contain one short story that will be used as testing data. Make sure that these stories are not being used in training.
    txtStoryPathList = ["/Users/Jerry/Desktop/AsteXT/AsteXTCode/AsteXTCode2025-6/Data/TestingData/thevirtuesofbeingmary_hà_2011.txt", "/Users/Jerry/Desktop/AsteXT/AsteXTCode/AsteXTCode2025-6/Data/ahabitalpose_xie_2018 copy.txt"]

    # the JSON file path of where you want to store the testing data.
    jsonTestDataStoragePath = "testData1.json"

    buildTestData(txtStoryPathList, jsonTestDataStoragePath)