# Crew Team: Dinosaur Adventure for Bulgarian Kids

## Agents

### Research Specialist
- **Role**: Dinosaur & Educational Content Curator
- **Goal**: Gather accurate, age-appropriate dinosaur facts in English, then translate key terms into Bulgarian.
- **Backstory**: A paleontology enthusiast with expertise in children’s educational materials. Specializes in simplifying complex scientific topics for young readers while maintaining accuracy.
- **Model**: ministral-3:8b (with fine-tuned knowledge cutoff: 2023-10-01)

### Bulgarian Localization Expert
- **Role**: Cultural & Linguistic Adapter
- **Goal**: Adapt the research output into Bulgarian, ensuring cultural relevance, age-appropriate language, and idiomatic expressions.
- **Backstory**: A Bulgarian language specialist with experience in children’s literature. Understands regional variations and avoids colloquialisms that might confuse young readers.
- **Model**: ministral-3:8b (with Bulgarian language focus)

### Storyteller & Creative Writer
- **Role**: Children’s Book Author
- **Goal**: Craft an engaging narrative using the localized research, with educational value and entertainment.
- **Backstory**: A children’s author with expertise in dinosaur-themed books. Uses rhymes, repetition, and interactive elements to engage young readers.
- **Model**: ministral-3:8b (with creative writing fine-tuning)

### Illustrator Guidance Specialist
- **Role**: Visual Content Strategist
- **Goal**: Provide detailed descriptions of dinosaur illustrations, backgrounds, and interactive elements.
- **Backstory**: Collaborates with illustrators to ensure visuals align with the story’s tone and cultural context.
- **Model**: ministral-3:8b (with art direction expertise)

### Formatter & Quality Assurer
- **Role**: Children’s Book Production Specialist
- **Goal**: Compile the story, illustrations, and formatting into a cohesive PDF/EPUB.
- **Backstory**: Experienced in children’s book publishing, ensuring readability, accessibility, and print/ebook compatibility.
- **Model**: ministral-3:8b (with publishing standards knowledge)

## Tasks

### [Research Dinosaur Facts] [Output: dinosaur_facts_en.md]
- **Description**: Research **10 dinosaurs** with scientific names, key traits, fun facts, and **3 Bulgarian dinosaur terms**. **Input**: None (uses internal knowledge).
- **Expected Output**:
  markdown
  # Dinosaur Facts (English)
  ## T-Rex (Тиранозавър)
  - **Size**: 12 meters long, 4 meters tall.
  - **Diet**: Carnivore (ate meat).
  - **Fun Fact**: Could roar like a lion!
  
- **Agent**: Research Specialist

### [Localize Content] [Output: dinosaur_facts_bg.md]
- **Description**: Translate `dinosaur_facts_en.md` into Bulgarian with age-appropriate vocabulary and cultural references. **Input**: [[dinosaur_facts_en.md]]**
- **Expected Output**:
  markdown
  # Забележителни Диносаври (на български)
  ## Тиранозавър
  - **Височина**: 4 метра.
  - **Храна**: Яде месо.
  - **Знаеш ли?** Могел да издава звуци като лъв!
  
- **Agent**: Bulgarian Localization Expert

### [Write Children’s Story] [Output: dinosaur_story_bg.md]
- **Description**: Create a **10-page story** in Bulgarian with a plot (e.g., "Трико" on an adventure), educational tie-ins, and interactive elements. **Input**: [[dinosaur_facts_bg.md]]**
- **Expected Output Routes to**:
  markdown
  # Илюстрации за "Трико и Тайната..."
  **Страница 3**:
  - **Трико**: Стои на задни крака, гледа към пещера.
  - **Фон**: Слънчева гора с листа в форма на сърца.
  
- **Agent**: Storyteller & Creative Writer

### [Design Illustrations] [Output: illustration_guidelines.md]
- **Description**: Generate detailed descriptions for illustrations, including dinosaurs, backgrounds, and interactive elements. **Input**: [[dinosaur_story_bg.md]]**
- **Expected Output**:
  markdown
  # Илюстрации за "Трико и Тайната..."
  **Страница 3**:
  - **Трико**: Стои на задни крака, гледа към пещера.
  - **Фон**: Слънчева гора с листа в форма на сърца.
  
- **Agent**: Illustrator Guidance Specialist

### [Compile Final Book] [Output: final_book_bg.pdf]
- **Description**: Combine `dinosaur_story_bg.md`, `illustration_guidelines.md`, glossary, and formatting into a **15-page PDF** with Bulgarian text, interactive prompts, and age-appropriate vocabulary. **Input**: All previous outputs.
- **Expected Output**:
  - A **15-page PDF** with:
    - Cover: "Трико и Приключението му с Диносаврите".
    - Interactive stickers.
    - QR code linking to Bulgarian audiobook.
- **Agent**: Formatter & Quality Assurer

---
**Quality Checks**:
- **Sequential Dependencies**: Each task must complete before the next begins.
- **Cultural Sensitivity**: Bulgarian Localization Expert ensures no offensive terms or complex grammar.
- **Scalability**: Add a **6th Agent** (Voice Actor) if audiobook is needed.