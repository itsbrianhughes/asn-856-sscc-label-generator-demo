#!/usr/bin/env python3
"""
Cartonization Demo
==================
Demonstrates the cartonization engine with sample orders.

Usage:
    python examples/demo_cartonization.py

Author: Integration Engineering Team
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.cartonization.config import CartonizationConfig
import json


def print_separator(title: str = ""):
    """Print a visual separator."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"{'=' * 80}\n")


def demo_simple_order():
    """Demonstrate cartonization of a simple order."""
    print_separator("Demo 1: Simple Order (Single Carton)")

    # Load sample order
    order_path = Path("examples/sample_orders/order_001.json")
    print(f"Loading order from: {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    print(f"Order ID: {order.order_id}")
    print(f"Purchase Order: {order.purchase_order}")
    print(f"Ship Date: {order.ship_date}")
    print(f"Items: {len(order.items)} line items")

    # Create cartonization engine
    engine = CartonizationEngine()

    # Process order
    print("\nCartonizing order...")
    result = engine.cartonize_order(order)

    # Display results
    shipment = result.shipment
    print(f"\n✅ Cartonization complete!")
    print(f"Shipment ID: {shipment.shipment_id}")
    print(f"Total Cartons: {shipment.total_cartons}")
    print(f"Total Weight: {shipment.total_weight:.2f} lbs")

    print(f"\nCarton Details:")
    for carton in shipment.cartons:
        print(f"\n  Carton {carton.sequence_number} ({carton.carton_id}):")
        print(f"    SSCC: {carton.sscc}")
        print(f"    Items: {carton.get_total_units()} units")
        print(f"    Weight: {carton.calculate_weight():.2f} lbs")
        print(f"    Contents:")
        for item in carton.items:
            print(f"      - {item.sku}: {item.quantity} {item.uom} ({item.description})")


def demo_multi_carton_order():
    """Demonstrate cartonization of an order requiring multiple cartons."""
    print_separator("Demo 2: Multi-Carton Order")

    # Load sample order
    order_path = Path("examples/sample_orders/order_002_multi_carton.json")
    print(f"Loading order from: {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    print(f"Order ID: {order.order_id}")
    print(f"Purchase Order: {order.purchase_order}")
    print(f"Items: {len(order.items)} line items")

    # Calculate total units
    total_units = sum(item.quantity for item in order.items)
    print(f"Total Units: {total_units}")

    # Create cartonization engine with custom config
    config = CartonizationConfig(
        max_items_per_carton=30,  # Lower limit to force multiple cartons
        max_weight_per_carton=75.0
    )
    engine = CartonizationEngine(config)

    # Process order
    print("\nCartonizing order...")
    result = engine.cartonize_order(order)

    # Display results
    shipment = result.shipment
    print(f"\n✅ Cartonization complete!")
    print(f"Shipment ID: {shipment.shipment_id}")
    print(f"Total Cartons: {shipment.total_cartons}")
    print(f"Total Weight: {shipment.total_weight:.2f} lbs")

    print(f"\nCarton Summary:")
    for carton in shipment.cartons:
        print(f"  Carton {carton.sequence_number}: {carton.get_total_units()} units, "
              f"{carton.calculate_weight():.2f} lbs, SSCC: {carton.sscc}")


def demo_sscc_validation():
    """Demonstrate SSCC generation and validation."""
    print_separator("Demo 3: SSCC Generation & Validation")

    from src.sscc.generator import SSCCGenerator, create_sscc_generator

    # Create generator
    print("Creating SSCC generator with company prefix: 0614141")
    generator = create_sscc_generator(
        company_prefix="0614141",
        serial_start=1
    )

    # Generate 5 SSCCs
    print("\nGenerating 5 SSCCs:")
    for i in range(5):
        sscc = generator.generate_next()
        full_sscc = sscc.get_full_sscc()
        formatted = sscc.get_formatted_sscc()
        is_valid = SSCCGenerator.validate_sscc(sscc)

        print(f"\n  SSCC #{i+1}:")
        print(f"    Full:      {full_sscc}")
        print(f"    Formatted: {formatted}")
        print(f"    GS1 AI:    {sscc.get_gs1_application_identifier()}")
        print(f"    Valid:     {'✅' if is_valid else '❌'}")


def demo_packing_strategies():
    """Demonstrate different packing strategies."""
    print_separator("Demo 4: Packing Strategies")

    from src.models.input_models import OrderLineItem, Address
    from datetime import date

    # Create test order
    order = OrderInput(
        order_id="DEMO-STRAT-001",
        purchase_order="PO-STRAT-001",
        ship_date=date(2025, 12, 15),
        ship_from=Address(
            name="Demo Warehouse",
            address_line1="123 Demo St",
            city="Dallas",
            state="TX",
            postal_code="75201"
        ),
        ship_to=Address(
            name="Demo Store",
            address_line1="456 Demo Ave",
            city="Austin",
            state="TX",
            postal_code="78701"
        ),
        items=[
            OrderLineItem(
                line_number=1,
                sku="SKU-LIGHT",
                description="Light Item",
                quantity=20,
                unit_weight=0.5
            ),
            OrderLineItem(
                line_number=2,
                sku="SKU-HEAVY",
                description="Heavy Item",
                quantity=20,
                unit_weight=5.0
            )
        ]
    )

    # Strategy 1: Mixed cartons
    print("Strategy 1: Mixed Cartons (default)")
    config1 = CartonizationConfig(
        max_items_per_carton=30,
        single_item_cartons=False
    )
    engine1 = CartonizationEngine(config1)
    result1 = engine1.cartonize_order(order)
    print(f"  Result: {len(result1.shipment.cartons)} carton(s)")
    for carton in result1.shipment.cartons:
        skus = [item.sku for item in carton.items]
        print(f"    Carton {carton.sequence_number}: {', '.join(skus)}")

    # Strategy 2: Separate cartons per SKU
    print("\nStrategy 2: Single-Item Cartons (separate SKUs)")
    config2 = CartonizationConfig(
        max_items_per_carton=30,
        single_item_cartons=True
    )
    engine2 = CartonizationEngine(config2)
    result2 = engine2.cartonize_order(order)
    print(f"  Result: {len(result2.shipment.cartons)} carton(s)")
    for carton in result2.shipment.cartons:
        skus = [item.sku for item in carton.items]
        print(f"    Carton {carton.sequence_number}: {', '.join(skus)}")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  CARTONIZATION ENGINE DEMO")
    print("  Project 3: ASN 856 + SSCC Label Generator")
    print("=" * 80)

    try:
        demo_simple_order()
        demo_multi_carton_order()
        demo_sscc_validation()
        demo_packing_strategies()

        print_separator("All Demos Complete!")
        print("✅ Cartonization engine is working correctly")
        print("\nNext steps:")
        print("  - PART 3: Build EDI 856 ASN generator")
        print("  - PART 4: Advanced SSCC features")
        print("  - PART 5: Label rendering with barcodes")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Sample order file not found")
        print(f"   {e}")
        print(f"\n   Make sure you're running from the project root directory:")
        print(f"   python examples/demo_cartonization.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
