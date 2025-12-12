"""
Cartonization Engine Tests
===========================
Tests for order cartonization and packing logic.

Author: Integration Engineering Team
"""

import pytest
from datetime import date
from pathlib import Path
import json

from src.cartonization.engine import CartonizationEngine
from src.cartonization.config import CartonizationConfig
from src.models.input_models import OrderInput, OrderLineItem, Address


class TestCartonizationEngine:
    """Test basic cartonization functionality."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        config = CartonizationConfig()
        engine = CartonizationEngine(config)
        assert engine.config is not None
        assert engine.sscc_generator is not None

    def test_simple_order_single_carton(self):
        """Test cartonizing a simple order that fits in one carton."""
        # Create small order
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

        # Verify results
        assert result.shipment is not None
        assert len(result.shipment.cartons) == 1
        assert result.shipment.cartons[0].sscc is not None
        assert len(result.shipment.cartons[0].sscc) == 18

    def test_order_multiple_cartons_by_quantity(self):
        """Test order that requires multiple cartons due to quantity limit."""
        config = CartonizationConfig(
            max_items_per_carton=25,  # Force multiple cartons
            max_weight_per_carton=None  # Ignore weight
        )

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
                    quantity=60,  # 60 items / 25 per carton = 3 cartons
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # Should create 3 cartons (25 + 25 + 10)
        assert len(result.shipment.cartons) == 3
        assert result.shipment.cartons[0].get_total_units() == 25
        assert result.shipment.cartons[1].get_total_units() == 25
        assert result.shipment.cartons[2].get_total_units() == 10

    def test_order_multiple_cartons_by_weight(self):
        """Test order that requires multiple cartons due to weight limit."""
        config = CartonizationConfig(
            max_items_per_carton=100,  # High limit
            max_weight_per_carton=20.0  # Low weight limit
        )

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
                    sku="HEAVY-ITEM",
                    description="Heavy Item",
                    quantity=15,  # 15 items @ 5 lbs = 75 lbs total
                    unit_weight=5.0  # 20 lb limit / 5 lb = 4 items per carton
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # Should create 4 cartons (4 + 4 + 4 + 3)
        assert len(result.shipment.cartons) == 4

        # Verify no carton exceeds weight limit
        for carton in result.shipment.cartons:
            assert carton.calculate_weight() <= 20.0


class TestCartonizationMultipleItems:
    """Test cartonization with multiple item types."""

    def test_multiple_items_single_carton(self):
        """Test multiple items that fit in one carton."""
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
                    sku="SKU-A",
                    description="Item A",
                    quantity=10,
                    unit_weight=1.0
                ),
                OrderLineItem(
                    line_number=2,
                    sku="SKU-B",
                    description="Item B",
                    quantity=15,
                    unit_weight=0.5
                )
            ]
        )

        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        # Should fit in one carton
        assert len(result.shipment.cartons) == 1
        assert result.shipment.cartons[0].get_total_units() == 25

    def test_multiple_items_multiple_cartons(self):
        """Test multiple items requiring multiple cartons."""
        config = CartonizationConfig(max_items_per_carton=20)

        order = OrderInput(
            order_id="TEST-005",
            purchase_order="PO-005",
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
                    quantity=15,
                    unit_weight=1.0
                ),
                OrderLineItem(
                    line_number=2,
                    sku="SKU-B",
                    description="Item B",
                    quantity=25,
                    unit_weight=0.5
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # 15 + 25 = 40 items, 20 per carton = 2 cartons
        assert len(result.shipment.cartons) >= 2


class TestCartonizationModes:
    """Test different cartonization modes."""

    def test_single_item_cartons_mode(self):
        """Test single_item_cartons mode (each SKU separate)."""
        config = CartonizationConfig(
            single_item_cartons=True,
            max_items_per_carton=100
        )

        order = OrderInput(
            order_id="TEST-006",
            purchase_order="PO-006",
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
                ),
                OrderLineItem(
                    line_number=2,
                    sku="SKU-B",
                    description="Item B",
                    quantity=15,
                    unit_weight=0.5
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # Should create 2 cartons (one per SKU)
        assert len(result.shipment.cartons) == 2


class TestSSCCAssignment:
    """Test SSCC assignment to cartons."""

    def test_unique_ssccs_assigned(self):
        """Test that each carton gets a unique SSCC."""
        config = CartonizationConfig(max_items_per_carton=10)

        order = OrderInput(
            order_id="TEST-007",
            purchase_order="PO-007",
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
                    quantity=50,  # Will create 5 cartons
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # Verify all SSCCs are unique
        ssccs = [carton.sscc for carton in result.shipment.cartons]
        assert len(ssccs) == len(set(ssccs))

        # Verify all SSCCs are valid (18 digits)
        for sscc in ssccs:
            assert len(sscc) == 18

    def test_sscc_format_in_carton(self):
        """Test SSCC format stored in carton."""
        order = OrderInput(
            order_id="TEST-008",
            purchase_order="PO-008",
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

        carton = result.shipment.cartons[0]
        assert carton.sscc is not None
        assert carton.sscc.isdigit()
        assert len(carton.sscc) == 18


class TestShipmentStructure:
    """Test shipment structure generation."""

    def test_shipment_metadata(self):
        """Test shipment contains correct metadata."""
        order = OrderInput(
            order_id="TEST-009",
            purchase_order="PO-009",
            ship_date=date(2025, 12, 15),
            ship_from=Address(
                name="ACME Warehouse",
                address_line1="123 Industrial Blvd",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store #42",
                address_line1="456 Main St",
                city="Austin",
                state="TX",
                postal_code="78701"
            ),
            carrier_code="UPSN",
            service_level="Ground",
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

        shipment = result.shipment
        assert shipment.ship_from_name == "ACME Warehouse"
        assert shipment.ship_to_name == "Store #42"
        assert shipment.carrier_code == "UPSN"
        assert shipment.service_level == "Ground"
        assert "Dallas" in shipment.ship_from_address
        assert "Austin" in shipment.ship_to_address

    def test_weight_calculation(self):
        """Test shipment weight calculation."""
        order = OrderInput(
            order_id="TEST-010",
            purchase_order="PO-010",
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
                    unit_weight=2.5
                ),
                OrderLineItem(
                    line_number=2,
                    sku="SKU-B",
                    description="Item B",
                    quantity=20,
                    unit_weight=1.0
                )
            ]
        )

        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        # Total weight should be (10 * 2.5) + (20 * 1.0) = 45.0 lbs
        assert result.shipment.total_weight == 45.0


class TestRealOrderFiles:
    """Test cartonization with real sample order files."""

    def test_sample_order_001(self):
        """Test cartonization of sample order 001."""
        sample_path = Path("examples/sample_orders/order_001.json")
        if not sample_path.exists():
            pytest.skip("Sample order file not found")

        with open(sample_path) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)
        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        assert result.shipment is not None
        assert len(result.shipment.cartons) >= 1
        assert result.shipment.shipment_id == f"SHIP-{order.order_id}"

    def test_sample_order_002_multi_carton(self):
        """Test cartonization of sample order 002 (multi-carton)."""
        sample_path = Path("examples/sample_orders/order_002_multi_carton.json")
        if not sample_path.exists():
            pytest.skip("Sample order file not found")

        with open(sample_path) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)
        engine = CartonizationEngine()
        result = engine.cartonize_order(order)

        # This order has more items, should create multiple cartons
        assert len(result.shipment.cartons) >= 1
        assert all(c.sscc is not None for c in result.shipment.cartons)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_order_items(self):
        """Test that empty order raises error."""
        order = OrderInput(
            order_id="TEST-ERR-001",
            purchase_order="PO-ERR-001",
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
            items=[]
        )

        engine = CartonizationEngine()
        with pytest.raises(ValueError, match="at least one item"):
            engine.cartonize_order(order)

    def test_very_large_quantity(self):
        """Test handling of very large quantities."""
        config = CartonizationConfig(max_items_per_carton=100)

        order = OrderInput(
            order_id="TEST-LARGE",
            purchase_order="PO-LARGE",
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
                    sku="SKU-BULK",
                    description="Bulk Item",
                    quantity=1000,
                    unit_weight=0.1
                )
            ]
        )

        engine = CartonizationEngine(config)
        result = engine.cartonize_order(order)

        # Should create 10 cartons (1000 / 100)
        assert len(result.shipment.cartons) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
