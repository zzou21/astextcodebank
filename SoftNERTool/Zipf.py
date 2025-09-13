import nltk, re
import matplotlib.pyplot as plt

class wordFrequency:
    def __init__(self):
        self.wordCountDictionary = None

    def loadFile(self, storyTXTFilePath):
        with open(storyTXTFilePath, "r", encoding="utf-8") as storyTXT:
            return storyTXT.read()
    
    def wordProcessing(self, storyTXTFilePath):
        contentStr = self.loadFile(storyTXTFilePath)
        contentStrSegmented = nltk.tokenize.word_tokenize(contentStr)
        contentStrSegmented = [re.sub(r'[^\w\s]', '', token) for token in contentStrSegmented if re.sub(r'[^\w\s]', '', token)]
        contentStrSegmented = [word.lower() for word in contentStrSegmented]

        wordCountDictionary = {}
        for word in contentStrSegmented:
            if word not in wordCountDictionary:
                wordCountDictionary[word] = 0
            wordCountDictionary[word] += 1

        wordCountSortList = sorted(wordCountDictionary.items(), key=lambda x: x[1], reverse=True)

        return wordCountSortList

    def visualization(self, storyFilePath):
        sortedDataList = self.wordProcessing(storyFilePath)

        top10Words = sortedDataList[:10]
        bottom10Words = sortedDataList[-10:]

        selected = top10Words + bottom10Words
        words, counts = zip(*selected)

        plt.figure(figsize=(14, 6))
        plt.bar(words, counts)
        plt.xticks(rotation=45, ha="right")
        plt.xlabel("Words")
        plt.ylabel("Frequency")
        plt.title("Top 10 and Bottom 10 Word Frequencies")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    storyFilePath = "/Users/Jerry/Desktop/AsteXT/AsteXTCode/AsteXTCode2025-6/Data/station4_greenfeld_2018 copy.txt"
    output = wordFrequency()
    output.visualization(storyFilePath)