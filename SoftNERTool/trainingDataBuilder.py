'''This file builds testing data for soft ner identification.

Underneath the main function block ("if __name__ == "__main__":"), find:

1. "combiner" (Python object): The object that combines multiple Hard NER and Soft NER files together.
    Parameters:
        "hardNerPaths" (list of strings): add a list of file paths to hard NER JSON
        "softNerPaths" (list of strings): add a list fo fiel paths to soft NER JSON that was outputted from the soft NER tagging tool that I provided before.

2. "combinedTrainingDataJsonPath" (string): put in the file path of the JSON where you will store the combined training data.

For ""combinedTrainingDataJsonPath", you can create a blank JSON file in your IDE (either VSCode or PyCharm) by creating a new file and end it with ".json", and then you can copy and paste the file path (not the file name) of the blank JSON file this variable.

Negative: hard NER
Negative: general words
Positive: soft NER

'''
import json
from dataclasses import dataclass, asdict


@dataclass
class TokenAnnotation:
    """Represents annotation for a single token."""
    token: str
    label: str  # "O" for general words, "Hard-GPE", "Soft-Institutional", etc.
    startChar: int
    endChar: int
    sentenceId: int


@dataclass
class CombinedAnnotation:
    """Represents combined annotations for a sentence."""
    sentenceId: int
    sentence: str
    tokens: list
    labels: list
    charSpans: list


class NerDatasetCombiner:
    """Combines hard NER and soft NER annotations into a unified dataset."""
    
    def __init__(self, hardNerPaths, softNerPaths):
        """
        Initialize the combiner with lists of paths to hard and soft NER JSON files.
        
        Args:
            hardNerPaths: List of paths to hard NER JSON files or a single path string
            softNerPaths: List of paths to soft NER JSON files or a single path string
        """
        # Allow single string or list for backwards compatibility
        if isinstance(hardNerPaths, str):
            hardNerPaths = [hardNerPaths]
        if isinstance(softNerPaths, str):
            softNerPaths = [softNerPaths]
        
        self.hardNerData = []
        self.softNerData = []
        
        # Load all hard NER files
        for path in hardNerPaths:
            with open(path, 'r', encoding='utf-8') as f:
                self.hardNerData.append(json.load(f))
        
        # Load all soft NER files
        for path in softNerPaths:
            with open(path, 'r', encoding='utf-8') as f:
                self.softNerData.append(json.load(f))
        
        # Use sentences from the first hard NER file as the base
        # (assuming all files annotate the same sentences)
        self.sentences = self.hardNerData[0]['sentences']
        
    def _tokenizeSentence(self, sentence):
        """Simple tokenization that splits on whitespace and tracks character positions."""
        tokens = []
        start = 0
        
        for i, char in enumerate(sentence):
            if char.isspace():
                if start < i:
                    tokens.append((sentence[start:i], start, i))
                start = i + 1
        
        if start < len(sentence):
            tokens.append((sentence[start:], start, len(sentence)))
        
        return tokens
    
    def _getLabelForSpan(self, sentenceId, charStart, charEnd):
        """Get the label for a character span, checking all hard and soft NER files."""
        sentenceIdStr = str(sentenceId)
        
        # Check all hard NER files
        for idx, hardNer in enumerate(self.hardNerData):
            if sentenceIdStr in hardNer['annotations']:
                for annotation in hardNer['annotations'][sentenceIdStr]:
                    annStart = annotation['start']
                    annEnd = annotation['end']
                    
                    if charStart < annEnd and charEnd > annStart:
                        # Include file index if multiple hard NER files
                        prefix = f"Hard{idx+1}" if len(self.hardNerData) > 1 else "Hard"
                        return f"{prefix}-{annotation['label']}"
        
        # Check all soft NER files
        for idx, softNer in enumerate(self.softNerData):
            if sentenceIdStr in softNer['annotations']:
                for annotation in softNer['annotations'][sentenceIdStr]:
                    annStart = annotation['start']
                    annEnd = annotation['end']
                    
                    if charStart < annEnd and charEnd > annStart:
                        # Include file index if multiple soft NER files
                        prefix = f"Soft{idx+1}" if len(self.softNerData) > 1 else "Soft"
                        return f"{prefix}-{annotation['label']}"
        
        return "O"
    
    def combineAnnotations(self):
        """Combine hard and soft NER annotations for all sentences."""
        combinedData = []
        
        for sentId, sentence in enumerate(self.sentences):
            tokensData = self._tokenizeSentence(sentence)
            
            tokens = []
            labels = []
            charSpans = []
            
            for token, startChar, endChar in tokensData:
                label = self._getLabelForSpan(sentId, startChar, endChar)
                
                tokens.append(token)
                labels.append(label)
                charSpans.append((startChar, endChar))
            
            combinedAnnotation = CombinedAnnotation(
                sentenceId=sentId,
                sentence=sentence,
                tokens=tokens,
                labels=labels,
                charSpans=charSpans
            )
            
            combinedData.append(combinedAnnotation)
        
        return combinedData
    
    def toBioFormat(self):
        """Convert annotations to BIO tagging format."""
        combined = self.combineAnnotations()
        bioData = []
        
        for annotation in combined:
            tokensBio = []
            prevLabel = "O"
            
            for token, label in zip(annotation.tokens, annotation.labels):
                if label == "O":
                    bioLabel = "O"
                elif label != prevLabel:
                    bioLabel = f"B-{label}"
                else:
                    bioLabel = f"I-{label}"
                
                tokensBio.append({
                    "token": token,
                    "label": bioLabel
                })
                prevLabel = label
            
            bioData.append({
                "sentenceId": annotation.sentenceId,
                "sentence": annotation.sentence,
                "tokens": tokensBio
            })
        
        return bioData
    
    def toDict(self):
        """Convert combined annotations to dictionary format."""
        combined = self.combineAnnotations()
        
        # Collect all labels from all files
        allHardLabels = []
        for hardNer in self.hardNerData:
            allHardLabels.extend(hardNer.get('labels', []))
        
        allSoftLabels = []
        for softNer in self.softNerData:
            allSoftLabels.extend(softNer.get('labels', []))
        
        return {
            "sentences": [asdict(ann) for ann in combined],
            "labelTypes": ["O", "Hard NER", "Soft NER"],
            "hardLabels": list(set(allHardLabels)),
            "softLabels": list(set(allSoftLabels)),
            "numHardNerFiles": len(self.hardNerData),
            "numSoftNerFiles": len(self.softNerData)
        }
    
    def saveCombined(self, outputPath, format="standard"):
        """Save combined annotations to a JSON file."""
        if format == "bio":
            data = self.toBioFormat()
        else:
            data = self.toDict()
        
        with open(outputPath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def getStatistics(self):
        """Get statistics about the combined dataset."""
        combined = self.combineAnnotations()
        
        totalTokens = 0
        labelCounts = {}
        
        for annotation in combined:
            totalTokens += len(annotation.tokens)
            for label in annotation.labels:
                labelCounts[label] = labelCounts.get(label, 0) + 1
        
        return {
            "totalSentences": len(combined),
            "totalTokens": totalTokens,
            "labelDistribution": labelCounts,
            "avgTokensPerSentence": totalTokens / len(combined) if combined else 0,
            "numHardNerFiles": len(self.hardNerData),
            "numSoftNerFiles": len(self.softNerData)
        }


if __name__ == "__main__":
    
    # Example with multiple files
    combiner = NerDatasetCombiner(
        hardNerPaths=[
            "/path/to/hardNER1.json",
            "/path/to/hardNER2.json",
            "/path/to/hardNER3.json"
        ],
        softNerPaths=[
            "/path/to/softNER1.json",
            "/path/to/softNER2.json"
        ]
    )
    
    combinedData = combiner.combineAnnotations()
    
    print("Example - First Sentence:")
    print(f"Sentence: {combinedData[0].sentence[:100]}...")
    print(f"\nTokens and Labels:")
    for token, label in zip(combinedData[0].tokens[:10], combinedData[0].labels[:10]):
        print(f"  {token:20} -> {label}")
    
    # File path of where you want to store the combined JSON file
    combinedTrainingDataJsonPath = "trainingCombinedNER.json"
    
    # Function call to output combined JSON
    combiner.saveCombined(combinedTrainingDataJsonPath, format="standard")
    print(f"Saved combined NER training data JSON: {combinedTrainingDataJsonPath}")
    

    # Uncomment this block of you want to use BIO format. We will not be using BIO format, so do not uncomment this block. I left this here in case you want to play around with it:
    # combiner.saveCombined("trainingCombinedNERBioFormat.json", format="bio")
    # print("Saved: trainingCombinedNERBioFormat.json")
    

    # Get statistics that will be printed in your consol
    stats = combiner.getStatistics()
    print("\nDataset Statistics:")
    print(f"  Hard NER files: {stats['numHardNerFiles']}")
    print(f"  Soft NER files: {stats['numSoftNerFiles']}")
    print(f"  Total sentences: {stats['totalSentences']}")
    print(f"  Total tokens: {stats['totalTokens']}")
    print(f"  Avg tokens/sentence: {stats['avgTokensPerSentence']:.2f}")
    print(f"\nLabel Distribution:")
    for label, count in sorted(stats['labelDistribution'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['totalTokens']) * 100
        print(f"  {label:30} {count:6} ({percentage:5.2f}%)")