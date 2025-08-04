# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered game story generator that creates interactive quests and storylines in JSON format from text descriptions. The system uses LLMs, RAG, and advanced AI techniques for narrative generation, logic structuring, and scene visualization.

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
cp .env.example .env
# Then edit .env with actual API keys
```

### Running the System
```bash
# Basic quest generation
python src/quest_generator.py

# Run API server
uvicorn src.api.main:app --reload --port 8000

# Run demos
python examples/story2game_scenecraft_demo.py
python examples/hybrid_pipeline_demo.py

# CLI interface (if main.py exists)
python main.py --input scenario.txt --output quest.json
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
- Uses ChromaDB for vector storage
- Caches genre-specific content
- Must be initialized with embeddings

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
- `genres/` - JSON files with genre-specific content
- `templates/` - Quest structure templates
- Files are loaded automatically on initialization
- Can be extended by adding new JSON files

### Important Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models (optional)
- `CHROMA_PERSIST_DIRECTORY` - Vector DB storage

Optional:
- `LOG_LEVEL` - Logging verbosity
- `DEFAULT_MODEL` - Default LLM to use
- `API_HOST`, `API_PORT` - API server settings