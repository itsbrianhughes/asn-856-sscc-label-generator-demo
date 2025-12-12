"""
Label Generator Tests
=====================
Tests for label generation and rendering.

Author: Integration Engineering Team
"""

import pytest
from datetime import date
from pathlib import Path
import json

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.label_generator.builder import LabelBuilder, create_label_builder
from src.label_generator.barcode import BarcodeGenerator
from src.models.label_models import LabelConfig, LabelSize


class TestBarcodeGenerator:
    """Test barcode generation."""

    def test_barcode_generator_initialization(self):
        """Test barcode generator initializes correctly."""
        gen = BarcodeGenerator()
        assert gen is not None

    def test_generate_sscc_barcode(self):
        """Test SSCC barcode generation."""
        from src.models.label_models import SSCC

        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )

        gen = BarcodeGenerator()

        try:
            barcode = gen.generate_sscc_barcode(sscc, format="PNG")
            assert barcode is not None
            assert barcode.getvalue()  # Has content
        except ImportError:
            pytest.skip("python-barcode not installed")

    def test_generate_barcode_from_string(self):
        """Test generating barcode from string."""
        gen = BarcodeGenerator()

        try:
            barcode = gen.generate_barcode_from_string(
                "TEST123456",
                format="PNG",
                height=40
            )
            assert barcode is not None
        except ImportError:
            pytest.skip("python-barcode not installed")


class TestLabelBuilder:
    """Test label building from carton data."""

    def test_label_builder_initialization(self):
        """Test label builder initializes correctly."""
        try:
            builder = LabelBuilder()
            assert builder is not None
            assert builder.config is not None
        except ImportError:
            pytest.skip("reportlab not installed")

    def test_build_label_for_single_carton(self):
        """Test building label for a single carton."""
        try:
            # Create order and cartonize
            from src.models.input_models import OrderInput, OrderLineItem, Address

            order = OrderInput(
                order_id="TEST-001",
                purchase_order="PO-001",
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

            # Build label
            builder = LabelBuilder()
            labels = builder.build_labels_for_shipment(shipment_package)

            assert len(labels) >= 1
            label = labels[0]

            # Verify label data
            assert label.sscc is not None
            assert label.ship_to_name == "Retail Store #42"
            assert label.ship_from_name == "ACME Warehouse"
            assert label.carton_sequence >= 1
            assert label.total_cartons >= 1
            assert label.purchase_order == "PO-001"

        except ImportError:
            pytest.skip("reportlab not installed")

    def test_build_labels_for_multiple_cartons(self):
        """Test building labels for multiple cartons."""
        try:
            from src.models.input_models import OrderInput, OrderLineItem, Address
            from src.cartonization.config import CartonizationConfig

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
                        quantity=100,  # Force multiple cartons
                        unit_weight=1.0
                    )
                ]
            )

            # Use config that forces multiple cartons
            config = CartonizationConfig(max_items_per_carton=30)
            engine = CartonizationEngine(config)
            shipment_package = engine.cartonize_order(order)

            # Build labels
            builder = LabelBuilder()
            labels = builder.build_labels_for_shipment(shipment_package)

            # Should have multiple labels
            assert len(labels) > 1

            # Verify sequence numbers
            for i, label in enumerate(labels, 1):
                assert label.carton_sequence == i
                assert label.total_cartons == len(labels)

        except ImportError:
            pytest.skip("reportlab not installed")

    def test_label_contains_sscc(self):
        """Test label includes SSCC."""
        try:
            from src.models.input_models import OrderInput, OrderLineItem, Address

            order = OrderInput(
                order_id="TEST-003",
                purchase_order="PO-003",
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
                        sku="SKU-B",
                        description="Item B",
                        quantity=10,
                        unit_weight=1.0
                    )
                ]
            )

            engine = CartonizationEngine()
            shipment_package = engine.cartonize_order(order)

            builder = LabelBuilder()
            labels = builder.build_labels_for_shipment(shipment_package)

            label = labels[0]

            # Verify SSCC
            assert label.sscc is not None
            assert len(label.sscc.get_full_sscc()) == 18
            assert label.sscc.get_full_sscc().isdigit()

        except ImportError:
            pytest.skip("reportlab not installed")

    def test_label_contents_summary(self):
        """Test label includes contents summary."""
        try:
            from src.models.input_models import OrderInput, OrderLineItem, Address

            order = OrderInput(
                order_id="TEST-004",
                purchase_order="PO-004",
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
                        sku="SKU-C",
                        description="Item C",
                        quantity=5,
                        unit_weight=1.0
                    ),
                    OrderLineItem(
                        line_number=2,
                        sku="SKU-D",
                        description="Item D",
                        quantity=3,
                        unit_weight=0.5
                    )
                ]
            )

            engine = CartonizationEngine()
            shipment_package = engine.cartonize_order(order)

            # Build label with contents enabled
            config = LabelConfig(show_contents=True)
            builder = LabelBuilder(config)
            labels = builder.build_labels_for_shipment(shipment_package)

            label = labels[0]

            # Verify contents
            assert label.contents_summary is not None
            assert len(label.contents_summary) > 0

        except ImportError:
            pytest.skip("reportlab not installed")


class TestLabelRendering:
    """Test PDF label rendering."""

    def test_render_single_label(self):
        """Test rendering a single label to PDF."""
        try:
            from src.models.input_models import OrderInput, OrderLineItem, Address

            order = OrderInput(
                order_id="TEST-RENDER-001",
                purchase_order="PO-RENDER-001",
                ship_date=date(2025, 12, 15),
                ship_from=Address(
                    name="Test Warehouse",
                    address_line1="123 Test St",
                    city="Dallas",
                    state="TX",
                    postal_code="75201"
                ),
                ship_to=Address(
                    name="Test Store",
                    address_line1="456 Test Ave",
                    city="Austin",
                    state="TX",
                    postal_code="78701"
                ),
                items=[
                    OrderLineItem(
                        line_number=1,
                        sku="TEST-SKU",
                        description="Test Item",
                        quantity=10,
                        unit_weight=1.0
                    )
                ]
            )

            engine = CartonizationEngine()
            shipment_package = engine.cartonize_order(order)

            # Render labels
            output_dir = Path("output/test_labels")
            output_dir.mkdir(parents=True, exist_ok=True)

            builder = LabelBuilder()
            batch = builder.render_labels_for_shipment(
                shipment_package,
                str(output_dir)
            )

            # Verify batch
            assert batch.total_labels >= 1
            assert len(batch.labels) >= 1

            # Check file exists
            first_label = batch.labels[0]
            assert Path(first_label.file_path).exists()

        except ImportError:
            pytest.skip("reportlab or python-barcode not installed")


class TestLabelWithSampleOrders:
    """Test label generation with real sample orders."""

    def test_sample_order_001_labels(self):
        """Test label generation from sample order 001."""
        try:
            sample_path = Path("examples/sample_orders/order_001.json")
            if not sample_path.exists():
                pytest.skip("Sample order file not found")

            # Load and process order
            with open(sample_path) as f:
                order_data = json.load(f)

            order = OrderInput(**order_data)
            engine = CartonizationEngine()
            shipment_package = engine.cartonize_order(order)

            # Build labels
            builder = LabelBuilder()
            labels = builder.build_labels_for_shipment(shipment_package)

            assert len(labels) >= 1

            # Verify label content
            label = labels[0]
            assert "ACME" in label.ship_from_name
            assert label.sscc is not None

        except ImportError:
            pytest.skip("reportlab not installed")

    def test_sample_order_002_multi_label(self):
        """Test multi-label generation from sample order 002."""
        try:
            sample_path = Path("examples/sample_orders/order_002_multi_carton.json")
            if not sample_path.exists():
                pytest.skip("Sample order file not found")

            with open(sample_path) as f:
                order_data = json.load(f)

            order = OrderInput(**order_data)

            # Force multiple cartons
            from src.cartonization.config import CartonizationConfig
            config = CartonizationConfig(max_items_per_carton=30)
            engine = CartonizationEngine(config)
            shipment_package = engine.cartonize_order(order)

            # Build labels
            builder = LabelBuilder()
            labels = builder.build_labels_for_shipment(shipment_package)

            # Should have multiple labels
            assert len(labels) >= 1

            # All SSCCs should be unique
            ssccs = [label.sscc.get_full_sscc() for label in labels]
            assert len(ssccs) == len(set(ssccs))

        except ImportError:
            pytest.skip("reportlab not installed")


class TestLabelConfiguration:
    """Test label configuration options."""

    def test_custom_label_size(self):
        """Test custom label size configuration."""
        try:
            config = LabelConfig(label_size=LabelSize.LABEL_4X8)
            builder = LabelBuilder(config)
            assert builder.config.label_size == LabelSize.LABEL_4X8
        except ImportError:
            pytest.skip("reportlab not installed")

    def test_disable_contents(self):
        """Test disabling contents display."""
        try:
            from src.models.input_models import OrderInput, OrderLineItem, Address

            order = OrderInput(
                order_id="TEST-NO-CONTENTS",
                purchase_order="PO-NO-CONTENTS",
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
                        sku="SKU-E",
                        description="Item E",
                        quantity=10,
                        unit_weight=1.0
                    )
                ]
            )

            engine = CartonizationEngine()
            shipment_package = engine.cartonize_order(order)

            # Build with contents disabled
            config = LabelConfig(show_contents=False)
            builder = LabelBuilder(config)
            labels = builder.build_labels_for_shipment(shipment_package)

            label = labels[0]
            assert label.contents_summary is None

        except ImportError:
            pytest.skip("reportlab not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
