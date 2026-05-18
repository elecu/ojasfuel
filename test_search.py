#!/usr/bin/env python3
"""
SMAEUK - Test basic flow
Search product by name → Extract ingredients & nutrition → Classify
"""

import sys
import json
from datetime import datetime

# Import classifier
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')
try:
    from src.classifier import ProductClassifier
except ImportError:
    print("❌ Classifier not found")
    sys.exit(1)

try:
    import openfoodfacts
except ImportError:
    print("❌ openfoodfacts not installed: pip install openfoodfacts")
    sys.exit(1)


def search_and_classify(product_name):
    """Search product by name and classify"""
    
    print("\n" + "="*80)
    print("🔍 SMAEUK - Product Search & Classify")
    print("="*80 + "\n")
    
    print(f"🔎 Searching for: '{product_name}'\n")
    
    # Initialize API
    api = openfoodfacts.API(user_agent="SMAEUK/1.0")
    
    # Search
    try:
        results = api.product.text_search(product_name, page_size=5)
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None
    
    products = results.get('products', [])
    
    if not products:
        print(f"❌ No products found for '{product_name}'")
        return None
    
    print(f"✅ Found {len(products)} products\n")
    
    # Process first product
    product = products[0]
    
    product_name = product.get('product_name', 'Unknown')
    product_id = product.get('id', product.get('code', 'N/A'))
    brand = product.get('brands', 'N/A')
    ingredients = product.get('ingredients_text', 'N/A')
    
    print("-" * 80)
    print("📦 PRODUCT INFO")
    print("-" * 80 + "\n")
    
    print(f"Name: {product_name}")
    print(f"Brand: {brand}")
    print(f"ID: {product_id}\n")
    
    # Extract nutrition
    print("-" * 80)
    print("🔬 NUTRITION FACTS (per 100g)")
    print("-" * 80 + "\n")
    
    nutrition = {}
    
    # All possible nutrition fields
    nutrition_fields = {
        'Energy (kcal)': 'energy_100g',
        'Energy (kJ)': 'energy-kj_100g',
        'Protein (g)': 'proteins_100g',
        'Fat (g)': 'fat_100g',
        'Saturated Fat (g)': 'saturated-fat_100g',
        'Carbohydrates (g)': 'carbohydrates_100g',
        'Sugars (g)': 'sugars_100g',
        'Fiber (g)': 'fiber_100g',
        'Sodium (mg)': 'sodium_100g',
        'Sodium (g)': 'salt_100g',
        'Potassium (mg)': 'potassium_100g',
        'Calcium (mg)': 'calcium_100g',
        'Iron (mg)': 'iron_100g',
        'Magnesium (mg)': 'magnesium_100g',
        'Phosphorus (mg)': 'phosphorus_100g',
        'Zinc (mg)': 'zinc_100g',
        'Manganese (mg)': 'manganese_100g',
        'Copper (mg)': 'copper_100g',
        'Selenium (µg)': 'selenium_100g',
        'Iodine (µg)': 'iodine_100g',
        'Vitamin A (µg)': 'vitamin-a_100g',
        'Vitamin B1 (mg)': 'vitamin-b1_100g',
        'Vitamin B2 (mg)': 'vitamin-b2_100g',
        'Vitamin B3 (mg)': 'vitamin-b3_100g',
        'Vitamin B6 (mg)': 'vitamin-b6_100g',
        'Vitamin B9 (µg)': 'vitamin-b9_100g',
        'Vitamin B12 (µg)': 'vitamin-b12_100g',
        'Vitamin C (mg)': 'vitamin-c_100g',
        'Vitamin D (µg)': 'vitamin-d_100g',
        'Vitamin E (mg)': 'vitamin-e_100g',
        'Vitamin K (µg)': 'vitamin-k_100g',
        'Cholesterol (mg)': 'cholesterol_100g',
        'Alcohol (g)': 'alcohol_100g',
        'Caffeine (mg)': 'caffeine_100g',
    }
    
    found_nutrition = 0
    for display_name, field_name in nutrition_fields.items():
        value = product.get(field_name)
        if value is not None:
            nutrition[field_name] = value
            print(f"  {display_name}: {value}")
            found_nutrition += 1
    
    if found_nutrition == 0:
        print("  ⚠️  No nutrition data available")
    else:
        print(f"\n✅ Found {found_nutrition} nutrition fields\n")
    
    # Extract ingredients
    print("-" * 80)
    print("📋 INGREDIENTS")
    print("-" * 80 + "\n")
    
    if ingredients and ingredients != 'N/A':
        print(f"{ingredients}\n")
    else:
        print("⚠️  No ingredients data\n")
    
    # Classify
    print("-" * 80)
    print("🤖 VEGAN/VEGETARIAN CLASSIFICATION")
    print("-" * 80 + "\n")
    
    classifier = ProductClassifier()
    
    if ingredients and ingredients != 'N/A':
        classification = classifier.classify(ingredients)
        
        # Display results
        if classification['is_vegan']:
            emoji = "✨"
            status = "VEGAN"
        elif classification['is_vegetarian']:
            emoji = "🥛"
            status = "VEGETARIAN"
        else:
            emoji = "❌"
            status = "NOT VEGETARIAN"
        
        print(f"{emoji} Status: {status}")
        print(f"   Confidence: {classification['confidence']*100:.1f}%")
        print(f"   Reason: {classification['reason']}\n")
        
        if classification['animal_products_found']:
            print(f"   🐟 Animal products: {', '.join(classification['animal_products_found'])}\n")
        
        if classification['dairy_or_eggs_found']:
            print(f"   🥚 Dairy/Eggs: {', '.join(classification['dairy_or_eggs_found'])}\n")
    else:
        print("❌ Cannot classify without ingredients")
        classification = None
    
    # Save result
    print("-" * 80)
    print("💾 SAVING RESULT")
    print("-" * 80 + "\n")
    
    result = {
        'search_time': datetime.now().isoformat(),
        'product': {
            'name': product_name,
            'brand': brand,
            'id': product_id,
            'url': f'https://world.openfoodfacts.org/product/{product_id}'
        },
        'ingredients': ingredients,
        'nutrition': nutrition,
        'classification': classification,
    }
    
    # Save JSON
    output_file = f"search_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Saved to: {output_file}\n")
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_search.py '<product_name>'")
        print("\nExamples:")
        print("  python test_search.py 'bread'")
        print("  python test_search.py 'vegan chocolate'")
        print("  python test_search.py 'almond milk'")
        sys.exit(1)
    
    product_name = " ".join(sys.argv[1:])
    result = search_and_classify(product_name)
    
    if result:
        print("="*80)
        print("✅ SUCCESS!")
        print("="*80 + "\n")
    else:
        print("❌ FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
