# Code Bank for AsteXT

This repository contains programs used in Natural Language Proccessing or related tasks for the AsteXT research team. Any other researchers, students, or learners are welcome to use any code or program in this toolkit for their research.

The files in this repository is a complete pipeline that teaches you how to fine-tune your domain-specific Named Entity Recognition language model, starting from data annotation and NER schema design. You will also learn machine learning techniques like hyperparameter tuning, data resampling, data annotation, model validation, F-1 scores, and others.

Directory structure:
- SoftNERTool: this folder contains tools used to identify soft NERs
  - softNERTagging.py: this file contains an interface coded in Python using the NLTK and Qt libraries for researchers to manually tag soft NER in stories.
    - Usage: After downloading the file, make sure you have both the NLTK and Qt libraries installed (you can do so by running the command `pip install nltk` and `pip install PyQt5` in your terminal). After running the program, you should be directed to select a TXT file from your local machine. You can only upload a TXT file. After making all annotations, you can export your annotation as a JSON file to a directory on your local machine of your preference.
  - identifyHardNER.py: this file contains the program that uses spaCy to identify traditional, "hard," NERs from the corpus that we are studying.
  - trainingDataBuilder.py: this file contains the program that builds the training dataset for our machine learning model.
  - testingDataBuilder.py: this file contains the program that builds the testing dataset for our machien learning model.

- machienFineTuneTutorial.ipynb: this Notebook contains a detailed and step-by-step tutorial for training your own domain-specific NER classification language model.