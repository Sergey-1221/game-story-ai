# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered game story generator that creates interactive quests and storylines in JSON format from text descriptions. The system uses LLMs, RAG, and advanced AI techniques for narrative generation, logic structuring, and scene visualization. The project includes Story2Game integration for structured logic and SceneCraft for 3D visualization.

## Key Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download language models (required for NLP)
python -m spacy download ru_core_news_sm
python -m spacy download en_core_web_sm

# Create .env file from example
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
# Then edit .env with actual API keys
```

### Running the System
```bash
# Run Streamlit UI (recommended)
venv\Scripts\streamlit.exe run streamlit_app.py  # Windows
streamlit run streamlit_app.py  # Linux/Mac

# Or use batch scripts
run_ui.bat  # Windows - Launches UI with auto-install of dependencies
run_all.bat  # Windows - Starts both API and UI in separate windows
./run_ui.sh  # Linux/Mac

# Basic quest generation (programmatic)
venv\Scripts\python.exe src/quest_generator.py  # Windows
python src/quest_generator.py  # Linux/Mac

# Run API server
venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000  # Windows
uvicorn src.api.main:app --reload --port 8000  # Linux/Mac
# Or use: start_api.bat (Windows)

# Run demos
venv\Scripts\python.exe examples/story2game_scenecraft_demo.py
venv\Scripts\python.exe examples/hybrid_pipeline_demo.py

# CLI interface
venv\Scripts\python.exe main.py --input scenario.txt --output quest.json
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run single test file
pytest tests/unit/test_parser.py -v

# Run test generation scripts
venv\Scripts\python.exe test_generation.py
venv\Scripts\python.exe test_quest_generation.py
```

### Development Tasks
```bash
# Type checking
mypy src/

# Format code (if configured)
black src/
isort src/

# Linting (if configured)
flake8 src/
pylint src/
```

## Core Architecture

### Generation Pipeline Flow
1. **Input Processing**: `InputParser` extracts scenario parameters (genre, hero, goal)
2. **Knowledge Retrieval**: `KnowledgeBase` + RAG retrieves genre-specific context
3. **Story Planning**: `StoryPlanner` creates quest structure with branching
4. **Scene Generation**: `SceneGenerator` uses LLM to create detailed scenes
5. **Logic Enhancement**: `Story2GameEngine` adds preconditions/effects
6. **Visualization**: `SceneCraftVisualizer` generates 3D layouts and images
7. **Validation**: `BranchManager` ensures quest integrity
8. **Output**: `OutputFormatter` produces final JSON/code

### Key Integration Points

**QuestGenerator** is the main entry point that orchestrates basic generation:
- Handles both sync/async generation
- Manages the sequential pipeline of all modules
- Located in `src/quest_generator.py`

**IntegratedQuestGenerator** extends this with Story2Game and SceneCraft:
- Adds structured logic with preconditions/effects
- Enables 3D visualization and layout generation
- Supports dynamic action expansion
- Located in `src/modules/integrated_quest_generator.py`

**HybridPipeline** provides advanced integration strategies:
- Sequential, collaborative, and adaptive generation modes
- Cross-modal feedback between components
- Located in `src/modules/hybrid_pipeline.py`

### Module Dependencies

The system uses a layered architecture:
- **Core Layer**: Models (`src/core/models.py`) define all data structures
- **Module Layer**: Individual generators/engines in `src/modules/`
- **Integration Layer**: Combines modules (`quest_generator.py`, `integrated_quest_generator.py`)
- **API Layer**: FastAPI server in `src/api/main.py`

### Critical State Management

**WorldState** (in Story2GameEngine):
- Tracks game objects, locations, inventory
- Validates action preconditions
- Applies effects after actions

**KnowledgeBase**:
- Uses ChromaDB for vector storage (persisted in `data/chroma/`)
- Caches genre-specific content
- Must be initialized with embeddings
- Alternative: `SimpleKnowledgeBase` for lightweight usage

**Generation Config**:
- Controls LLM behavior (model, temperature, tokens)
- Enables/disables features (RAG, branching depth)
- Passed through entire pipeline

### Output Formats

The system supports multiple output formats:
- **Basic JSON**: Quest structure with scenes and choices
- **Enhanced JSON**: Includes logic, preconditions, effects
- **Unity/Unreal**: Game engine specific formats
- **Python/JS Code**: Executable quest logic
- **Visualization**: Images, 3D layouts, scene graphs

### API Endpoints

Main FastAPI endpoints:
- `POST /generate` - Generate quest from JSON
- `POST /generate/file` - Generate from text file
- `POST /generate/quick` - Quick generation with parameters
- `GET /quest/{quest_id}` - Retrieve generated quest
- `GET /examples` - Get example scenarios

### Knowledge Base Structure

Located in `data/knowledge_base/`:
- `genres/` - JSON files with genre-specific content (currently: cyberpunk.json)
- `templates/` - Quest structure templates
- Files are loaded automatically on initialization
- Can be extended by adding new JSON files

### Important Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models (optional)
- `CHROMA_PERSIST_DIRECTORY` - Vector DB storage (default: ./data/chroma)

Optional:
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `DEFAULT_MODEL` - Default LLM to use (default: gpt-4o-mini)
- `API_HOST`, `API_PORT` - API server settings

## Windows-Specific Notes

When working on Windows, always use:
- `venv\Scripts\python.exe` instead of `python` for running scripts
- `venv\Scripts\pip.exe` for package management
- `venv\Scripts\streamlit.exe` for running Streamlit
- Windows batch files (`.bat`) for convenience scripts

The project includes several batch files for common operations:
- `run_ui.bat` - Launch Streamlit interface with auto-install
- `run_all.bat` - Run both API and UI in separate windows
- `start_api.bat` - Start FastAPI server
- `start_ui.bat` - Alternative UI launcher
- `run_api_safe.bat` - Safe API startup

## Streamlit UI Features

The Streamlit interface (`streamlit_app.py`) provides:
- Quest generation with real-time progress tracking
- Save/load functionality for quests
- Visualization of generated scenes
- Export options for different formats
- Session management for multiple quests

## File Structure for Generated Quests

Generated quests are saved in `saved_quests/` with the following structure:
- `{quest_name}_{timestamp}/`
  - `quest.json` - Basic quest structure
  - `integrated_quest.json` - Enhanced quest with logic
  - `quest_logic.json` - Separate logic file
  - `quest_logic.py` - Executable Python code
  - `visualization_meta.json` - Visualization metadata
  - `{quest_title}_{timestamp}/` - Scene visualizations
    - `quest_map.json` - Overall quest map
    - `scene_{id}/` - Per-scene assets
      - `composite.png` - Combined visualization
      - `layout.json` - 3D layout data
      - `view_0.png` - Primary view

## Common Development Patterns

### Adding New Generators
1. Create module in `src/modules/`
2. Inherit from base classes when appropriate
3. Register in `QuestGenerator` or `IntegratedQuestGenerator`
4. Update `GenerationConfig` if new options needed

### Extending Knowledge Base
1. Add JSON files to `data/knowledge_base/genres/`
2. Follow existing schema for genre data
3. Run knowledge base initialization to create embeddings

### Working with Async Code
Many modules support both sync and async operation:
- Use `async def generate()` for async methods
- Provide sync wrappers when needed
- Handle both in integration points