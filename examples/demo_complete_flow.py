#!/usr/bin/env python3
"""
Complete Flow Demo
==================
Demonstrates complete end-to-end flow:
  Order JSON → Cartonization → ASN Generation → Label Rendering

Usage:
    python examples/demo_complete_flow.py

Author: Integration Engineering Team
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.asn_builder.builder import ASNBuilder
from src.label_generator.builder import LabelBuilder
from src.models.label_models import LabelConfig
import json


def print_separator(title: str = "", width: int = 80):
    """Print a visual separator."""
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}\n")
    else:
        print(f"{'=' * width}\n")


def demo_complete_pipeline():
    """Demonstrate complete order processing pipeline."""
    print_separator("COMPLETE ORDER PROCESSING PIPELINE")

    # Step 1: Load Order
    print("📥 STEP 1: Load Order")
    print("-" * 80)

    order_path = Path("examples/sample_orders/order_001.json")
    print(f"Loading: {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    print(f"✅ Order Loaded:")
    print(f"   Order ID: {order.order_id}")
    print(f"   PO Number: {order.purchase_order}")
    print(f"   Items: {len(order.items)} line items")
    print(f"   Total Units: {sum(item.quantity for item in order.items)}")
    print(f"   Ship From: {order.ship_from.name}, {order.ship_from.city}, {order.ship_from.state}")
    print(f"   Ship To: {order.ship_to.name}, {order.ship_to.city}, {order.ship_to.state}")

    # Step 2: Cartonization
    print("\n📦 STEP 2: Cartonization")
    print("-" * 80)

    print("Running cartonization engine...")
    engine = CartonizationEngine()
    shipment_package = engine.cartonize_order(order)

    shipment = shipment_package.shipment
    print(f"✅ Cartonization Complete:")
    print(f"   Shipment ID: {shipment.shipment_id}")
    print(f"   Cartons Created: {shipment.total_cartons}")
    print(f"   Total Weight: {shipment.total_weight:.2f} lbs")
    print(f"\n   Carton Details:")
    for carton in shipment.cartons:
        print(f"   - Carton {carton.sequence_number}: SSCC {carton.sscc}, "
              f"{carton.get_total_units()} units, {carton.calculate_weight():.2f} lbs")

    # Step 3: ASN Generation
    print("\n📄 STEP 3: ASN Generation (EDI 856)")
    print("-" * 80)

    print("Generating EDI 856 ASN...")
    asn_builder = ASNBuilder()
    edi_content = asn_builder.build_asn(
        shipment_package,
        sender_id="ACME",
        receiver_id="TECHMART"
    )

    # Save ASN
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    asn_file = output_dir / f"856_{shipment.shipment_id}.txt"
    with open(asn_file, "w") as f:
        f.write(edi_content)

    segment_count = asn_builder.count_segments(edi_content)
    print(f"✅ ASN Generated:")
    print(f"   File: {asn_file}")
    print(f"   Segments: {segment_count}")
    print(f"   Size: {len(edi_content)} bytes")

    # Show preview
    print(f"\n   Preview (first 10 segments):")
    formatted = asn_builder.format_for_display(edi_content, add_line_numbers=False)
    lines = formatted.split("\n")[:10]
    for line in lines:
        print(f"   {line}")
    print(f"   ... ({segment_count - 10} more segments)")

    # Step 4: Label Generation
    print("\n🏷️  STEP 4: Shipping Label Generation")
    print("-" * 80)

    print("Generating GS1-128 shipping labels...")

    try:
        # Configure labels
        label_config = LabelConfig(
            show_contents=True,
            max_contents_lines=5
        )

        label_builder = LabelBuilder(label_config)

        # Create labels directory
        labels_dir = output_dir / "labels"
        labels_dir.mkdir(exist_ok=True)

        # Render labels
        label_batch = label_builder.render_labels_for_shipment(
            shipment_package,
            str(labels_dir)
        )

        print(f"✅ Labels Generated:")
        print(f"   Directory: {labels_dir}")
        print(f"   Total Labels: {label_batch.total_labels}")
        print(f"\n   Label Files:")
        for label_output in label_batch.labels:
            print(f"   - {Path(label_output.file_path).name}")
            print(f"     SSCC: {label_output.sscc}")

    except ImportError as e:
        print(f"⚠️  Label generation skipped: {e}")
        print(f"   Install dependencies: pip install reportlab python-barcode")

    # Step 5: Summary
    print("\n📊 STEP 5: Processing Summary")
    print("-" * 80)

    print(f"✅ Complete Order Processing Successful!\n")
    print(f"Input:")
    print(f"  └─ Order: {order.order_id} (PO: {order.purchase_order})")
    print(f"     └─ {len(order.items)} line items, {sum(item.quantity for item in order.items)} units\n")

    print(f"Output:")
    print(f"  ├─ Shipment: {shipment.shipment_id}")
    print(f"  │  └─ {shipment.total_cartons} carton(s), {shipment.total_weight:.2f} lbs")
    print(f"  │")
    print(f"  ├─ EDI 856 ASN: {asn_file.name}")
    print(f"  │  └─ {segment_count} segments, {len(edi_content)} bytes")
    print(f"  │")
    print(f"  └─ Shipping Labels: {labels_dir.name}/")
    try:
        print(f"     └─ {label_batch.total_labels} PDF label(s)")
    except:
        print(f"     └─ (skipped)")

    print(f"\n🎉 All processing stages complete!")


def demo_multi_carton_flow():
    """Demonstrate multi-carton order processing."""
    print_separator("MULTI-CARTON ORDER PROCESSING")

    # Load order 002
    order_path = Path("examples/sample_orders/order_002_multi_carton.json")
    print(f"📥 Loading: {order_path}")

    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)

    # Force more cartons with smaller limits
    from src.cartonization.config import CartonizationConfig
    config = CartonizationConfig(
        max_items_per_carton=30,
        max_weight_per_carton=75.0
    )

    print(f"\n📦 Cartonizing with constraints:")
    print(f"   Max items per carton: {config.max_items_per_carton}")
    print(f"   Max weight per carton: {config.max_weight_per_carton} lbs")

    engine = CartonizationEngine(config)
    shipment_package = engine.cartonize_order(order)

    shipment = shipment_package.shipment
    print(f"\n✅ Created {shipment.total_cartons} cartons")

    # Generate ASN
    print(f"\n📄 Generating ASN...")
    asn_builder = ASNBuilder()
    edi_content = asn_builder.build_asn(shipment_package)

    output_dir = Path("output")
    asn_file = output_dir / f"856_{shipment.shipment_id}.txt"
    with open(asn_file, "w") as f:
        f.write(edi_content)

    # Count specific segments
    hl_count = edi_content.count("HL*")
    sscc_count = edi_content.count("REF*0J*")

    print(f"   HL Segments: {hl_count}")
    print(f"   SSCC References: {sscc_count}")
    print(f"   File: {asn_file}")

    # Generate labels
    print(f"\n🏷️  Generating {shipment.total_cartons} shipping labels...")

    try:
        label_builder = LabelBuilder()
        labels_dir = output_dir / "labels"
        label_batch = label_builder.render_labels_for_shipment(
            shipment_package,
            str(labels_dir)
        )

        print(f"✅ {label_batch.total_labels} labels generated")

        # Show SSCC list
        print(f"\nSSCC List:")
        for label in label_batch.labels[:5]:  # Show first 5
            print(f"  - {label.sscc}")
        if label_batch.total_labels > 5:
            print(f"  ... and {label_batch.total_labels - 5} more")

    except ImportError:
        print(f"⚠️  Label generation skipped (install reportlab and python-barcode)")

    print(f"\n✅ Multi-carton processing complete!")


def demo_label_preview():
    """Show detailed label content."""
    print_separator("LABEL CONTENT PREVIEW")

    # Load simple order
    order_path = Path("examples/sample_orders/order_001.json")
    with open(order_path) as f:
        order_data = json.load(f)

    order = OrderInput(**order_data)
    engine = CartonizationEngine()
    shipment_package = engine.cartonize_order(order)

    # Build labels
    try:
        label_builder = LabelBuilder()
        labels = label_builder.build_labels_for_shipment(shipment_package)

        label = labels[0]

        print(f"📋 Label Content for Carton {label.carton_sequence}:\n")
        print(f"SSCC (Barcode):")
        print(f"  {label.sscc.get_full_sscc()}")
        print(f"  {label.sscc.get_formatted_sscc()}")
        print(f"\nShip To:")
        print(f"  {label.ship_to_name}")
        print(f"  {label.ship_to_address}")
        print(f"  {label.ship_to_city}, {label.ship_to_state} {label.ship_to_postal}")
        print(f"\nShip From:")
        print(f"  {label.ship_from_name}")
        if label.ship_from_city and label.ship_from_state:
            print(f"  {label.ship_from_city}, {label.ship_from_state}")
        print(f"\nCarton Info:")
        print(f"  Carton: {label.carton_sequence} of {label.total_cartons}")
        if label.weight:
            print(f"  Weight: {label.weight:.2f} lbs")
        if label.item_count:
            print(f"  Items: {label.item_count}")
        if label.carrier_name:
            print(f"  Carrier: {label.carrier_name}")
            if label.service_level:
                print(f"  Service: {label.service_level}")
        if label.purchase_order:
            print(f"  PO: {label.purchase_order}")

        if label.contents_summary:
            print(f"\nContents:")
            for item in label.contents_summary:
                print(f"  • {item}")

        print(f"\n✅ Label preview complete")

    except ImportError as e:
        print(f"⚠️  Label preview skipped: {e}")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  COMPLETE ORDER PROCESSING DEMONSTRATION")
    print("  Project 3: ASN 856 + SSCC Label Generator")
    print("  Order → Cartonization → ASN → Labels")
    print("=" * 80)

    try:
        demo_complete_pipeline()
        demo_multi_carton_flow()
        demo_label_preview()

        print_separator("ALL DEMOS COMPLETE!")
        print("✅ Full order processing pipeline demonstrated")
        print("\nGenerated Files:")
        print("  output/")
        print("  ├── 856_SHIP-ORD-2025-001.txt")
        print("  ├── 856_SHIP-ORD-2025-002.txt")
        print("  └── labels/")
        print("      ├── label_carton_1_*.pdf")
        print("      ├── label_carton_2_*.pdf")
        print("      └── ...")
        print("\n🎉 Project 3 Core Functionality Complete!")
        print("\nNext steps:")
        print("  - PART 6: CLI/UI interface for user interaction")
        print("  - PART 7: Final packaging and documentation")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Sample order file not found")
        print(f"   {e}")
        print(f"\n   Make sure you're running from the project root directory:")
        print(f"   python examples/demo_complete_flow.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
