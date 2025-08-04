#!/usr/bin/env python3
"""
Test initialization of quest generator
"""
import time
from loguru import logger

print("Testing initialization...")

try:
    start = time.time()
    print("1. Importing QuestGenerator...")
    from src.quest_generator import QuestGenerator
    print(f"   [OK] Import successful ({time.time() - start:.2f}s)")
    
    print("2. Creating QuestGenerator instance...")
    start = time.time()
    generator = QuestGenerator()
    print(f"   [OK] Instance created ({time.time() - start:.2f}s)")
    
    print("\nInitialization successful!")
    
except Exception as e:
    print(f"\n[ERROR] Initialization failed: {e}")
    logger.exception("Initialization error")
    raise