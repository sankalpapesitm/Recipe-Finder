#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for Bytez image generation
Run this to diagnose image generation issues
"""
import sys
import os

# Add the advanced_recipe_finder directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'advanced_recipe_finder'))

from bytez_image_generator import BytezImageGenerator
from config_backup import Config

def test_bytez_generation():
    """Test Bytez image generation with detailed logging"""
    print("=" * 60)
    print("Testing Bytez Image Generation")
    print("=" * 60)
    
    # Initialize generator
    print("\n1. Initializing Bytez generator...")
    generator = BytezImageGenerator(api_key=Config.BYTEZ_API_KEY)
    
    if not generator.is_available():
        print("❌ FAILED: Bytez not available!")
        print("   Make sure 'bytez' package is installed: pip install bytez")
        return False
    
    print("✓ Bytez initialized successfully")
    
    # Test simple generation
    print("\n2. Testing image generation...")
    print("   Description: Pancakes")
    print("   Ingredients: flour, eggs, milk")
    
    result = generator.generate_image(
        description="Pancakes",
        ingredients="flour, eggs, milk"
    )
    
    print("\n3. Result:")
    print(f"   Success: {result['success']}")
    
    if result['success']:
        print(f"   ✓ Image Path: {result['image_path']}")
        print(f"   ✓ Prompt: {result['prompt']}")
        
        # Verify file exists
        if os.path.exists(result['image_path']):
            file_size = os.path.getsize(result['image_path'])
            print(f"   ✓ File exists: {file_size} bytes")
            
            # Try to open with PIL
            try:
                from PIL import Image
                img = Image.open(result['image_path'])
                print(f"   ✓ Image valid: {img.size[0]}x{img.size[1]} pixels, {img.format}")
                return True
            except Exception as e:
                print(f"   ❌ Image invalid: {e}")
                return False
        else:
            print(f"   ❌ File does not exist!")
            return False
    else:
        print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    print("\nBytez Image Generation Test")
    print("=" * 60)
    
    try:
        success = test_bytez_generation()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ TEST PASSED - Image generation working!")
        else:
            print("❌ TEST FAILED - Check errors above")
        print("=" * 60)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
