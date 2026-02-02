# User Task for Agents

## Task 1: Research Dinosaur Facts
- **Description**: Research 10 dinosaurs including scientific names, key traits, fun facts, and 3 Bulgarian dinosaur terms.
- **Input**: None (internal knowledge)
- **Output**: `dinosaur_facts_en.md`
- **Expected Output Format**:
  markdown
  # Dinosaur Facts (English)
  ## T-Rex (Тиранозавър)
  - **Size**: 12 meters long, 4 meters tall.
  - **Diet**: Carnivore (ate meat).
  - **Fun Fact**: Could roar like a lion!
  

## Task 2: Localize Content
- **Description**: Translate `dinosaur_facts_en.md` into Bulgarian with age-appropriate vocabulary and cultural references.
- **Input**: `dinosaur_facts_en.md`
- **Output**: `dinosaur_facts_bg.md`
- **Expected Output Format**:
  markdown
  # Забележителни Диносаври (на български)
  ## Тиранозавър
  - **Височина**: 4 метра.
  - **Храна**: Яде месо.
  - **Знаеш ли?** Могел да издава звуци като лъв!
  

## Task 3: Write Children’s Story
- **Description**: Create a 10-page Bulgarian story with an engaging plot (e.g., "Трико" on an adventure), educational tie-ins, and interactive elements.
- **Input**: `dinosaur_facts_bg.md`
- **Output**: `dinosaur_story_bg.md`

## Task 4: Design Illustrations
- **Description**: Generate detailed descriptions for dinosaur illustrations, backgrounds, and interactive elements.
- **Input**: `dinosaur_story_bg.md`
- **Output**: `illustration_guidelines.md`
- **Expected Output Format**:
  markdown
  # Илюстрации за "Трико и Тайната..."
  **Страница 3**:
  - **Трико**: Стои на задни крака, гледа към пещера.
  - **Фон**: Слънчева гора с листа в форма на сърца.
  

## Task 5: Compile Final Book
- **Description**: Combine `dinosaur_story_bg.md`, `illustration_guidelines.md`, and a glossary into a 15-page PDF with interactive prompts.
- **Input**: `dinosaur_story_bg.md`, `illustration_guidelines.md`, glossary
- **Output**: `final_book_bg.pdf`
- **Expected Output**:
  - Cover: "Трико и Приключението му с Диносаврите"
  - Interactive stickers
  - QR code linking to Bulgarian audiobook

## Quality Checks
- **Sequential Dependencies**: Each task must complete before the next begins.
- **Cultural Sensitivity**: Bulgarian Localization Expert ensures no offensive terms or complex grammar.
- **Scalability**: Add a Voice Actor Agent for audiobook if needed.