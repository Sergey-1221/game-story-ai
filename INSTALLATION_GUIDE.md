# Installation Guide for Game Story AI

## Quick Start

1. **Install the working requirements:**
   ```bash
   pip install -r requirements-working.txt
   ```

2. **Download language models:**
   ```bash
   python -m spacy download ru_core_news_sm
   python -m spacy download en_core_web_sm
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

## Dealing with Installation Issues

### If installation is slow or times out:

Install packages in batches:

```bash
# Core packages first
pip install openai langchain chromadb pydantic python-dotenv tiktoken

# NLP packages
pip install spacy nltk

# API framework
pip install fastapi uvicorn httpx

# Data processing
pip install pandas numpy scipy scikit-learn

# AI/ML packages (these are large)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118  # For CUDA 11.8
# OR for CPU only:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Then the rest
pip install transformers diffusers accelerate
pip install -r requirements-working.txt
```

### Missing Packages

Some packages in the original requirements don't exist on PyPI:

1. **Wave Function Collapse**: Implement your own or use alternatives like:
   ```python
   # Instead of wave-function-collapse, use noise libraries:
   pip install opensimplex
   ```

2. **Stable Diffusion WebUI**: This is a full application. For image generation in your code:
   ```python
   # Use diffusers library instead (already included)
   from diffusers import StableDiffusionPipeline
   ```

3. **Game Engine APIs**: Install through the game engines themselves:
   - Unreal Engine: Use the official Python plugin
   - Unity: Use UnityPy or Python for Unity

## Minimal Installation

For just the core quest generation functionality:

```bash
pip install -r requirements-minimal.txt
```

## Troubleshooting

1. **Memory errors during installation**: Install packages one by one
2. **Version conflicts**: Create a fresh virtual environment
3. **Missing C++ compiler**: Some packages need Visual Studio Build Tools on Windows
4. **GPU support**: Install CUDA toolkit for torch GPU support

## Verifying Installation

Test your installation:

```python
python -c "import openai, langchain, chromadb, spacy; print('Core packages installed successfully')"
```