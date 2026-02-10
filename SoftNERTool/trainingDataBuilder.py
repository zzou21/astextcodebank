'''This file builds testing data for soft ner identification.

Within the main function block ("if __name__ == "__main__":"), find and update:

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
        
        #Load all soft NER files
        for path in softNerPaths:
            with open(path, 'r', encoding='utf-8') as f:
                self.softNerData.append(json.load(f))
        
        # Use sentences from the first hard NER file as the base (assuming all files annotate the same sentences)
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
                        return f"Hard-{annotation['label']}"
        
        # Check all soft NER files
        for idx, softNer in enumerate(self.softNerData):
            if sentenceIdStr in softNer['annotations']:
                for annotation in softNer['annotations'][sentenceIdStr]:
                    annStart = annotation['start']
                    annEnd = annotation['end']
                    
                    if charStart < annEnd and charEnd > annStart:
                        return f"Soft-{annotation['label']}"
        
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
            
            # Create annotation
            combinedAnnotation = CombinedAnnotation(
                sentenceId=sentId,
                sentence=sentence,
                tokens=tokens,
                labels=labels,
                charSpans=charSpans
            )
            
            combinedData.append(combinedAnnotation)
        
        return combinedData
    
    # Only use this if the function call in the Main function block chooses to use BIO format
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
    """Build training data per story, then merge all stories into one JSON.

    We keep the original flat list input style:
      - hardNerPaths = [story1_hard.json, story2_hard.json, ...]
      - softNerPaths = [story1_soft.json, story2_soft.json, ...]

    We assume that hardNerPaths[i] and softNerPaths[i] belong to the
    same story. Each pair is combined independently to avoid
    cross-story label contamination, then all sentences are concatenated.
    """

    # IMPORTANT: update these two lists. Make sure that
    #   - hardNerPaths[i] corresponds to softNerPaths[i]
    #   - Each pair (hard, soft) comes from the same book.
    hardNerPaths = [
        "/Users/damao/Documents/AsteXT/workdir/ifyoucutmemymotherbleeds_su_2023/ifyoucutmemymotherbleeds_su_2023HardNER.json",
        "/Users/damao/Documents/AsteXT/workdir/tension_khalifeh_1984/tension_khalifeh_1984HardNER.json",
        "/Users/damao/Documents/AsteXT/workdir/lipstick_kuo_2000/lipstick_kuo_2000HardNER.json",
        "/Users/damao/Documents/AsteXT/workdir/mallikareflectsontheeventsofdiscountmonday_zaidi_2019/mallikareflectsontheeventsofdiscountmonday_zaidi_2019HardNER.json",
    ]

    softNerPaths = [
        "/Users/damao/Documents/AsteXT/workdir/ifyoucutmemymotherbleeds_su_2023/annotations.json",
        "/Users/damao/Documents/AsteXT/workdir/tension_khalifeh_1984/annotations.json",
        "/Users/damao/Documents/AsteXT/workdir/lipstick_kuo_2000/annotations.json",
        "/Users/damao/Documents/AsteXT/workdir/mallikareflectsontheeventsofdiscountmonday_zaidi_2019/annotations.json",
    ]

    if len(hardNerPaths) != len(softNerPaths):
        raise ValueError("The lengths of hardNerPaths and softNerPaths must be the same, and they should correspond one-to-one to the same book.")

    all_sentences = []
    all_hard_labels = set()
    all_soft_labels = set()
    total_hard_files = 0
    total_soft_files = 0

    print("Building per-story training data and merging...")

    for idx, (hard_path, soft_path) in enumerate(zip(hardNerPaths, softNerPaths), start=1):
        print(f"\n[{idx}/{len(hardNerPaths)}] Processing pair:\n  hard: {hard_path}\n  soft: {soft_path}")

        combiner = NerDatasetCombiner(
            hardNerPaths=[hard_path],
            softNerPaths=[soft_path],
        )

        story_dict = combiner.toDict()

        # If you need independent training JSON for each book (standard format), uncomment below:
        # import os
        # story_name = os.path.splitext(os.path.basename(hard_path))[0]
        # per_story_path = f"training_{story_name}.json"
        # with open(per_story_path, "w", encoding="utf-8") as f:
        #     json.dump(story_dict, f, indent=2, ensure_ascii=False)
        # print(f"  Saved per-story training data: {per_story_path}")

        # If you also want a BIO-format training file for this book,
        # you can call saveCombined with format="bio":
        # bio_story_path = f"training_{story_name}_bio.json"
        # combiner.saveCombined(bio_story_path, format="bio")
        # print(f"  Saved per-story BIO-format training data: {bio_story_path}")

        # To inspect per-book statistics:
        # stats = combiner.getStatistics()
        # print("  Per-book statistics:")
        # print(f"    Total sentences: {stats['totalSentences']}")
        # print(f"    Total tokens: {stats['totalTokens']}")

        # Accumulate into the overall merged output
        all_sentences.extend(story_dict.get("sentences", []))
        all_hard_labels.update(story_dict.get("hardLabels", []))
        all_soft_labels.update(story_dict.get("softLabels", []))
        total_hard_files += story_dict.get("numHardNerFiles", 0)
        total_soft_files += story_dict.get("numSoftNerFiles", 0)

    merged_dict = {
        "sentences": all_sentences,
        "labelTypes": ["O", "Hard NER", "Soft NER"],
        "hardLabels": sorted(all_hard_labels),
        "softLabels": sorted(all_soft_labels),
        "numHardNerFiles": total_hard_files,
        "numSoftNerFiles": total_soft_files,
    }

    # Name of the final merged training JSON
    combinedTrainingDataJsonPath = "training_2026Jan_all.json"

    with open(combinedTrainingDataJsonPath, "w", encoding="utf-8") as f:
        json.dump(merged_dict, f, indent=2, ensure_ascii=False)

    print(f"\nSaved merged NER training data JSON: {combinedTrainingDataJsonPath}")

    # Simple overall statistics for the merged dataset
    total_sentences = len(all_sentences)
    total_tokens = sum(len(s.get("tokens", [])) for s in all_sentences)
    label_counts = {}
    for s in all_sentences:
        for lbl in s.get("labels", []):
            label_counts[lbl] = label_counts.get(lbl, 0) + 1

    avg_tokens_per_sentence = total_tokens / total_sentences if total_sentences else 0

    print("\nMerged Dataset Statistics:")
    print(f"  Stories: {len(hardNerPaths)}")
    print(f"  Hard NER files: {total_hard_files}")
    print(f"  Soft NER files: {total_soft_files}")
    print(f"  Total sentences: {total_sentences}")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg tokens/sentence: {avg_tokens_per_sentence:.2f}")
    print(f"\nLabel Distribution (token-level):")
    for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_tokens) * 100 if total_tokens else 0
        print(f"  {label:30} {count:6} ({percentage:5.2f}%)")