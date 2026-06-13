## 🌱 Contributing to RaizQA

Welcome to the RaizQA project! We are thrilled that you are interested in contributing to our qualitative analysis application. This guide will help you understand our architecture, logic, and how you can get started with contributing to either the frontend or backend of the project.

## 🛠️ Tech Stack & Setup

RaizQA is a desktop application built entirely with **Python** and **PySide6** (Qt for Python). 

### Setting up your development environment:
1. **Fork and clone** the repository.
2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**:
   ```bash
   python main.py
   ```
5. **Run tests**:
   The project uses `pytest` for unit and integration testing. Run the test suite using:
   ```bash
   pytest tests/
   ```

## 🏗️ Project Architecture & Logic

To contribute effectively, it's important to understand how RaizQA is structured. The application is broadly divided into a **Frontend (UI)** and a **Backend (Core logic & Persistence)**. We are actively moving towards a more modular structure, so it's vital to follow these patterns.

### 🖥️ Frontend (`gui/` and `code_viewer/`)
The frontend is responsible for everything the user interacts with, built using PySide6.
*   **`gui/main_window.py`**: The main application shell. Historically, it contained most of the logic, but it is currently being refactored to act strictly as a coordinator. It sets up the workspace layout, manages the global state (e.g., the currently active project), and routes Qt Signals between widgets.
*   **Modular Widgets (`gui/widgets/`)**: This is the new home for modular UI components (e.g., `actions_panel.py`, `document_editor.py`, `local_search.py`). **All new UI panels and components should be created here.** These components should be self-contained and communicate with the main window using PySide6 Signals and Slots.
*   **`gui/dialogs/`**: Contains modular popup windows for specific features (e.g., `new_code_dialog.py`, `wordcloud_dialog.py`, `compare_dialog.py`). 
*   **`gui/image_viewer.py`**: Handles image rendering, zooming, and drawing selection rectangles using `QGraphicsView`. A key logic here is that **selection coordinates are mapped to the original image resolution (`image_size`)**, ensuring that zoom levels or window resizing operations don't offset the coded zones.
*   **Text Rendering & Highlighting**: Document text is displayed using `QTextEdit`. When a user selects text and codes it, the UI captures the exact `start` and `end` indices of the selection. These indices are used to inject colored background highlights (overlays) directly into the text component.

**How to contribute to the Frontend:**
*   **Add new modular widgets**: When adding new UI elements, build them as self-contained classes in `gui/widgets/` and embed them into `main_window.py`. Please avoid bloating `main_window.py`.
*   **Add new analysis dialogs**: Create a new `QDialog` class in `gui/dialogs/` and hook it up to the main application.
*   **UI/UX Polishing**: Improve the visual theme in `gui/theme.py` and `gui/styles.qss`, or enhance responsiveness and layouts. When adding new widgets, ensure they use the established style classes to maintain consistency.

### ⚙️ Backend (`core/`)
The backend is completely local and file-based. It manages data persistence, file parsing, and business logic without needing a database server.
*   **In-Memory Data Structures (EDDs)**: `core/project.py` maintains high-performance in-memory dictionaries (`codes_dict`, `themes_dict`, `texts_dict`). It supports sub-code hierarchies, allowing structured analysis. This allows for O(1) instant read times when querying coded fragments or searching through text, heavily optimizing the analysis process.
*   **Atomic Persistence Logic**: Projects are stored in a standard folder structure containing JSON files (`project_data.json`, `edds_data.json`). The backend uses `PointerManager` for atomic saves, ensuring that even if the app crashes mid-save, the project state will not become corrupted.
*   **Dynamic Text Synchronization (Diff-Match-Patch)**: When a document is edited by the user, the backend uses a `diff_match_patch` algorithm (with a `0.3` threshold tolerance) to automatically locate and resync the `start` and `end` indices of existing coded fragments. If a sentence is completely overwritten, the associated code fragment is silently purged to maintain data integrity.
*   **Importing Logic**: Supported formats (TXT, PDF, DOCX, images) are parsed upon import. Text documents are converted into raw text strings and stored internally, while images are copied directly into the project's `/documentos` folder.
*   **Collaboration & Merging**: Handled by `core/merge_manager.py`, `core/import_manager.py`, and `core/export_manager.py`, this logic allows multiple users to share and merge project codes seamlessly. Ensure any changes to EDDs are compatible with these collaborative features.

**How to contribute to the Backend:**
*   **Add new document formats**: Extend `core/project.py` to parse new file types (e.g., CSV or Markdown) and integrate them into the project structure.
*   **Improve Export functionalities**: Help build better export handlers in `core/export_manager.py` (e.g., exporting to new formats like HTML or SPSS).
*   **Data integrity & Testing**: The project uses `pytest`. All new features, especially core logic and data transformations, must pass existing tests and include new ones in the `tests/` directory to prevent regressions and ensure the JSON state never corrupts.

## 🔄 Contribution Workflow

1. **Branch out**: Create a new branch for your feature or bugfix (`git checkout -b feature/my-new-feature`).
2. **Code**: Make your changes, keeping the separation of concerns (Frontend modular widgets in `gui/widgets/`, Backend in `core/`). Avoid touching legacy files like `gui_raizQA.py` and `models/`.
3. **Commit**: Write clear, concise commit messages.
4. **Push**: Push your branch to your fork.
5. **Pull Request**: Open a PR against the `NewStructure` branch (or `main`, depending on the target). Provide a clear description of what your PR solves or adds.
