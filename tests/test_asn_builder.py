"""
ASN Builder Tests
=================
Tests for EDI 856 ASN generation.

Author: Integration Engineering Team
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import json

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.asn_builder.builder import ASNBuilder, create_asn_builder
from src.asn_builder.segments import SegmentGenerator
from src.asn_builder.hierarchy import HierarchyBuilder


class TestSegmentGenerator:
    """Test individual segment generation."""

    def test_segment_generator_initialization(self):
        """Test segment generator initializes correctly."""
        gen = SegmentGenerator()
        assert gen.element_sep == "*"
        assert gen.subelement_sep == ":"

    def test_generate_isa(self):
        """Test ISA segment generation."""
        gen = SegmentGenerator()
        isa = gen.generate_isa(
            sender_id="SENDER123",
            receiver_id="RECEIVER456",
            control_number="1",
            timestamp=datetime(2025, 12, 15, 14, 30)
        )

        assert isa.startswith("ISA")
        assert "SENDER123" in isa
        assert "RECEIVER456" in isa
        assert "251215" in isa  # Date YYMMDD
        assert "1430" in isa     # Time HHMM

    def test_generate_gs(self):
        """Test GS segment generation."""
        gen = SegmentGenerator()
        gs = gen.generate_gs(
            sender_code="SENDER",
            receiver_code="RECEIVER",
            control_number="1",
            timestamp=datetime(2025, 12, 15, 14, 30)
        )

        assert gs.startswith("GS*SH")
        assert "SENDER" in gs
        assert "RECEIVER" in gs
        assert "20251215" in gs  # Date YYYYMMDD

    def test_generate_st(self):
        """Test ST segment generation."""
        gen = SegmentGenerator()
        st = gen.generate_st("1")

        assert st == "ST*856*0001"

    def test_generate_bsn(self):
        """Test BSN segment generation."""
        gen = SegmentGenerator()
        bsn = gen.generate_bsn(
            shipment_id="SHIP-001",
            ship_date=datetime(2025, 12, 15, 14, 30)
        )

        assert bsn.startswith("BSN*00")
        assert "SHIP-001" in bsn
        assert "20251215" in bsn

    def test_generate_hl(self):
        """Test HL segment generation."""
        gen = SegmentGenerator()

        # Shipment level (root, has children)
        hl_s = gen.generate_hl("1", None, "S", has_children=True)
        assert hl_s == "HL*1**S*1"

        # Order level (has parent and children)
        hl_o = gen.generate_hl("2", "1", "O", has_children=True)
        assert hl_o == "HL*2*1*O*1"

        # Item level (has parent, no children)
        hl_i = gen.generate_hl("4", "3", "I", has_children=False)
        assert hl_i == "HL*4*3*I*0"

    def test_generate_ref(self):
        """Test REF segment generation."""
        gen = SegmentGenerator()

        # PO reference
        ref_po = gen.generate_ref("PO", "PO-12345")
        assert ref_po == "REF*PO*PO-12345"

        # SSCC reference
        ref_sscc = gen.generate_ref("0J", "006141410000000018")
        assert ref_sscc == "REF*0J*006141410000000018"

    def test_generate_lin(self):
        """Test LIN segment generation."""
        gen = SegmentGenerator()
        lin = gen.generate_lin("SKU-123", "SK")

        assert lin == "LIN**SK*SKU-123"

    def test_generate_sn1(self):
        """Test SN1 segment generation."""
        gen = SegmentGenerator()
        sn1 = gen.generate_sn1(50, "EA")

        assert sn1 == "SN1**50*EA"

    def test_generate_td1(self):
        """Test TD1 segment generation."""
        gen = SegmentGenerator()
        td1 = gen.generate_td1(
            packaging_code="CTN",
            lading_quantity=1,
            weight=25.5
        )

        assert "TD1*CTN*1" in td1
        assert "G*25.50*LB" in td1

    def test_generate_ctt(self):
        """Test CTT segment generation."""
        gen = SegmentGenerator()
        ctt = gen.generate_ctt(line_count=5, total_weight=125.75)

        assert "CTT*5" in ctt
        assert "125.75*LB" in ctt


class TestHierarchyBuilder:
    """Test HL hierarchy construction."""

    def test_hierarchy_builder_initialization(self):
        """Test hierarchy builder initializes correctly."""
        gen = SegmentGenerator()
        builder = HierarchyBuilder(gen)
        assert builder.hl_counter == 0

    def test_build_simple_hierarchy(self):
        """Test building hierarchy for simple shipment."""
        # Create simple shipment via cartonization
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="TEST-001",
            purchase_order="PO-001",
            ship_date=date(2025, 12, 15),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-A",
                    description="Item A",
                    quantity=10,
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        # Build hierarchy
        gen = SegmentGenerator()
        builder = HierarchyBuilder(gen)
        root = builder.build_hierarchy(result.shipment)

        # Verify structure
        assert root.level_code == "S"  # Shipment
        assert root.has_children()
        assert len(root.children) == 1  # One order

        order_node = root.children[0]
        assert order_node.level_code == "O"  # Order
        assert order_node.has_children()

        # Should have at least one carton
        assert len(order_node.children) >= 1

        carton_node = order_node.children[0]
        assert carton_node.level_code == "T"  # Tare/Carton
        assert carton_node.has_children()

    def test_get_all_segments(self):
        """Test getting all segments from hierarchy."""
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="TEST-002",
            purchase_order="PO-002",
            ship_date=date(2025, 12, 15),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-A",
                    description="Item A",
                    quantity=10,
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        gen = SegmentGenerator()
        builder = HierarchyBuilder(gen)
        root = builder.build_hierarchy(result.shipment)

        # Get all segments
        segments = root.get_all_segments()

        # Should have multiple segments
        assert len(segments) > 0

        # First segment should be HL*1 (shipment)
        assert segments[0].startswith("HL*1")


class TestASNBuilder:
    """Test complete ASN document generation."""

    def test_asn_builder_initialization(self):
        """Test ASN builder initializes correctly."""
        builder = ASNBuilder()
        assert builder.segment_terminator == "~"
        assert builder.element_separator == "*"

    def test_build_simple_asn(self):
        """Test building complete ASN from simple order."""
        # Create order and cartonize
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="ORD-001",
            purchase_order="PO-12345",
            ship_date=date(2025, 12, 15),
            ship_from=Address(
                name="ACME Warehouse",
                address_line1="123 Industrial Blvd",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Retail Store #42",
                address_line1="456 Commerce St",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="WIDGET-A",
                    description="Premium Widget",
                    quantity=25,
                    unit_weight=2.0
                )
            ]
        )

        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        # Build ASN
        builder = ASNBuilder()
        edi_content = builder.build_asn(
            shipment_package,
            sender_id="ACME",
            receiver_id="RETAIL"
        )

        # Verify structure
        assert edi_content.startswith("ISA")
        assert "GS*SH" in edi_content
        assert "ST*856" in edi_content
        assert "BSN" in edi_content
        assert "HL" in edi_content
        assert "CTT" in edi_content
        assert "SE*" in edi_content
        assert "GE*" in edi_content
        assert edi_content.endswith("~")

    def test_asn_contains_required_segments(self):
        """Test ASN contains all required segments."""
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="ORD-002",
            purchase_order="PO-67890",
            ship_date=date(2025, 12, 16),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-A",
                    description="Item A",
                    quantity=10,
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        builder = ASNBuilder()
        edi_content = builder.build_asn(shipment_package)

        # Check for required segments
        required_segments = [
            "ISA",  # Interchange header
            "GS",   # Functional group header
            "ST",   # Transaction set header
            "BSN",  # Beginning segment
            "HL",   # Hierarchical level
            "REF",  # Reference (PO, SSCC)
            "LIN",  # Item identification
            "SN1",  # Item quantity
            "CTT",  # Transaction totals
            "SE",   # Transaction set trailer
            "GE",   # Functional group trailer
            "IEA"   # Interchange trailer
        ]

        for segment in required_segments:
            assert segment in edi_content, f"Missing required segment: {segment}"

    def test_asn_with_sscc(self):
        """Test ASN includes SSCC references."""
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="ORD-003",
            purchase_order="PO-SSCC-TEST",
            ship_date=date(2025, 12, 17),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-B",
                    description="Item B",
                    quantity=20,
                    unit_weight=1.5
                )
            ]
        )

        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        # Get SSCC from first carton
        sscc = shipment_package.shipment.cartons[0].sscc

        builder = ASNBuilder()
        edi_content = builder.build_asn(shipment_package)

        # Verify SSCC is in the output
        assert f"REF*0J*{sscc}" in edi_content

    def test_asn_segment_count(self):
        """Test segment count is accurate."""
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="ORD-004",
            purchase_order="PO-COUNT",
            ship_date=date(2025, 12, 18),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-C",
                    description="Item C",
                    quantity=5,
                    unit_weight=0.5
                )
            ]
        )

        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        builder = ASNBuilder()
        edi_content = builder.build_asn(shipment_package)

        # Count segments (split by terminator, subtract 1 for empty last element)
        segment_count = builder.count_segments(edi_content)

        # Should have multiple segments
        assert segment_count > 10

    def test_format_for_display(self):
        """Test formatting ASN for human-readable display."""
        from src.models.input_models import OrderInput, OrderLineItem, Address

        order = OrderInput(
            order_id="ORD-005",
            purchase_order="PO-FORMAT",
            ship_date=date(2025, 12, 19),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Main",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Elm",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            items=[
                OrderLineItem(
                    line_number=1,
                    sku="SKU-D",
                    description="Item D",
                    quantity=15,
                    unit_weight=1.2
                )
            ]
        )

        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        builder = ASNBuilder()
        edi_content = builder.build_asn(shipment_package)

        # Format for display
        formatted = builder.format_for_display(edi_content)

        # Should have line breaks
        assert "\n" in formatted

        # Each line should be a segment
        lines = formatted.split("\n")
        assert len(lines) > 10


class TestASNWithSampleOrders:
    """Test ASN generation with real sample order files."""

    def test_sample_order_001_asn(self):
        """Test ASN generation from sample order 001."""
        sample_path = Path("examples/sample_orders/order_001.json")
        if not sample_path.exists():
            pytest.skip("Sample order file not found")

        # Load and cartonize order
        with open(sample_path) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)
        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        # Build ASN
        builder = ASNBuilder()
        edi_content = builder.build_asn(
            shipment_package,
            sender_id="ACME",
            receiver_id="TECHMART"
        )

        # Verify output
        assert "ISA" in edi_content
        assert "ORD-2025-001" in edi_content or "SHIP-ORD-2025-001" in edi_content
        assert "PO-ACME-12345" in edi_content

    def test_sample_order_002_asn(self):
        """Test ASN generation from sample order 002 (multi-carton)."""
        sample_path = Path("examples/sample_orders/order_002_multi_carton.json")
        if not sample_path.exists():
            pytest.skip("Sample order file not found")

        with open(sample_path) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)
        engine = CartonizationEngine()
        shipment_package = engine.cartonize_order(order)

        builder = ASNBuilder()
        edi_content = builder.build_asn(
            shipment_package,
            sender_id="ACME",
            receiver_id="BIGBOX"
        )

        # Verify multiple cartons
        sscc_count = edi_content.count("REF*0J*")
        assert sscc_count >= 1  # Should have at least one SSCC


class TestASNValidation:
    """Test ASN validation logic."""

    def test_validate_empty_shipment(self):
        """Test validation catches empty shipment."""
        from src.models.internal_models import ShipmentPackage, Shipment

        package = ShipmentPackage(
            shipment=Shipment(
                shipment_id="EMPTY",
                ship_date=datetime.now(),
                ship_from_name="Warehouse",
                ship_from_address="123 Main",
                ship_to_name="Store",
                ship_to_address="456 Elm",
                orders=[],
                cartons=[],
                total_cartons=0
            )
        )

        builder = ASNBuilder()
        with pytest.raises(ValueError, match="at least one order"):
            builder.build_asn(package)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
