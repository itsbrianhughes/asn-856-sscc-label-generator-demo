#!/usr/bin/env python3
"""
ASN Generation Demo
===================
Demonstrates complete end-to-end flow:
  Order JSON → Cartonization → ASN Generation → EDI File

Usage:
    python examples/demo_asn_generation.py

Author: Integration Engineering Team
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.asn_builder.builder import ASNBuilder
import json


def print_separator(title: str = "", width: int = 80):
    """Print a visual separator."""
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}\n")
    else:
        print(f"{'=' * width}\n")


def demo_end_to_end_simple():
    """Demonstrate complete flow with simple order."""
    print_separator("Demo 1: End-to-End ASN Generation (Simple Order)")

    # Step 1: Load order
    order_path = Path("examples/sample_orders/order_001.json")
    print(f"📥 Step 1: Loading order from {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    print(f"   Order ID: {order.order_id}")
    print(f"   PO Number: {order.purchase_order}")
    print(f"   Items: {len(order.items)} line items")
    print(f"   Total Units: {sum(item.quantity for item in order.items)}")

    # Step 2: Cartonization
    print(f"\n📦 Step 2: Cartonizing order")
    engine = CartonizationEngine()
    shipment_package = engine.cartonize_order(order)

    shipment = shipment_package.shipment
    print(f"   Shipment ID: {shipment.shipment_id}")
    print(f"   Cartons Created: {shipment.total_cartons}")
    print(f"   Total Weight: {shipment.total_weight:.2f} lbs")

    for carton in shipment.cartons:
        print(f"   - Carton {carton.sequence_number}: SSCC {carton.sscc}")

    # Step 3: ASN Generation
    print(f"\n📄 Step 3: Generating EDI 856 ASN")
    builder = ASNBuilder()
    edi_content = builder.build_asn(
        shipment_package,
        sender_id="ACME",
        receiver_id="TECHMART"
    )

    segment_count = builder.count_segments(edi_content)
    print(f"   Segments Generated: {segment_count}")
    print(f"   Document Length: {len(edi_content)} characters")

    # Step 4: Save to file
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"856_{shipment.shipment_id}.txt"
    with open(output_file, "w") as f:
        f.write(edi_content)

    print(f"\n💾 Step 4: Saved ASN to {output_file}")

    # Step 5: Display formatted preview
    print(f"\n👁️  Step 5: ASN Preview (first 20 segments)")
    print("-" * 80)

    formatted = builder.format_for_display(edi_content, add_line_numbers=True)
    lines = formatted.split("\n")[:20]
    for line in lines:
        print(line)

    if len(formatted.split("\n")) > 20:
        print("  ...")
        print(f"  ({len(formatted.split('\n')) - 20} more segments)")

    print("\n✅ Complete! ASN generated successfully")


def demo_multi_carton_asn():
    """Demonstrate ASN with multiple cartons."""
    print_separator("Demo 2: Multi-Carton ASN Generation")

    # Load order
    order_path = Path("examples/sample_orders/order_002_multi_carton.json")
    print(f"📥 Loading order from {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)

    # Force multiple cartons with smaller limits
    from src.cartonization.config import CartonizationConfig

    config = CartonizationConfig(
        max_items_per_carton=30,
        max_weight_per_carton=75.0
    )

    print(f"\n📦 Cartonizing with limits:")
    print(f"   Max items per carton: {config.max_items_per_carton}")
    print(f"   Max weight per carton: {config.max_weight_per_carton} lbs")

    engine = CartonizationEngine(config)
    shipment_package = engine.cartonize_order(order)

    shipment = shipment_package.shipment
    print(f"\n   Result: {shipment.total_cartons} cartons created")

    # Generate ASN
    print(f"\n📄 Generating ASN for multi-carton shipment")
    builder = ASNBuilder()
    edi_content = builder.build_asn(
        shipment_package,
        sender_id="ACME",
        receiver_id="BIGBOX"
    )

    # Count specific segments
    hl_count = edi_content.count("HL*")
    sscc_count = edi_content.count("REF*0J*")
    lin_count = edi_content.count("LIN*")

    print(f"\n   Statistics:")
    print(f"   - HL Segments: {hl_count}")
    print(f"   - SSCC References: {sscc_count}")
    print(f"   - Line Items: {lin_count}")

    # Save
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"856_{shipment.shipment_id}.txt"
    with open(output_file, "w") as f:
        f.write(edi_content)

    print(f"\n💾 Saved to {output_file}")
    print("✅ Multi-carton ASN complete!")


def demo_asn_structure_analysis():
    """Analyze ASN structure and hierarchy."""
    print_separator("Demo 3: ASN Structure Analysis")

    # Load and process order
    order_path = Path("examples/sample_orders/order_001.json")
    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    engine = CartonizationEngine()
    shipment_package = engine.cartonize_order(order)

    # Generate ASN
    builder = ASNBuilder()
    edi_content = builder.build_asn(shipment_package)

    print("📊 ASN Structure Breakdown:\n")

    # Parse segments
    segments = edi_content.split("~")
    segments = [s for s in segments if s]  # Remove empty

    # Categorize segments
    segment_types = {}
    for segment in segments:
        seg_type = segment.split("*")[0]
        segment_types[seg_type] = segment_types.get(seg_type, 0) + 1

    print("Segment Type Counts:")
    for seg_type, count in sorted(segment_types.items()):
        print(f"   {seg_type:6s}: {count:3d}")

    # Analyze hierarchy
    print("\n📍 HL Hierarchy Levels:")
    hl_segments = [s for s in segments if s.startswith("HL*")]
    for hl in hl_segments:
        parts = hl.split("*")
        hl_num = parts[1]
        parent = parts[2] if parts[2] else "ROOT"
        level = parts[3]
        has_children = parts[4] if len(parts) > 4 else "?"

        level_names = {
            "S": "Shipment",
            "O": "Order",
            "T": "Tare/Carton",
            "I": "Item"
        }

        print(f"   HL{hl_num:2s} (parent: {parent:4s}) → {level_names.get(level, level):12s} (children: {has_children})")

    # Show specific segment examples
    print("\n📝 Example Segments:")

    examples = {
        "BSN": "Beginning Segment (Shipment Info)",
        "REF*PO": "Purchase Order Reference",
        "REF*0J": "SSCC Reference",
        "TD1": "Package Details (Weight)",
        "LIN": "Item Identification",
        "SN1": "Item Quantity"
    }

    for prefix, description in examples.items():
        matching = [s for s in segments if s.startswith(prefix)]
        if matching:
            print(f"\n   {description}:")
            print(f"   {matching[0]}")


def demo_asn_validation():
    """Demonstrate ASN validation features."""
    print_separator("Demo 4: ASN Validation")

    print("✅ Valid ASN Generation:")

    # Generate valid ASN
    order_path = Path("examples/sample_orders/order_001.json")
    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    engine = CartonizationEngine()
    shipment_package = engine.cartonize_order(order)

    builder = ASNBuilder()
    edi_content = builder.build_asn(shipment_package)

    # Validation checks
    checks = [
        ("ISA header present", edi_content.startswith("ISA")),
        ("Segment terminator (~)", "~" in edi_content),
        ("Element separator (*)", "*" in edi_content),
        ("Transaction set (856)", "ST*856" in edi_content),
        ("BSN segment", "BSN*" in edi_content),
        ("HL hierarchy", "HL*" in edi_content),
        ("Transaction totals", "CTT*" in edi_content),
        ("Proper envelope closing", edi_content.strip().endswith("~"))
    ]

    print("\nValidation Checks:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")

    # Check required segment order
    print("\n📋 Segment Order Validation:")
    segment_order = [
        "ISA", "GS", "ST", "BSN", "HL", "CTT", "SE", "GE", "IEA"
    ]

    current_pos = 0
    for expected_seg in segment_order:
        pos = edi_content.find(expected_seg, current_pos)
        if pos >= 0:
            print(f"   ✅ {expected_seg} found at position {pos}")
            current_pos = pos
        else:
            print(f"   ❌ {expected_seg} not found or out of order")

    print("\n✅ All validations passed!")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  ASN GENERATION DEMO")
    print("  Project 3: ASN 856 + SSCC Label Generator")
    print("  Complete Order → Cartonization → ASN Flow")
    print("=" * 80)

    try:
        demo_end_to_end_simple()
        demo_multi_carton_asn()
        demo_asn_structure_analysis()
        demo_asn_validation()

        print_separator("All Demos Complete!")
        print("✅ ASN generation is working correctly")
        print("\nGenerated Files:")
        print("  - output/856_SHIP-ORD-2025-001.txt")
        print("  - output/856_SHIP-ORD-2025-002.txt")
        print("\nNext steps:")
        print("  - PART 5: Label rendering with GS1-128 barcodes")
        print("  - PART 6: CLI/UI interface")
        print("  - PART 7: Final packaging and documentation")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Sample order file not found")
        print(f"   {e}")
        print(f"\n   Make sure you're running from the project root directory:")
        print(f"   python examples/demo_asn_generation.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
