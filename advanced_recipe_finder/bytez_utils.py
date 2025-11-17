#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bytez AI Utilities - Testing, Examples, and Verification
Complete utility suite for Bytez image generation
"""
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

def test_bytez_import():
    """Test if Bytez can be imported"""
    print("Testing Bytez import...")
    try:
        from bytez import Bytez
        print("✅ Bytez imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Bytez: {e}")
        print("   Install with: pip install bytez")
        return False


def test_bytez_generator_import():
    """Test if BytezImageGenerator can be imported"""
    print("\nTesting BytezImageGenerator import...")
    try:
        from bytez_image_generator import BytezImageGenerator
        print("✅ BytezImageGenerator imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import BytezImageGenerator: {e}")
        return False


def test_generator_initialization():
    """Test if generator can be initialized"""
    print("\nTesting generator initialization...")
    try:
        from bytez_image_generator import BytezImageGenerator
        
        generator = BytezImageGenerator()
        
        if generator.is_available():
            print("✅ Generator initialized successfully")
            print(f"   Using API key: {generator.api_key[:10]}...")
            return True
        else:
            print("⚠️  Generator initialized but not available")
            print("   Check if Bytez is installed and API key is valid")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize generator: {e}")
        return False


def test_prompt_building():
    """Test prompt building functionality"""
    print("\nTesting prompt building...")
    try:
        from bytez_image_generator import BytezImageGenerator
        
        generator = BytezImageGenerator()
        
        prompt1 = generator.build_enhanced_prompt("chocolate cake")
        print(f"   Prompt 1: {prompt1}")
        
        prompt2 = generator.build_enhanced_prompt(
            "chocolate cake",
            "chocolate, flour, eggs, sugar"
        )
        print(f"   Prompt 2: {prompt2}")
        
        print("✅ Prompt building works correctly")
        return True
    except Exception as e:
        print(f"❌ Prompt building failed: {e}")
        return False


def test_image_generation():
    """Test actual image generation (requires valid API key)"""
    print("\nTesting image generation...")
    print("⚠️  This will make an actual API call")
    
    response = input("Do you want to test image generation? (y/n): ")
    if response.lower() != 'y':
        print("⏭️  Skipping image generation test")
        return None
    
    try:
        from bytez_image_generator import BytezImageGenerator
        
        generator = BytezImageGenerator()
        
        if not generator.is_available():
            print("❌ Generator not available - check API key")
            return False
        
        print("   Generating image for 'chocolate cake'...")
        result = generator.generate_image(
            description="chocolate cake with strawberries",
            ingredients="chocolate, flour, eggs, strawberries"
        )
        
        if result['success']:
            print(f"✅ Image generated successfully!")
            print(f"   Path: {result['image_path']}")
            print(f"   Prompt: {result['prompt']}")
            
            if os.path.exists(result['image_path']):
                size = os.path.getsize(result['image_path'])
                print(f"   File size: {size / 1024:.2f} KB")
            
            return True
        else:
            print(f"❌ Image generation failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Image generation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("Bytez Image Generation Test Suite")
    print("=" * 60)
    
    results = {
        "Bytez Import": test_bytez_import(),
        "Generator Import": test_bytez_generator_import(),
        "Generator Init": test_generator_initialization(),
        "Prompt Building": test_prompt_building(),
    }
    
    if all(results.values()):
        results["Image Generation"] = test_image_generation()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{test_name:.<30} {status}")
    
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Bytez integration is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def check_gemini_image_references():
    """Check for any remaining Gemini image generation code"""
    print("🔍 Checking for Gemini image references...")
    
    files_to_check = ['app.py', 'bytez_image_generator.py']
    
    gemini_image_terms = [
        'GEMINI_IMAGE_MODEL',
        'gemini-2.0-flash-exp',
        'responseModalities',
        'Image generated by Gemini AI',
        'Gemini 2.0 Flash Exp'
    ]
    
    found_issues = []
    
    for filename in files_to_check:
        if not os.path.exists(filename):
            continue
            
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for term in gemini_image_terms:
            if term in content and 'DEPRECATED' not in content[:500]:
                found_issues.append(f"Found '{term}' in {filename}")
    
    if found_issues:
        print("❌ Found Gemini image references:")
        for issue in found_issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ No Gemini image references found (clean!)")
        return True


def check_bytez_implementation():
    """Verify Bytez is properly implemented"""
    print("\n🔍 Checking Bytez implementation...")
    
    checks = []
    
    if os.path.exists('bytez_image_generator.py'):
        checks.append(("bytez_image_generator.py exists", True))
    else:
        checks.append(("bytez_image_generator.py exists", False))
    
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks.append(("BytezImageGenerator import", 'BytezImageGenerator' in content))
        checks.append(("bytez_generator initialized", 'bytez_generator = BytezImageGenerator' in content))
        checks.append(("BYTEZ_API_KEY configured", 'BYTEZ_API_KEY' in content))
        checks.append(("bytez_generator.generate_image used", 'bytez_generator.generate_image' in content))
    
    if os.path.exists('../requirements.txt'):
        with open('../requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        checks.append(("bytez in requirements.txt", 'bytez' in content))
    
    all_passed = all(passed for _, passed in checks)
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
    
    return all_passed


def check_image_generation_type():
    """Verify what's handling image generation"""
    print("\n🔍 Checking image generation handler...")
    
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '@app.route(\'/generate_recipe_image\'' in content:
            if 'bytez_generator.generate_image' in content:
                print("✅ /generate_recipe_image uses Bytez")
                return True
            else:
                print("❌ /generate_recipe_image doesn't use Bytez")
                return False
    
    print("⚠️  Could not verify endpoint")
    return False


def check_config_separation():
    """Verify Gemini is only for text, Bytez for images"""
    print("\n🔍 Checking API configuration...")
    
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_gemini_text = 'GEMINI_TEXT_MODEL' in content
        has_bytez_key = 'BYTEZ_API_KEY' in content
        no_gemini_image = 'GEMINI_IMAGE_MODEL' not in content
        
        print(f"   {'✅' if has_gemini_text else '❌'} Gemini configured for text")
        print(f"   {'✅' if has_bytez_key else '❌'} Bytez configured")
        print(f"   {'✅' if no_gemini_image else '❌'} No GEMINI_IMAGE_MODEL")
        
        return has_gemini_text and has_bytez_key and no_gemini_image
    
    return False


def run_verification():
    """Run all verification checks"""
    print("=" * 60)
    print("Gemini Removal & Bytez Implementation Verification")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    results = {
        "No Gemini Image Code": check_gemini_image_references(),
        "Bytez Implementation": check_bytez_implementation(),
        "Correct Endpoint Handler": check_image_generation_type(),
        "API Separation": check_config_separation(),
    }
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:.<40} {status}")
    
    print("=" * 60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 SUCCESS! All checks passed!")
        print("\nImage Generation Setup:")
        print("  ✅ Gemini removed from image generation")
        print("  ✅ Bytez implementation active")
        print("  ✅ Proper API separation")
        print("\nYou can now:")
        print("  1. Run: python app.py")
        print("  2. Test: curl -X POST http://localhost:5000/generate_recipe_image")
        print("  3. All image generation will use Bytez Photoreal AI")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review the output above.")
        return 1


# ============================================================================
# EXAMPLE FUNCTIONS
# ============================================================================

def example_basic():
    """Basic usage example"""
    print("Example 1: Basic Image Generation")
    print("-" * 50)
    
    from bytez_image_generator import BytezImageGenerator
    
    generator = BytezImageGenerator()
    
    if not generator.is_available():
        print("❌ Bytez not available. Install with: pip install bytez")
        return
    
    result = generator.generate_image(
        description="chocolate cake with strawberries on top",
        ingredients="chocolate, flour, eggs, strawberries, cream"
    )
    
    if result['success']:
        print(f"✅ Success! Image saved to:")
        print(f"   {result['image_path']}")
        print(f"\n   Prompt used: {result['prompt']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_with_logo():
    """Example with logo overlay"""
    print("Example 2: Image Generation with Logo")
    print("-" * 50)
    
    from bytez_image_generator import BytezImageGenerator
    
    generator = BytezImageGenerator()
    
    if not generator.is_available():
        print("❌ Bytez not available")
        return
    
    logo_path = "path/to/your/logo.png"
    
    result = generator.generate_image(
        description="grilled salmon with roasted vegetables",
        ingredients="salmon fillet, broccoli, carrots, olive oil, herbs",
        logo_path=logo_path if os.path.exists(logo_path) else None
    )
    
    if result['success']:
        print(f"✅ Success with logo! Image saved to:")
        print(f"   {result['image_path']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print()


def example_prompt_building():
    """Example of prompt building"""
    print("Example 3: Prompt Building")
    print("-" * 50)
    
    from bytez_image_generator import BytezImageGenerator
    
    generator = BytezImageGenerator()
    
    prompt1 = generator.build_enhanced_prompt("pasta carbonara")
    print(f"Simple: {prompt1}")
    
    prompt2 = generator.build_enhanced_prompt(
        "pasta carbonara",
        "spaghetti, bacon, eggs, parmesan, black pepper"
    )
    print(f"With ingredients: {prompt2}")
    
    prompt3 = generator.build_enhanced_prompt(
        "gourmet pizza with fresh basil and mozzarella",
        "pizza dough, tomato sauce, mozzarella, basil, olive oil"
    )
    print(f"Complex: {prompt3}")
    
    print()


def example_multiple_images():
    """Example generating multiple images"""
    print("Example 4: Generate Multiple Images")
    print("-" * 50)
    
    from bytez_image_generator import BytezImageGenerator
    
    generator = BytezImageGenerator()
    
    if not generator.is_available():
        print("❌ Bytez not available")
        return
    
    dishes = [
        ("chocolate cake", "chocolate, flour, eggs, sugar"),
        ("caesar salad", "romaine lettuce, croutons, parmesan, caesar dressing"),
        ("grilled chicken", "chicken breast, olive oil, herbs, lemon")
    ]
    
    for description, ingredients in dishes:
        print(f"\nGenerating: {description}...")
        result = generator.generate_image(description, ingredients)
        
        if result['success']:
            print(f"✅ Saved to: {result['image_path']}")
        else:
            print(f"❌ Failed: {result['error']}")
    
    print()


def example_placeholder():
    """Example generating placeholder"""
    print("Example 5: Generate Placeholder")
    print("-" * 50)
    
    from bytez_image_generator import BytezImageGenerator
    
    generator = BytezImageGenerator()
    
    placeholder_path = generator.generate_placeholder(
        description="Delicious food image"
    )
    
    print(f"✅ Placeholder created at: {placeholder_path}")
    print()


def run_examples():
    """Run all examples"""
    print("\n" + "=" * 50)
    print("Bytez Image Generation Examples")
    print("=" * 50 + "\n")
    
    example_basic()
    example_prompt_building()
    example_placeholder()
    
    print("\nOptional examples (uncomment in code to run):")
    print("  - example_with_logo()")
    print("  - example_multiple_images()")
    
    print("=" * 50)
    print("Examples completed!")
    print("=" * 50)


# ============================================================================
# MAIN CLI
# ============================================================================

def print_menu():
    """Print interactive menu"""
    print("\n" + "=" * 60)
    print("Bytez AI Utilities - Main Menu")
    print("=" * 60)
    print("\n1. Run Tests (verify installation)")
    print("2. Run Verification (check migration)")
    print("3. Run Examples (see usage)")
    print("4. Quick Test (basic functionality)")
    print("5. Exit")
    print()


def quick_test():
    """Quick test without prompts"""
    print("\n" + "=" * 60)
    print("Quick Test")
    print("=" * 60)
    
    from bytez_image_generator import BytezImageGenerator
    
    try:
        generator = BytezImageGenerator()
        
        if generator.is_available():
            print("✅ Bytez is available and configured")
            print(f"   API Key: {generator.api_key[:10]}...")
            print(f"   Model: Dreamlike Photoreal 2.0")
            
            prompt = generator.build_enhanced_prompt("chocolate cake", "chocolate, flour")
            print(f"\n✅ Prompt building works")
            print(f"   Example: {prompt}")
            
            print("\n✅ All basic checks passed!")
            print("\nTo test image generation:")
            print("  python bytez_utils.py --test")
        else:
            print("❌ Bytez not available")
            print("   Run: pip install bytez")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bytez AI Utilities')
    parser.add_argument('--test', action='store_true', help='Run tests')
    parser.add_argument('--verify', action='store_true', help='Run verification')
    parser.add_argument('--examples', action='store_true', help='Run examples')
    parser.add_argument('--quick', action='store_true', help='Quick test')
    parser.add_argument('--interactive', action='store_true', help='Interactive menu')
    
    args = parser.parse_args()
    
    if args.test:
        return run_tests()
    elif args.verify:
        return run_verification()
    elif args.examples:
        run_examples()
        return 0
    elif args.quick:
        quick_test()
        return 0
    elif args.interactive or len(sys.argv) == 1:
        # Interactive mode
        while True:
            print_menu()
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == '1':
                run_tests()
            elif choice == '2':
                run_verification()
            elif choice == '3':
                run_examples()
            elif choice == '4':
                quick_test()
            elif choice == '5':
                print("\nGoodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-5.")
            
            input("\nPress Enter to continue...")
        
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
