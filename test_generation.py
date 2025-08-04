#!/usr/bin/env python3
"""
Test quest generation functionality
"""
import asyncio
from src.quest_generator import QuestGenerator
from src.core.models import GenerationConfig, ScenarioInput
from loguru import logger

async def test_generation():
    """Test basic quest generation"""
    print("Testing Quest Generation...")
    print("=" * 50)
    
    try:
        # Initialize generator
        generator = QuestGenerator()
        
        # Create test scenario
        scenario = ScenarioInput(
            genre="fantasy",
            hero="Храбрый рыцарь",
            goal="Спасти принцессу из логова дракона"
        )
        
        # Configure generation
        config = GenerationConfig(
            model="gpt-4o-mini",
            temperature=0.8,
            use_rag=False,  # Disable RAG for quick test
            ensure_branching_depth=2
        )
        
        print(f"Genre: {scenario.genre}")
        print(f"Hero: {scenario.hero}")
        print(f"Goal: {scenario.goal}")
        print(f"Model: {config.model}")
        print("=" * 50)
        print("Generating quest...")
        
        # Generate quest
        quest = await generator.generate_async(scenario)
        
        print(f"\nGenerated quest: {quest.title}")
        print(f"Scenes: {len(quest.scenes)}")
        
        # Print first scene
        if quest.scenes:
            first_scene = quest.scenes[0]
            print(f"\nFirst scene ID: {first_scene.scene_id}")
            print(f"Text: {first_scene.text[:200]}...")
            print(f"Choices: {len(first_scene.choices)}")
            
            for i, choice in enumerate(first_scene.choices, 1):
                print(f"  {i}. {choice.text}")
        
        print("\nGeneration test passed!")
        return True
        
    except Exception as e:
        print(f"\nGeneration test failed: {e}")
        logger.exception("Generation test error")
        return False

def main():
    """Run test"""
    success = asyncio.run(test_generation())
    exit(0 if success else 1)

if __name__ == "__main__":
    main()