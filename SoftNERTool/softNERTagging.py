"""
This file contails the interface to manually tag soft NERs in a story. Please make sure that you have both NLTK and PyQt5 installed. You can do so through using "pip". You can only upload a TXT file to this program. Make sure that you have stored the story you want to tag as a plain TXT file.

After you've tagged the soft NERs, the system will export a JSON file. Please make sure to keep your JSON files organized so that we can easily refer to them.
"""

import sys, nltk, json, re
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QTextEdit, QMessageBox, QProgressBar, QFrame, QScrollArea, QFileDialog, QDialog, QListWidget, QLineEdit, QDialogButtonBox, QInputDialog, QSplitter, QTreeWidget, QTreeWidgetItem, QTabWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

class LabelSelectionDialog(QDialog):
    def __init__(self, labels, selected_text, parent=None):
        super().__init__(parent)
        self.selected_label = None
        self.labels = labels
        
        self.setWindowTitle("Select Entity Label")
        self.setModal(True)
        self.setFixedSize(300, 400)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"Select label for: '{selected_text}'")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setWordWrap(True)
        layout.addWidget(header)
        
        # Label list
        self.label_list = QListWidget()
        for label in labels:
            self.label_list.addItem(label)
        
        # Select first item by default
        if labels:
            self.label_list.setCurrentRow(0)
        
        layout.addWidget(self.label_list)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def accept(self):
        current_item = self.label_list.currentItem()
        if current_item:
            self.selected_label = current_item.text()
        super().accept()

class EntityLabelManager(QDialog):
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.labels = labels[:]
        
        self.setWindowTitle("Manage Entity Labels")
        self.setModal(True)
        self.setFixedSize(350, 400)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Manage Entity Labels")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(header)
        
        # Label list
        self.label_list = QListWidget()
        self.update_label_list()
        layout.addWidget(self.label_list)
        
        # Buttons for managing labels
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Label")
        add_btn.clicked.connect(self.add_label)
        button_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Label")
        remove_btn.clicked.connect(self.remove_label)
        button_layout.addWidget(remove_btn)
        
        layout.addLayout(button_layout)
        
        # buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def update_label_list(self):
        self.label_list.clear()
        for label in self.labels:
            self.label_list.addItem(label)
    
    def add_label(self):
        text, ok = QInputDialog.getText(self, "Add Label", "Enter new label name:")
        if ok and text.strip():
            label = text.strip()
            if label not in self.labels:
                self.labels.append(label)
                self.update_label_list()
            else:
                QMessageBox.warning(self, "Duplicate Label", f"Label '{label}' already exists.")
    
    def remove_label(self):
        current_item = self.label_list.currentItem()
        if current_item:
            label = current_item.text()
            reply = QMessageBox.question(self, "Remove Label", 
                                       f"Are you sure you want to remove label '{label}'?")
            if reply == QMessageBox.Yes:
                self.labels.remove(label)
                self.update_label_list()

class ClickableTextEdit(QTextEdit):
    def __init__(self, sentence, sentence_index, parent=None):
        super().__init__(parent)
        self.sentence = sentence
        self.sentence_index = sentence_index
        self.parent_window = parent
        self.selected_ranges = []  # Store (start, end, label) tuples
        self.selection_start = None
        self.double_click_started = False
        
        # Setup text display
        self.setPlainText(sentence)
        self.setReadOnly(True)
        self.setMaximumHeight(100)
        self.setMinimumHeight(60)
        
        # Style the text area
        self.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                background-color: #fafafa;
            }
            QTextEdit:hover {
                border-color: #4CAF50;
            }
        """)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to select word under cursor"""
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            # Find word boundaries around the clicked position
            start, end = self.find_word_boundaries(position)
            
            if start < end:  # Valid word found
                selected_text = self.sentence[start:end]
                
                # Check if this selection matches an existing entity exactly
                existing_entity = self.find_exact_entity_match(start, end)
                if existing_entity:
                    # Remove the existing entity
                    self.remove_selection(existing_entity[0], existing_entity[1], existing_entity[2])
                    if self.parent_window:
                        self.parent_window.status_label.setText(f"Removed entity: '{selected_text}' ({existing_entity[2]})")
                elif not self.overlaps_existing_selection(start, end):
                    # ask user to select a label
                    if self.parent_window and self.parent_window.entity_labels:
                        dialog = LabelSelectionDialog(self.parent_window.entity_labels, selected_text, self)
                        if dialog.exec_() == QDialog.Accepted and dialog.selected_label:
                            # Add new entity with label
                            self.add_selection(start, end, selected_text, dialog.selected_label)
                            if self.parent_window:
                                self.parent_window.status_label.setText(f"Added entity: '{selected_text}' ({dialog.selected_label})")
                    else:
                        QMessageBox.warning(self, "No Labels", "Please set up entity labels first using the 'Manage Labels' button.")
                else:
                    QMessageBox.warning(self, "Overlapping Selection", 
                                      "This selection overlaps with an existing entity. To remove an entity, double-click on it exactly.")
        
        # Don't call super() to prevent default double-click behavior
    
    def find_word_boundaries(self, position):
        """Find the start and end positions of the word at the given position"""
        text = self.sentence
        
        # If position is out of bounds, return invalid range
        if position < 0 or position >= len(text):
            return position, position
        
        # Find start of word (move backward)
        start = position
        while start > 0 and self.is_word_char(text[start - 1]):
            start -= 1
        
        # Find end of word (move forward)
        end = position
        while end < len(text) and self.is_word_char(text[end]):
            end += 1
        
        # If we're on a non-word character, try to find the nearest word
        if start == end:
            # Look backward for a word
            temp_pos = position - 1
            while temp_pos >= 0 and not self.is_word_char(text[temp_pos]):
                temp_pos -= 1
            
            if temp_pos >= 0:
                # Found a word character, find its boundaries
                end = temp_pos + 1
                start = temp_pos
                while start > 0 and self.is_word_char(text[start - 1]):
                    start -= 1
            else:
                # Look forward for a word
                temp_pos = position
                while temp_pos < len(text) and not self.is_word_char(text[temp_pos]):
                    temp_pos += 1
                
                if temp_pos < len(text):
                    start = temp_pos
                    end = temp_pos + 1
                    while end < len(text) and self.is_word_char(text[end]):
                        end += 1
        
        return start, end
    
    def is_word_char(self, char):
        """Check if character is part of a word (alphanumeric or common word characters)"""
        return char.isalnum() or char in "'-"
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            self.selection_start = cursor.position()
            
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release for both single-click drag and double-click drag"""
        if event.button() == Qt.LeftButton:
            if self.double_click_started:
                # Handle double-click selection (with or without drag)
                start = self.selection_start
                end = self.selection_end
                self.double_click_started = False
                
                if start is not None and end is not None and end > start:
                    selected_text = self.sentence[start:end]
                    self.process_selection(start, end, selected_text)
                
                # Clear temporary highlighting
                self.highlight_selections()
                
            elif self.selection_start is not None:
                # Handle regular click-and-drag selection
                cursor = self.cursorForPosition(event.pos())
                selection_end = cursor.position()
                
                # Ensure start is before end
                start = min(self.selection_start, selection_end)
                end = max(self.selection_start, selection_end)
                
                # Only proceed if there's actually a selection (and it's not just a click)
                if end > start and abs(end - start) > 1:
                    selected_text = self.sentence[start:end]
                    self.process_selection(start, end, selected_text)
            
            # Reset selection tracking
            self.selection_start = None
            self.selection_end = None
            
        super().mouseReleaseEvent(event)
    
    def process_selection(self, start, end, selected_text):
        """Process a completed selection (either from drag or double-click)"""
        # Check if this selection matches an existing entity exactly
        existing_entity = self.find_exact_entity_match(start, end)
        if existing_entity:
            # Remove the existing entity
            self.remove_selection(existing_entity[0], existing_entity[1], existing_entity[2])
            if self.parent_window:
                self.parent_window.status_label.setText(f"Removed entity: '{selected_text}' ({existing_entity[2]})")
        elif not self.overlaps_existing_selection(start, end):
            # Ask user to select a label
            if self.parent_window and self.parent_window.entity_labels:
                dialog = LabelSelectionDialog(self.parent_window.entity_labels, selected_text, self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_label:
                    # Add new entity with label
                    self.add_selection(start, end, selected_text, dialog.selected_label)
                    if self.parent_window:
                        self.parent_window.status_label.setText(f"Added entity: '{selected_text}' ({dialog.selected_label})")
            else:
                QMessageBox.warning(self, "No Labels", "Please set up entity labels first using the 'Manage Labels' button.")
        else:
            QMessageBox.warning(self, "Overlapping Selection", 
                              "This selection overlaps with an existing entity. To remove an entity, select it exactly.")
    
    def overlaps_existing_selection(self, start, end):
        """Check if the new selection overlaps with any existing selection"""
        for existing_start, existing_end, existing_label in self.selected_ranges:
            if not (end <= existing_start or start >= existing_end):
                return True
        return False
    
    def find_exact_entity_match(self, start, end):
        """Check if the selection exactly matches an existing entity"""
        for existing_start, existing_end, existing_label in self.selected_ranges:
            if start == existing_start and end == existing_end:
                return (existing_start, existing_end, existing_label)
        return None
    
    def add_selection(self, start, end, text, label):
        """Add a new entity selection with label"""
        self.selected_ranges.append((start, end, label))
        self.highlight_selections()
        
        # Update parent window
        if self.parent_window:
            self.parent_window.update_entity_display()
    
    def remove_selection(self, start, end, label):
        """Remove an entity selection"""
        if (start, end, label) in self.selected_ranges:
            self.selected_ranges.remove((start, end, label))
            self.highlight_selections()
            
            if self.parent_window:
                self.parent_window.update_entity_display()
    
    def highlight_selections(self):
        """Highlight all selected entities in the text with different colors per label"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        
        # Clear existing formatting
        format_clear = QTextCharFormat()
        cursor.setCharFormat(format_clear)
        
        # Color mapping for different labels
        label_colors = {
            'PERSON': ("#FFE4B5", "#8B4513"),
            'PLACE': ("#E0FFE0", "#2E8B57"),
            'ORGANIZATION': ("#E0E6FF", "#4169E1"),
            'TIME': ("#FFF0E6", "#FF6347"),
            'EVENT': ("#F0E6FF", "#9370DB"),
        }
        
        # Apply highlighting to each selection
        for start, end, label in self.selected_ranges:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            
            format_highlight = QTextCharFormat()
            
            # Use specific colors for known labels, default for others
            if label in label_colors:
                bg_color, fg_color = label_colors[label]
            else:
                # Generate a hash-based color for unknown labels
                hash_val = hash(label) % 5
                colors = [("#FFE4B5", "#8B4513"), ("#E0FFE0", "#2E8B57"), 
                         ("#E0E6FF", "#4169E1"), ("#FFF0E6", "#FF6347"), ("#F0E6FF", "#9370DB")]
                bg_color, fg_color = colors[hash_val]
            
            format_highlight.setBackground(QColor(bg_color))
            format_highlight.setForeground(QColor(fg_color))
            cursor.setCharFormat(format_highlight)
        
        # Reset cursor position
        cursor.clearSelection()
        self.setTextCursor(cursor)

class NamedEntityAnnotationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sentences = []
        self.currentSentenceIndex = 0
        self.annotations = {}  # Will store {sentence_index: [(start, end, text, label), ...]}
        self.textWidgets = []
        self.entity_labels = ["Private", "Communal/Public", "Extraterrestrial/Figurative", "Natural", "Institutional"]  # Default labels
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Named Entity Annotation Tool")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Header
        header = QLabel("Named Entity Annotation Tool")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("padding: 20px; color: #2E7D32;")
        layout.addWidget(header)
        
        # Instructions
        instructions = QLabel(
            "Instructions: Click and drag to select named entities in the text below. "
            "You'll be prompted to select a label type for each entity. Different labels are highlighted in different colors. "
            "To remove an entity, click and drag over it again exactly. Click 'Save Annotations' when finished."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: #E8F5E8; border-radius: 5px; margin: 10px;")
        layout.addWidget(instructions)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Text File")
        load_btn.clicked.connect(self.load_sentences)
        load_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        control_layout.addWidget(load_btn)
        
        labels_btn = QPushButton("Manage Labels")
        labels_btn.clicked.connect(self.manage_labels)
        labels_btn.setStyleSheet(self.get_button_style("#FF9800"))
        control_layout.addWidget(labels_btn)
        
        save_btn = QPushButton("Save Annotations")
        save_btn.clicked.connect(self.save_annotations)
        save_btn.setStyleSheet(self.get_button_style("#2196F3"))
        control_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear All Annotations")
        clear_btn.clicked.connect(self.clear_all_annotations)
        clear_btn.setStyleSheet(self.get_button_style("#FF5722"))
        control_layout.addWidget(clear_btn)
        
        layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Current labels display
        self.labels_display = QLabel(f"Current Labels: {', '.join(self.entity_labels)}")
        self.labels_display.setStyleSheet("padding: 5px; background-color: #FFF3E0; border-radius: 3px; font-size: 11px;")
        layout.addWidget(self.labels_display)
        
        # Scrollable area for sentences
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Current annotations display
        self.annotations_label = QLabel("Current Annotations: None")
        self.annotations_label.setStyleSheet("padding: 10px; background-color: #F5F5F5; border-radius: 5px;")
        layout.addWidget(self.annotations_label)
        
        # Status bar
        self.status_label = QLabel("Load a text file to begin annotation")
        self.status_label.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(self.status_label)
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
            QPushButton:pressed {{
                background-color: {color}BB;
            }}
        """
    
    def manage_labels(self):
        """Open dialog to manage entity labels"""
        dialog = EntityLabelManager(self.entity_labels, self)
        if dialog.exec_() == QDialog.Accepted:
            self.entity_labels = dialog.labels
            self.labels_display.setText(f"Current Labels: {', '.join(self.entity_labels)}")
    
    def load_sentences(self):
        """Load sentences from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Text File", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sentences = data
                    else:
                        QMessageBox.warning(self, "Invalid Format", "JSON file must contain a list of sentences.")
                        return
            else:
                # This part cleans the stories into sentence segments
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Clean new lines
                    content = re.sub(r"\n", " ", content)
                    # Sentence segmentation
                    segmentedSentences = nltk.sent_tokenize(content)

                    self.sentences = segmentedSentences
                                
            self.setupAnnotationInterface()
            self.status_label.setText(f"Loaded {len(self.sentences)} sentences")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def setupAnnotationInterface(self):
        """Setup the interface with loaded sentences"""
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())): 
            self.scroll_layout.itemAt(i).widget().setParent(None)
        
        self.textWidgets = []
        self.annotations = {}
        
        # Create text widgets for each sentence
        for i, sentence in enumerate(self.sentences):
            # Sentence header
            header = QLabel(f"Sentence {i + 1}:")
            header.setFont(QFont("Arial", 12, QFont.Bold))
            header.setStyleSheet("margin-top: 15px; margin-bottom: 5px; color: #333;")
            self.scroll_layout.addWidget(header)
            
            # Clickable text widget
            text_widget = ClickableTextEdit(sentence, i, self)
            self.textWidgets.append(text_widget)
            self.scroll_layout.addWidget(text_widget)
            
            # Initialize annotations for this sentence
            self.annotations[i] = []
        
        # Setup progress bar
        self.progress_bar.setMaximum(len(self.sentences))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        self.update_entity_display()
    
    def update_entity_display(self):
        """Update the display of current annotations"""
        total_entities = 0
        sentences_with_entities = 0
        
        for i, text_widget in enumerate(self.textWidgets):
            entities = []
            for start, end, label in text_widget.selected_ranges:
                entity_text = text_widget.sentence[start:end]
                entities.append((start, end, entity_text, label))
            
            self.annotations[i] = entities
            if entities:
                sentences_with_entities += 1
                total_entities += len(entities)
        
        # Update progress
        self.progress_bar.setValue(sentences_with_entities)
        
        # Update annotations display
        if total_entities == 0:
            self.annotations_label.setText("Current Annotations: None")
        else:
            self.annotations_label.setText(
                f"Current Annotations: {total_entities} entities in {sentences_with_entities} sentences"
            )
    
    def save_annotations(self):
        """Save annotations to JSON file"""
        if not self.annotations:
            QMessageBox.warning(self, "No Annotations", "No annotations to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotations", "annotations.json", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data for export
            export_data = {
                "sentences": self.sentences,
                "labels": self.entity_labels,
                "annotations": {}
            }
            
            for sentence_idx, entities in self.annotations.items():
                if entities:  # Only include sentences with annotations
                    export_data["annotations"][str(sentence_idx)] = [
                        {
                            "start": start,
                            "end": end,
                            "text": text,
                            "label": label,
                            "sentence": self.sentences[sentence_idx]
                        }
                        for start, end, text, label in entities
                    ]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Annotations saved to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save annotations: {str(e)}")
    
    def clear_all_annotations(self):
        """Clear all annotations"""
        reply = QMessageBox.question(
            self, "Clear Annotations", 
            "Are you sure you want to clear all annotations?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for text_widget in self.textWidgets:
                text_widget.selected_ranges = []
                text_widget.highlight_selections()
            
            self.update_entity_display()
            self.status_label.setText("All annotations cleared")

class EntitySummaryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Entity Summary")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        header.setStyleSheet("padding: 10px; background-color: #E3F2FD; border-radius: 5px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # By Label tab
        self.by_label_tree = QTreeWidget()
        self.by_label_tree.setHeaderLabels(["Label", "Entity", "Sentence #", "Context"])
        self.by_label_tree.setAlternatingRowColors(True)
        self.tab_widget.addTab(self.by_label_tree, "By Label")
        
        # By Sentence tab
        self.by_sentence_tree = QTreeWidget()
        self.by_sentence_tree.setHeaderLabels(["Sentence", "Entity", "Label", "Position"])
        self.by_sentence_tree.setAlternatingRowColors(True)
        self.tab_widget.addTab(self.by_sentence_tree, "By Sentence")
        
        # All Entities tab (flat list)
        self.all_entities_tree = QTreeWidget()
        self.all_entities_tree.setHeaderLabels(["Entity", "Label", "Sentence #", "Context"])
        self.all_entities_tree.setAlternatingRowColors(True)
        self.tab_widget.addTab(self.all_entities_tree, "All Entities")
        
        layout.addWidget(self.tab_widget)
        
        # Statistics
        self.stats_label = QLabel("No entities tagged")
        self.stats_label.setStyleSheet("padding: 10px; background-color: #F5F5F5; border-radius: 5px; margin-top: 10px;")
        layout.addWidget(self.stats_label)
        
        # Export button
        export_btn = QPushButton("Export Entity List")
        export_btn.clicked.connect(self.export_entities)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(export_btn)
    
    def update_entity_display(self, annotations, sentences):
        """Update all entity displays with current annotations"""
        # Clear all trees
        self.by_label_tree.clear()
        self.by_sentence_tree.clear()
        self.all_entities_tree.clear()
        
        # Collect all entities
        all_entities = []
        label_groups = {}
        sentence_groups = {}
        
        for sentence_idx, entities in annotations.items():
            if entities:
                sentence_num = sentence_idx + 1
                sentence_text = sentences[sentence_idx] if sentence_idx < len(sentences) else "Unknown"
                
                for start, end, entity_text, label in entities:
                    entity_info = {
                        'text': entity_text,
                        'label': label,
                        'sentence_idx': sentence_idx,
                        'sentence_num': sentence_num,
                        'start': start,
                        'end': end,
                        'context': self.get_context(sentence_text, start, end)
                    }
                    
                    all_entities.append(entity_info)
                    
                    # Group by label
                    if label not in label_groups:
                        label_groups[label] = []
                    label_groups[label].append(entity_info)
                    
                    # Group by sentence
                    if sentence_num not in sentence_groups:
                        sentence_groups[sentence_num] = []
                    sentence_groups[sentence_num].append(entity_info)
        
        # Populate By Label tree
        for label, entities in sorted(label_groups.items()):
            label_item = QTreeWidgetItem(self.by_label_tree)
            label_item.setText(0, f"{label} ({len(entities)})")
            label_item.setFont(0, QFont("Arial", 10, QFont.Bold))
            
            for entity in sorted(entities, key=lambda x: (x['sentence_num'], x['start'])):
                entity_item = QTreeWidgetItem(label_item)
                entity_item.setText(0, "")
                entity_item.setText(1, entity['text'])
                entity_item.setText(2, str(entity['sentence_num']))
                entity_item.setText(3, entity['context'])
        
        self.by_label_tree.expandAll()
        
        # Populate By Sentence tree
        for sentence_num, entities in sorted(sentence_groups.items()):
            sentence_item = QTreeWidgetItem(self.by_sentence_tree)
            sentence_item.setText(0, f"Sentence {sentence_num} ({len(entities)} entities)")
            sentence_item.setFont(0, QFont("Arial", 10, QFont.Bold))
            
            for entity in sorted(entities, key=lambda x: x['start']):
                entity_item = QTreeWidgetItem(sentence_item)
                entity_item.setText(0, "")
                entity_item.setText(1, entity['text'])
                entity_item.setText(2, entity['label'])
                entity_item.setText(3, f"{entity['start']}-{entity['end']}")
        
        self.by_sentence_tree.expandAll()
        
        # Populate All Entities tree
        for entity in sorted(all_entities, key=lambda x: (x['sentence_num'], x['start'])):
            entity_item = QTreeWidgetItem(self.all_entities_tree)
            entity_item.setText(0, entity['text'])
            entity_item.setText(1, entity['label'])
            entity_item.setText(2, str(entity['sentence_num']))
            entity_item.setText(3, entity['context'])
        
        # Update statistics
        total_entities = len(all_entities)
        unique_entities = len(set(entity['text'].lower() for entity in all_entities))
        total_labels = len(label_groups)
        sentences_with_entities = len(sentence_groups)
        
        stats_text = f"""
        Total Entities: {total_entities}
        Unique Entities: {unique_entities}
        Labels Used: {total_labels}
        Sentences with Entities: {sentences_with_entities}
        """.strip()
        
        self.stats_label.setText(stats_text)
        
        # Resize columns
        for tree in [self.by_label_tree, self.by_sentence_tree, self.all_entities_tree]:
            for i in range(tree.columnCount()):
                tree.resizeColumnToContents(i)
    
    def get_context(self, sentence, start, end, context_length=30):
        """Get context around the entity for display"""
        context_start = max(0, start - context_length)
        context_end = min(len(sentence), end + context_length)
        
        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < len(sentence) else ""
        
        context = sentence[context_start:context_end]
        # Highlight the entity within the context
        entity_start_in_context = start - context_start
        entity_end_in_context = end - context_start
        
        highlighted_context = (
            context[:entity_start_in_context] + 
            "[" + context[entity_start_in_context:entity_end_in_context] + "]" +
            context[entity_end_in_context:]
        )
        
        return prefix + highlighted_context + suffix
    
    def export_entities(self):
        """Export entity list to CSV or text file"""
        if self.parent_window and hasattr(self.parent_window, 'annotations'):
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Entity List", "entity_list.txt", 
                "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                try:
                    all_entities = []
                    for sentence_idx, entities in self.parent_window.annotations.items():
                        for start, end, entity_text, label in entities:
                            all_entities.append({
                                'entity': entity_text,
                                'label': label,
                                'sentence': sentence_idx + 1,
                                'position': f"{start}-{end}"
                            })
                    
                    if file_path.endswith('.csv'):
                        import csv
                        with open(file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(['Entity', 'Label', 'Sentence', 'Position'])
                            for entity in all_entities:
                                writer.writerow([entity['entity'], entity['label'], 
                                               entity['sentence'], entity['position']])
                    else:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write("Entity List\n")
                            f.write("=" * 50 + "\n\n")
                            
                            current_label = None
                            for entity in sorted(all_entities, key=lambda x: (x['label'], x['sentence'])):
                                if entity['label'] != current_label:
                                    current_label = entity['label']
                                    f.write(f"\n{current_label}:\n")
                                    f.write("-" * len(current_label) + "\n")
                                
                                f.write(f"  • {entity['entity']} (Sentence {entity['sentence']})\n")
                    
                    QMessageBox.information(self, "Success", f"Entity list exported to {file_path}")
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export entities: {str(e)}")

class NamedEntityAnnotationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sentences = []
        self.currentSentenceIndex = 0
        self.annotations = {}  # Will store {sentence_index: [(start, end, text, label), ...]}
        self.textWidgets = []
        self.entity_labels = ["Private", "Communal/Public", "Extraterrestrial/Figurative", "Natural", "Institutional"]  # Default labels
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Named Entity Annotation Tool")
        self.setGeometry(100, 100, 1400, 800)  # Made wider for side panel
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create splitter for main content and entity summary
        splitter = QSplitter(Qt.Horizontal)
        main_widget_layout = QHBoxLayout(main_widget)
        main_widget_layout.addWidget(splitter)
        
        # Left panel (main annotation interface)
        left_panel = QWidget()
        layout = QVBoxLayout(left_panel)
        
        # Header
        header = QLabel("Named Entity Annotation Tool")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("padding: 20px; color: #2E7D32;")
        layout.addWidget(header)
        
        # Instructions
        instructions = QLabel(
            "Instructions: Double-click any word to select it instantly, or double-click and drag to select multiple words with smart word boundaries. "
            "You can also use traditional click-and-drag for precise selections. "
            "You'll be prompted to select a label type for each entity. Different labels are highlighted in different colors. "
            "To remove an entity, double-click on it or drag over it exactly. Click 'Save Annotations' when finished."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: #E8F5E8; border-radius: 5px; margin: 10px;")
        layout.addWidget(instructions)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Text File")
        load_btn.clicked.connect(self.load_sentences)
        load_btn.setStyleSheet(self.get_button_style("#4CAF50"))
        control_layout.addWidget(load_btn)
        
        labels_btn = QPushButton("Manage Labels")
        labels_btn.clicked.connect(self.manage_labels)
        labels_btn.setStyleSheet(self.get_button_style("#FF9800"))
        control_layout.addWidget(labels_btn)
        
        save_btn = QPushButton("Save Annotations")
        save_btn.clicked.connect(self.save_annotations)
        save_btn.setStyleSheet(self.get_button_style("#2196F3"))
        control_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear All Annotations")
        clear_btn.clicked.connect(self.clear_all_annotations)
        clear_btn.setStyleSheet(self.get_button_style("#FF5722"))
        control_layout.addWidget(clear_btn)
        
        layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Current labels display
        self.labels_display = QLabel(f"Current Labels: {', '.join(self.entity_labels)}")
        self.labels_display.setStyleSheet("padding: 5px; background-color: #FFF3E0; border-radius: 3px; font-size: 11px;")
        layout.addWidget(self.labels_display)
        
        # Scrollable area for sentences
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Current annotations display
        self.annotations_label = QLabel("Current Annotations: None")
        self.annotations_label.setStyleSheet("padding: 10px; background-color: #F5F5F5; border-radius: 5px;")
        layout.addWidget(self.annotations_label)
        
        # Status bar
        self.status_label = QLabel("Load a text file to begin annotation")
        self.status_label.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(self.status_label)
        
        # Right panel (entity summary)
        self.entity_summary = EntitySummaryWidget(self)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(self.entity_summary)
        splitter.setSizes([800, 600])  # Initial sizes
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
            QPushButton:pressed {{
                background-color: {color}BB;
            }}
        """
    
    def manage_labels(self):
        """Open dialog to manage entity labels"""
        dialog = EntityLabelManager(self.entity_labels, self)
        if dialog.exec_() == QDialog.Accepted:
            self.entity_labels = dialog.labels
            self.labels_display.setText(f"Current Labels: {', '.join(self.entity_labels)}")
    
    def load_sentences(self):
        """Load sentences from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Text File", "", "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sentences = data
                    else:
                        QMessageBox.warning(self, "Invalid Format", "JSON file must contain a list of sentences.")
                        return
            else:
                # This part cleans the stories into sentence segments
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Clean new lines
                    content = re.sub(r"\n", " ", content)

                    # Sentence segmentation
                    segmentedSentences = nltk.sent_tokenize(content)

                    self.sentences = segmentedSentences
                                
            self.setupAnnotationInterface()
            self.status_label.setText(f"Loaded {len(self.sentences)} sentences")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def setupAnnotationInterface(self):
        """Setup the interface with loaded sentences"""
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())): 
            self.scroll_layout.itemAt(i).widget().setParent(None)
        
        self.textWidgets = []
        self.annotations = {}
        
        # Create text widgets for each sentence
        for i, sentence in enumerate(self.sentences):
            # Sentence header
            header = QLabel(f"Sentence {i + 1}:")
            header.setFont(QFont("Arial", 12, QFont.Bold))
            header.setStyleSheet("margin-top: 15px; margin-bottom: 5px; color: #333;")
            self.scroll_layout.addWidget(header)
            
            # Clickable text widget
            text_widget = ClickableTextEdit(sentence, i, self)
            self.textWidgets.append(text_widget)
            self.scroll_layout.addWidget(text_widget)
            
            # Initialize annotations for this sentence
            self.annotations[i] = []
        
        # Setup progress bar
        self.progress_bar.setMaximum(len(self.sentences))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        self.update_entity_display()
    
    def update_entity_display(self):
        """Update the display of current annotations"""
        total_entities = 0
        sentences_with_entities = 0
        
        for i, text_widget in enumerate(self.textWidgets):
            entities = []
            for start, end, label in text_widget.selected_ranges:
                entity_text = text_widget.sentence[start:end]
                entities.append((start, end, entity_text, label))
            
            self.annotations[i] = entities
            if entities:
                sentences_with_entities += 1
                total_entities += len(entities)
        
        # Update progress
        self.progress_bar.setValue(sentences_with_entities)
        
        # Update annotations display
        if total_entities == 0:
            self.annotations_label.setText("Current Annotations: None")
        else:
            self.annotations_label.setText(
                f"Current Annotations: {total_entities} entities in {sentences_with_entities} sentences"
            )
        
        # Update entity summary widget
        self.entity_summary.update_entity_display(self.annotations, self.sentences)
    
    def save_annotations(self):
        """Save annotations to JSON file"""
        if not self.annotations:
            QMessageBox.warning(self, "No Annotations", "No annotations to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotations", "annotations.json", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data for export
            export_data = {
                "sentences": self.sentences,
                "labels": self.entity_labels,
                "annotations": {}
            }
            
            for sentence_idx, entities in self.annotations.items():
                if entities:  # Only include sentences with annotations
                    export_data["annotations"][str(sentence_idx)] = [
                        {
                            "start": start,
                            "end": end,
                            "text": text,
                            "label": label,
                            "sentence": self.sentences[sentence_idx]
                        }
                        for start, end, text, label in entities
                    ]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Annotations saved to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save annotations: {str(e)}")
    
    def clear_all_annotations(self):
        """Clear all annotations"""
        reply = QMessageBox.question(
            self, "Clear Annotations", 
            "Are you sure you want to clear all annotations?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for text_widget in self.textWidgets:
                text_widget.selected_ranges = []
                text_widget.highlight_selections()
            
            self.update_entity_display()
            self.status_label.setText("All annotations cleared")

if __name__ == "__main__":
    annotationTool = QApplication(sys.argv)
    
    annotationTool.setStyle('Fusion')
    
    window = NamedEntityAnnotationTool()
    window.show()
    
    sys.exit(annotationTool.exec_())