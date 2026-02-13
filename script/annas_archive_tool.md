# Anna's Archive Tool - Пълна документация

## Въведение

Anna's Archive Tool е комплексна система за търсене, изтегляне и анализ на книги, интегрирана с CrewAI екосистемата. Той предоставя мощни инструменти за автоматизиране на процесите, свързани с намиране и обработка на електронни книги.

### Основни цели
- Автоматизирано търсене на книги в Anna's Archive
- Изтегляне на книги в различни формати (PDF, EPUB, MOBI)
- Конверсия на файлове за по-лесна обработка
- RAG (Retrieval-Augmented Generation) функционалност за анализ на съдържание
- Интеграция с CrewAI за автоматизирани задачи

### Основни възможности
- Търсене по заглавие и автор
- Поддръжка на множество източници и огледални сайтове
- Автоматично обработка на Cloudflare защитата
- Конверсия на MOBI файлове в TXT формат
- Индексиране и търсене в съдържанието на книгите
- Интеграция с CrewAI инструменти

---

## Архитектура на системата

### Файлова структура

```
script/
├── annas_archive_tool.py          # Основен CrewAI инструмент
├── annas_book_search.py           # Модул за търсене на книги
├── annas_download_manager.py      # Фасаден модул за изтегляне
├── annas_download_manager_core.py # Основна логика за изтегляне
├── annas_link_extractor.py        # Извличане на линкове за изтегляне
├── annas_file_converter.py       # Конверсия на файлове
├── annas_cli.py                   # CLI интерфейс
├── annas_utils.py                 # Утилити функции
├── annas_browser_manager.py       # Управление на браузър
└── annas_config.py                # Конфигурация и настройки
```

### Диаграма на взаимодействието

```
CrewAI Tools Registry
         ↓
    AnnasArchiveTool
         ↓
┌─────────────────────────────┐
│  annas_download_manager.py  │ (Фасаден модул)
└─────────────────────────────┘
         ↓
┌─────────────────────────────┐
│annas_download_manager_core.py│ (Основна логика)
└─────────────────────────────┘
         ↓
┌─────────────────────────────┐
│  annas_link_extractor.py    │ (Извличане на линкове)
└─────────────────────────────┘
         ↓
┌─────────────────────────────┐
│  annas_file_converter.py    │ (Конверсия на файлове)
└─────────────────────────────┘
```

### Поток на данните

1. **Потребителска заявка** → AnnasArchiveTool
2. **Търсене** → annas_book_search.py
3. **Намиране на линкове** → annas_link_extractor.py
4. **Изтегляне** → annas_download_manager_core.py
5. **Конверсия** → annas_file_converter.py (ако е необходимо)
6. **Индексиране** → rag_storage.py (за RAG функционалност)
7. **Анализ** → rag_book_tool.py

---

## Подробен опис на всеки модул

### 1. annas_config.py

**Описание:** Конфигурационен модул, съдържащ всички настройки, константи и входни схеми.

**Основни компоненти:**

#### Константи
```python
# Anna's Archive домейни (често се променят)
DOMAINS = [
    "https://annas-archive.li",
    "https://annas-archive.se", 
    "https://annas-archive.org",
    "https://bg.annas-archive.li",
]

# IPFS gateways за fallback изтегляне
IPFS_GATEWAYS = [
    "https://cloudflare-ipfs.com/ipfs/",
    "https://ipfs.io/ipfs/",
    "https://gateway.pinata.cloud/ipfs/",
    "https://dweb.link/ipfs/"
]
```

#### Logging система
```python
def debug_print(msg: str):
    """Print and log debug message if DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        logger.debug(msg)
```

#### Input schemas за CrewAI
```python
class AnnasArchiveInput(BaseModel):
    """Input schema for AnnasArchiveTool."""
    query: str = Field(..., description="The name and author of the book to search for.")

class BookResult(BaseModel):
    """Represents a search result from Anna's Archive."""
    title: str
    author: Optional[str] = None
    format: Optional[str] = None
    size: Optional[str] = None
    url: str
    md5: Optional[str] = None
```

**Функционалност:**
- Дефинира всички константи, използвани в системата
- Предоставя logging функционалност
- Дефинира входни схеми за CrewAI инструменти
- Управлява динамичните URL променливи

---

### 2. annas_utils.py

**Описание:** Модул с утилити функции за помощни операции.

**Основни функции:**

#### score_book_relevance()
```python
def score_book_relevance(book_title: str, query: str) -> float:
    """
    Score how relevant a book title is to the search query.
    Higher score = better match.
    
    Scoring:
    - Exact title match: 100
    - Title starts with query: 90
    - Title contains query as whole words: 80
    - Query words in title: 10 per word
    - Penalty for extra words in title: -5 per extra word
    """
```

#### resolve_download_dir()
```python
def resolve_download_dir(download_dir: Optional[str], crew_name: Optional[str]) -> str:
    """Determine the download directory."""
    # Логика за определяне на директорията за изтегляне
    # Поддържа експлицитни директории, crew-специфични директории
    # и environment променливи
```

#### verify_file_type()
```python
def verify_file_type(path: str, initial_ext: str) -> Tuple[str, str]:
    """Verifies file type using magic bytes and renames if necessary."""
    # Проверява типа файла чрез magic bytes
    # Поддържа PDF, EPUB, MOBI, TXT формати
    # Преименува файла ако е необходимо
```

**Функционалност:**
- Оценка на релевантността на резултати от търсене
- Определяне на директории за изтегляне
- Проверка и валидация на типове файлове
- Генериране на безопасни имена на файлове

---

### 3. annas_browser_manager.py

**Описание:** Модул за управление на браузър и автоматизирани уеб операции.

**Основни компоненти:**

#### BrowserManager клас
```python
class BrowserManager:
    """Manages Playwright browser instance and related operations."""
    
    def __init__(self):
        # Инициализация на Playwright браузър
        
    def find_working_domain(self) -> Optional[str]:
        """Find a working Anna's Archive domain."""
        
    def init_browser(self, headless: bool = False) -> None:
        """Initialize Playwright browser instance."""
        
    def close_browser(self) -> None:
        """Close Playwright browser instance."""
        
    def wait_for_cloudflare(self, page: Page, timeout: int = 30) -> bool:
        """Wait for Cloudflare challenge to complete."""
```

**Функционалност:**
- Управление на Playwright браузър инстанция
- Автоматично намиране на работещи домейни
- Обработка на Cloudflare защитата
- Създаване на абсолютни URL адреси
- Debug функционалност за запазване на страници

---

### 4. annas_book_search.py

**Описание:** Модул за търсене на книги в Anna's Archive.

**Основни компоненти:**

#### BookSearcher клас
```python
class BookSearcher:
    """Handles searching for books on Anna's Archive."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        
    def search_books(self, query: str, max_results: int = 10) -> List[BookResult]:
        """Search for books and return results."""
        
    def score_and_sort_results(self, results: List[BookResult], query: str) -> List[BookResult]:
        """Score and sort results by relevance."""
```

**Функционалност:**
- Търсене на книги по заглавие и автор
- Обработка на резултати от търсенето
- Оценка и сортиране на резултати по релевантност
- Поддържа множество страници с резултати

---

### 5. annas_download_manager.py

**Описание:** Фасаден модул, който координира всички операции по изтегляне.

**Основни компоненти:**

#### DownloadManager клас (фасад)
```python
class DownloadManager:
    """Handles book downloading and file operations."""
    
    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        # Импортира функционалност от специализирани модули
```

**Функционалност:**
- Координира операциите между различните модули
- Предоставя единен API за изтегляне
- Управлява процеса на изтегляне от началото до края
- Обработва грешки и fallback стратегии

---

### 6. annas_download_manager_core.py

**Описание:** Основна логика за изтегляне на файлове.

**Основни функции:**

#### download_from_url()
```python
def download_from_url(url: str, output_path: str, book_title: str = "Unknown") -> bool:
    """
    Download file from URL using direct HTTP request with browser session.
    Returns True if successful.
    """
```

#### download_book()
```python
def download_book(book_url: str, output_dir: str, preferred_ext: str = 'pdf', 
                  filename: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Download a book, trying multiple sources.
    Returns (file_path, extension) or (None, error_message).
    """
```

#### try_mirror_download()
```python
def try_mirror_download(mirror_url: str, output_path: str, 
                       book_title: str = "Unknown") -> bool:
    """
    Try to download from a mirror site (libgen, z-lib, etc.).
    """
```

**Функционалност:**
- Директно изтегляне на файлове от URL адреси
- Поддържа множество стратегии за изтегляне
- Обработва mirror сайтове като fallback
- Предоставя progress indication
- Валидира изтеглените файлове

---

### 7. annas_link_extractor.py

**Описание:** Модул за извличане на линкове за изтегляне от страниците на книгите.

**Основни функции:**

#### get_download_links()
```python
def get_download_links(browser_manager, book_url: str) -> Dict[str, List[str]]:
    """
    Extract download links from book detail page.
    Returns dict with keys: 'direct', 'mirrors', 'ipfs'
    """
```

#### find_slow_download_button()
```python
def find_slow_download_button(page) -> Optional[str]:
    """Find and click "Slow Download" button to get the actual download link."""
```

#### handle_countdown_timer()
```python
def handle_countdown_timer(page) -> bool:
    """Handle countdown timer on slow download page."""
```

**Функционалност:**
- Автоматично намиране на бутона за бавно изтегляне
- Обработка на countdown таймери
- Извличане на директни и mirror линкове
- Поддържа IPFS линкове като fallback

---

### 8. annas_file_converter.py

**Описание:** Модул за конверсия на файлове от един формат в друг.

**Основни функции:**

#### convert_mobi_to_txt()
```python
def convert_mobi_to_txt(mobi_path: str, output_dir: str) -> Optional[str]:
    """Converts a MOBI file to a TXT file using pymupdf (fitz)."""
```

#### convert_mobi_fallback()
```python
def convert_mobi_fallback(mobi_path: str, output_dir: str) -> Optional[str]:
    """Fallback method to convert MOBI to TXT using HTML extraction."""
```

#### read_file_content()
```python
def read_file_content(path: str, ext: str) -> str:
    """Extracts a snippet of text from the downloaded file."""
```

**Функционалност:**
- Конверсия на MOBI файлове в TXT формат
- Поддържа множество стратегии за конверсия
- Извличане на съдържание от различни формати
- Fallback механизми за по-голяма надеждност

---

### 9. annas_archive_tool.py

**Описание:** Основен CrewAI инструмент, който интегрира всички функционалности.

**Основни компоненти:**

#### AnnasArchiveTool клас
```python
class AnnasArchiveTool:
    """
    Search for books on Anna's Archive, download them, and read their content.
    Uses Playwright for reliable Cloudflare bypass.
    Integrates with crewAI and supports RAG indexing.
    """
    
    def __init__(self, **kwargs):
        # Инициализация на всички мениджъри
        
    def _run(self, query: str, download_dir: Optional[str] = None, 
             crew_name: Optional[str] = None, filename: Optional[str] = None,
             browser_mode: str = 'show') -> str:
        """
        Main execution method.
        Returns result message with file path and content preview.
        """
```

**Функционалност:**
- Пълен цикъл на работа: търсене → изтегляне → конверсия → анализ
- Интеграция с CrewAI инструменти
- Поддържа различни режими на браузър
- Автоматично RAG индексиране
- Обработва грешки и предоставя полезни съобщения

---

### 10. annas_cli.py

**Описание:** Команден ред интерфейс за инструментите.

**Основни функции:**
- Предоставя CLI достъп до основните функционалности
- Поддържа различни опции за конфигурация
- Лесна употреба за автоматизирани задачи

---

## Интеграция с CrewAI

### Tools Registry интеграция

AnnasArchiveTool е интегриран в CrewAI tools registry чрез `tools_registry.py`:

```python
# tools_registry.py
try:
    from annas_archive_tool import AnnasArchiveTool
    from rag_book_tool import AskBookTool
except (ImportError, ModuleNotFoundError):
    from script.annas_archive_tool import AnnasArchiveTool
    from script.rag_book_tool import AskBookTool

def get_tool_agent_tools():
    """Returns a list of tools for the Tool Agent."""
    tools = []
    
    # Anna's Archive tool
    tools.append(AnnasArchiveTool())
    
    # RAG Book Tool
    tools.append(AskBookTool())
    
    return tools
```

### Достъпни инструменти за агенти

#### AnnasArchiveTool
- **Име:** `annas_archive_tool`
- **Описание:** Search for books on Anna's Archive, download them, and read their content
- **Вход:** `query` - име и автор на книгата за търсене
- **Изход:** Път до изтегления файл и преглед на съдържанието

#### AskBookTool (RAG функционалност)
- **Име:** `ask_book_tool`
- **Описание:** Ask a question about a book that has been downloaded and indexed
- **Вход:** `query` - въпрос към книгата, `book_id` - ID на книгата (опционално)
- **Изход:** Релевантни секции от книгата с контекст

### Примери за използване в CrewAI

#### Базово търсене и изтегляне
```python
from crewai import Agent, Task, Crew

# Агент за търсене на книги
book_searcher = Agent(
    role='Book Researcher',
    goal='Find and download relevant books for research',
    backstory='You are an expert researcher who finds and downloads books.',
    tools=[annas_archive_tool],
    verbose=True
)

# Задача за търсене на книга
search_task = Task(
    description="Search for and download 'The Art of Clean Code' by Robert Martin",
    expected_output="Path to downloaded book file",
    agent=book_searcher
)

# Създаване и изпълнение на екип
crew = Crew(
    agents=[book_searcher],
    tasks=[search_task],
    verbose=True
)

result = crew.kickoff()
```

#### RAG анализ на изтеглена книга
```python
# Агент за анализ на книги
book_analyst = Agent(
    role='Book Analyst',
    goal='Analyze downloaded books and provide insights',
    backstory='You are a literary analyst who extracts insights from books.',
    tools=[ask_book_tool],
    verbose=True
)

# Задача за анализ
analysis_task = Task(
    description="Analyze the downloaded book and provide a summary of key concepts",
    expected_output="Comprehensive summary with key insights",
    agent=book_analyst
)

crew = Crew(
    agents=[book_analyst],
    tasks=[analysis_task],
    verbose=True
)

result = crew.kickoff()
```

#### Комбиниран подход
```python
# Агент, който търси и анализира
research_analyst = Agent(
    role='Research Analyst',
    goal='Find relevant books and analyze their content',
    backstory='You conduct comprehensive research by finding and analyzing books.',
    tools=[annas_archive_tool, ask_book_tool],
    verbose=True
)

# Комплексна задача
research_task = Task(
    description="Search for books about machine learning, download the best one, "
                "and provide a detailed analysis of key concepts and applications",
    expected_output="Comprehensive research report with book analysis",
    agent=research_analyst
)

crew = Crew(
    agents=[research_analyst],
    tasks=[research_task],
    verbose=True
)

result = crew.kickoff()
```

---

## RAG система

### Архитектура на RAG системата

RAG (Retrieval-Augmented Generation) системата се състои от два основни компонента:

#### 1. rag_storage.py - Хранилище за индексиране
```python
class RAGStorage:
    def __init__(self, persist_directory: str = "crews/shared/rag_db", llm=None):
        # Инициализация на векторно хранилище с ChromaDB
        # Поддържа HuggingFace embeddings или fallback embeddings
        
    def add_book(self, file_path: str, book_id: str):
        """Индексира книга във векторното хранилище"""
        
    def generate_hierarchical_summaries(self, text: str, book_id: str, source_path: str):
        """Генерира йерархични резюмета на книгата"""
        
    def query(self, query_text: str, book_id: Optional[str] = None, 
              k: int = 5, query_type: str = "SPECIFIC") -> List[Document]:
        """Заявка към векторното хранилище"""
```

#### 2. rag_book_tool.py - Инструмент за заявки
```python
class AskBookTool(BaseTool):
    name: str = "ask_book_tool"
    description: str = "Ask a question about a book that has been downloaded and indexed"
    
    def _classify_query(self, query: str) -> tuple[str, float]:
        """Класифицира заявката като BROAD, SPECIFIC или MIXED"""
        
    def _run(self, query: str, book_id: Optional[str] = None) -> str:
        """Изпълнява заявка към индексираните книги"""
```

### Функционалност на RAG системата

#### Индексиране на книги
- Автоматично индексиране при изтегляне
- Поддържа PDF, EPUB и TXT формати
- Генерира йерархични резюмета (секции и цялостни резюмета)
- Използва векторно търсене за релевантност

#### Типове заявки
1. **SPECIFIC** - Точни факти и събития
   - Използва по-голям k за пълно покритие
   - Фокусиране върху конкретни детайли

2. **BROAD** - Общи теми и сюжети
   - Комбинира резюмета с разнообразни фрагменти
   - Предоставя обща представа за книгата

3. **MIXED** - Комбиниран подход
   - Съчетава стратегиите за BROAD и SPECIFIC
   - Адаптивен според контекста на въпроса

#### Примери за RAG използване

```python
# След като книга е изтеглена и индексирана, можете да задавате въпроси:

# Въпрос за конкретен факт
result = ask_book_tool._run(
    query="What are the main principles of clean code according to Robert Martin?",
    book_id="the_art_of_clean_code"
)

# Въпрос за обща тема
result = ask_book_tool._run(
    query="Explain the concept of SOLID principles in software design",
    book_id="the_art_of_clean_code"
)

# Въпрос към всички индексирани книги
result = ask_book_tool._run(
    query="What books discuss design patterns and software architecture?"
)
```

---

## Примери за употреба

### Пример 1: Основно търсене и изтегляне

```python
from annas_archive_tool import AnnasArchiveTool

# Създаване на инструмент
tool = AnnasArchiveTool()

# Изпълнение на търсене
result = tool._run(
    query="The Pragmatic Programmer",
    download_dir="./downloads",
    browser_mode="headless"
)

print(result)
```

**Очакван изход:**
```
Successfully downloaded 'The Pragmatic Programmer' to './downloads/The Pragmatic Programmer.pdf'
Format: PDF, Size: 2,456,789 bytes

Content Preview:
[PDF - 345 pages]
The Pragmatic Programmer is a book about software development practices...
```

### Пример 2: Търсене с RAG анализ

```python
from annas_archive_tool import AnnasArchiveTool
from rag_book_tool import AskBookTool

# Изтегляне на книга
archive_tool = AnnasArchiveTool()
result = archive_tool._run(
    query="Clean Code",
    download_dir="./downloads"
)

# Анализ на изтеглената книга
ask_tool = AskBookTool()
analysis = ask_tool._run(
    query="What are the main principles of clean code?",
    book_id="Clean Code"
)

print(analysis)
```

### Пример 3: CrewAI екип за изследователска задача

```python
from crewai import Agent, Task, Crew, Process
from tools_registry import get_tool_agent_tools

# Зареждане на инструменти
tools = get_tool_agent_tools()
annas_tool = tools[0]  # AnnasArchiveTool
ask_tool = tools[1]    # AskBookTool

# Агент за изследване
research_agent = Agent(
    role='Research Specialist',
    goal='Conduct comprehensive research by finding and analyzing books',
    backstory='You are an expert researcher who specializes in finding and analyzing relevant literature.',
    tools=[annas_tool, ask_tool],
    verbose=True
)

# Задача за изследване
research_task = Task(
    description="Search for books about artificial intelligence and machine learning, "
                "download the most relevant one, and provide a detailed analysis "
                "of key concepts and applications.",
    expected_output="Comprehensive research report with book analysis and key insights",
    agent=research_agent
)

# Създаване на екип
crew = Crew(
    agents=[research_agent],
    tasks=[research_task],
    process=Process.sequential,
    verbose=True
)

# Изпълнение
result = crew.kickoff()
print(result)
```

### Пример 4: Batch обработка на множество книги

```python
from annas_archive_tool import AnnasArchiveTool
import os

tool = AnnasArchiveTool()

# Списък с книги за изтегляне
books_to_download = [
    "Design Patterns",
    "Refactoring",
    "Code Complete",
    "The Clean Coder"
]

# Директория за изтегляне
download_dir = "./batch_downloads"
os.makedirs(download_dir, exist_ok=True)

# Изтегляне на всички книги
for book in books_to_download:
    print(f"Downloading: {book}")
    result = tool._run(
        query=book,
        download_dir=download_dir,
        browser_mode="headless"
    )
    print(f"Result: {result[:100]}...")
    print("-" * 50)
```

---

## Дебъг и поддръжка

### Logging система

Системата предоставя детайлно logging за отстраняване на проблеми:

```python
# Включване на debug режим
import os
os.environ['DEBUG_MODE'] = 'True'

# Лог файловете се съхраняват в:
# script/annas_archive_tool.log
```

### Често срещани проблеми и решения

#### 1. Проблем с Cloudflare защита
**Симптом:** Страницата не се зарежда или изтеглянето се проваля
**Решение:** 
- Проверете дали браузърът се инициализира правилно
- Уверете се, че имате интернет връзка
- Пробвайте различен домейн от списъка DOMAINS

#### 2. Проблем с изтегляне от mirror сайтове
**Симптом:** Изтеглянето от основния източник се проваля
**Решение:**
- Системата автоматично пробва mirror сайтове
- Проверете дали имате достъп до огледалните сайтове
- Уверете се, че няма блокиране на Tor onion линкове

#### 3. Проблем с конверсия на MOBI файлове
**Симптом:** MOBI файлът не се конвертира в TXT
**Решение:**
- Системата използва pymupdf като основен метод
- Ако pymupdf не е наличен, използва fallback метод с HTML извличане
- Уверете се, че имате инсталирани необходимите библиотеки

#### 4. Проблем с RAG индексиране
**Симптом:** Книгата не се индексира или заявките не работят
**Решение:**
- Проверете дали книгата е в поддържан формат (PDF, EPUB, TXT)
- Уверете се, че директорията за индексиране съществува
- Проверете логовете за грешки при индексиране

### Конфигурация

#### Environment променливи
```bash
# Debug режим
export DEBUG_MODE=True

# Директория за изтегляне
export CREW_OUTPUT_DIR="./output"

# Браузър режим (show, hide, headless)
export BROWSER_MODE="headless"
```

#### Конфигурационни файлове
- `.env` файл за environment променливи
- `annas_config.py` за системни настройки
- `tools_registry.py` за инструменти на CrewAI

---

## API референция

### AnnasArchiveTool

#### Клас: AnnasArchiveTool

**Методи:**

##### `__init__(**kwargs)`
Инициализира инструментите с конфигурационни параметри.

**Параметри:**
- `kwargs` - допълнителни конфигурационни параметри

##### `_run(query: str, download_dir: Optional[str] = None, crew_name: Optional[str] = None, filename: Optional[str] = None, browser_mode: str = 'show') -> str`

Основен метод за изпълнение на търсене и изтегляне.

**Параметри:**
- `query` (str): Име и автор на книгата за търсене
- `download_dir` (Optional[str]): Експлицитна директория за изтегляне
- `crew_name` (Optional[str]): Име на crew за crew-специфична директория
- `filename` (Optional[str]): Персонализирано име на файла без разширение
- `browser_mode` (str): Режим на браузъра ('show', 'hide', 'headless')

**Връща:**
- `str`: Резултатно съобщение с път до файла и преглед на съдържанието

**Пример:**
```python
result = tool._run(
    query="The Pragmatic Programmer",
    download_dir="./my_books",
    browser_mode="headless"
)
```

### AskBookTool (RAG)

#### Клас: AskBookTool

**Методи:**

##### `_run(query: str, book_id: Optional[str] = None) -> str`

Задава въпрос към индексирана книга.

**Параметри:**
- `query` (str): Въпросът към книгата
- `book_id` (Optional[str]): ID на книгата (ако не е зададен, търси във всички)

**Връща:**
- `str`: Отговор с релевантни секции от книгата

**Пример:**
```python
result = ask_tool._run(
    query="What are the main principles of clean code?",
    book_id="Clean Code"
)
```

### Вътрешни функции

#### score_book_relevance(book_title: str, query: str) -> float
Оценява релевантността на заглавие спрямо заявката.

#### resolve_download_dir(download_dir: Optional[str], crew_name: Optional[str]) -> str
Определя директорията за изтегляне.

#### verify_file_type(path: str, initial_ext: str) -> Tuple[str, str]
Проверява и валидира типа на файла.

---

## Заключение

Anna's Archive Tool предоставя пълен набор от инструменти за автоматизиране на процесите, свързани с търсене, изтегляне и анализ на книги. Системата е:

- **Модулна:** Разделяна на специализирани компоненти за лесна поддръжка
- **Интегрирана:** Пълна интеграция с CrewAI екосистемата
- **Надеждна:** Множество стратегии за изтегляне и обработка на грешки
- **Гъвкава:** Поддържа различни формати и конфигурации
- **Мощна:** RAG функционалност за дълбок анализ на съдържание

Системата е готова за използване в автоматизирани работни процеси и може да бъде разширена с допълнителни функционалности според нуждите.

---

*Документацията е генерирана автоматично и отразява текущото състояние на Anna's Archive Tool.*