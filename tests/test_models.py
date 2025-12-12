"""
Model Validation Tests
======================
Basic tests to ensure data models load correctly and validate properly.

Author: Integration Engineering Team
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import json


class TestInputModels:
    """Test input data models."""

    def test_address_validation(self):
        """Test Address model validation."""
        from src.models.input_models import Address

        # Valid address
        addr = Address(
            name="Test Location",
            address_line1="123 Main St",
            city="Dallas",
            state="TX",
            postal_code="75201",
            country="US"
        )
        assert addr.state == "TX"
        assert addr.country == "US"

        # State auto-uppercase
        addr2 = Address(
            name="Test",
            address_line1="123 Main",
            city="Austin",
            state="tx",
            postal_code="78701"
        )
        assert addr2.state == "TX"

    def test_order_line_item_validation(self):
        """Test OrderLineItem validation."""
        from src.models.input_models import OrderLineItem

        # Valid item
        item = OrderLineItem(
            line_number=1,
            sku="TEST-SKU-001",
            description="Test Item",
            quantity=10,
            unit_weight=1.5
        )
        assert item.sku == "TEST-SKU-001"
        assert item.quantity == 10

    def test_order_input_from_json(self):
        """Test loading OrderInput from sample JSON file."""
        from src.models.input_models import OrderInput

        # Load sample order
        sample_path = Path("examples/sample_orders/order_001.json")
        if sample_path.exists():
            with open(sample_path) as f:
                order_data = json.load(f)

            order = OrderInput(**order_data)
            assert order.order_id == "ORD-2025-001"
            assert order.purchase_order == "PO-ACME-12345"
            assert len(order.items) == 3
            assert order.ship_to.state == "TX"


class TestInternalModels:
    """Test internal business models."""

    def test_item_weight_calculation(self):
        """Test Item total weight calculation."""
        from src.models.internal_models import Item

        item = Item(
            sku="TEST-001",
            description="Test Item",
            quantity=10,
            unit_weight=2.5
        )

        total_weight = item.get_total_weight()
        assert total_weight == 25.0

    def test_carton_calculations(self):
        """Test Carton weight and unit calculations."""
        from src.models.internal_models import Carton, Item

        items = [
            Item(sku="SKU-A", description="Item A", quantity=5, unit_weight=2.0),
            Item(sku="SKU-B", description="Item B", quantity=3, unit_weight=1.5)
        ]

        carton = Carton(
            carton_id="CTN-001",
            sequence_number=1,
            items=items
        )

        # Test weight calculation
        total_weight = carton.calculate_weight()
        assert total_weight == 14.5  # (5 * 2.0) + (3 * 1.5)

        # Test unit count
        total_units = carton.get_total_units()
        assert total_units == 8  # 5 + 3

    def test_packaging_level_enum(self):
        """Test PackagingLevel enum values."""
        from src.models.internal_models import PackagingLevel

        assert PackagingLevel.SHIPMENT.value == "S"
        assert PackagingLevel.ORDER.value == "O"
        assert PackagingLevel.TARE.value == "T"
        assert PackagingLevel.ITEM.value == "I"


class TestASNModels:
    """Test ASN-specific models."""

    def test_hl_level_code_enum(self):
        """Test HLLevelCode enum."""
        from src.models.asn_models import HLLevelCode

        assert HLLevelCode.SHIPMENT.value == "S"
        assert HLLevelCode.ORDER.value == "O"
        assert HLLevelCode.TARE.value == "T"

    def test_hierarchical_level_creation(self):
        """Test HierarchicalLevel model."""
        from src.models.asn_models import HierarchicalLevel, HLLevelCode

        # Create root level (shipment)
        root = HierarchicalLevel(
            hl_id="1",
            parent_hl_id=None,
            level_code=HLLevelCode.SHIPMENT,
            child_code="1"
        )

        assert root.hl_id == "1"
        assert root.parent_hl_id is None
        assert root.level_code == HLLevelCode.SHIPMENT

    def test_asn_header_creation(self):
        """Test ASNHeader model."""
        from src.models.asn_models import ASNHeader

        header = ASNHeader(
            shipment_id="SHIP-001",
            shipment_date=datetime.now(),
            sender_id="SENDER123",
            receiver_id="RECEIVER456",
            control_number="1001"
        )

        assert header.shipment_id == "SHIP-001"
        assert header.sender_id == "SENDER123"


class TestLabelModels:
    """Test label and SSCC models."""

    def test_sscc_creation(self):
        """Test SSCC model."""
        from src.models.label_models import SSCC

        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )

        # Test full SSCC
        full_sscc = sscc.get_full_sscc()
        assert len(full_sscc) == 18
        assert full_sscc == "006141411234567898"

        # Test formatted SSCC
        formatted = sscc.get_formatted_sscc()
        assert "0614141" in formatted

        # Test GS1 AI format
        gs1_format = sscc.get_gs1_application_identifier()
        assert gs1_format.startswith("(00)")

    def test_sscc_validation(self):
        """Test SSCC validation rules."""
        from src.models.label_models import SSCC
        from pydantic import ValidationError

        # Valid SSCC
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )
        assert sscc.extension_digit == "0"

        # Invalid extension digit (should fail)
        with pytest.raises(ValidationError):
            SSCC(
                extension_digit="10",  # Too long
                company_prefix="0614141",
                serial_reference="123456789",
                check_digit="8"
            )

    def test_barcode_and_label_enums(self):
        """Test enum types."""
        from src.models.label_models import BarcodeType, LabelSize

        assert BarcodeType.GS1_128.value == "GS1-128"
        assert LabelSize.LABEL_4X6.value == "4x6"


class TestModelIntegration:
    """Test integration between models."""

    def test_full_order_to_shipment_flow(self):
        """Test converting OrderInput to Shipment structure."""
        from src.models.input_models import OrderInput, Address, OrderLineItem
        from src.models.internal_models import Item, Carton, Order, Shipment

        # Create sample order
        order_input = OrderInput(
            order_id="ORD-001",
            purchase_order="PO-12345",
            ship_date=date(2025, 12, 15),
            ship_from=Address(
                name="Warehouse",
                address_line1="123 Industrial",
                city="Dallas",
                state="TX",
                postal_code="75201"
            ),
            ship_to=Address(
                name="Store",
                address_line1="456 Main",
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

        # Verify order structure
        assert order_input.order_id == "ORD-001"
        assert len(order_input.items) == 1
        assert order_input.ship_to.state == "TX"

        # Create internal models (simplified)
        items = [
            Item(
                sku=order_input.items[0].sku,
                description=order_input.items[0].description,
                quantity=order_input.items[0].quantity,
                unit_weight=order_input.items[0].unit_weight
            )
        ]

        carton = Carton(
            carton_id="CTN-001",
            sequence_number=1,
            items=items
        )

        order = Order(
            order_id=order_input.order_id,
            purchase_order=order_input.purchase_order,
            carton_ids=[carton.carton_id]
        )

        shipment = Shipment(
            shipment_id="SHIP-001",
            ship_date=datetime.combine(order_input.ship_date, datetime.min.time()),
            ship_from_name=order_input.ship_from.name,
            ship_from_address=f"{order_input.ship_from.address_line1}, {order_input.ship_from.city}, {order_input.ship_from.state}",
            ship_to_name=order_input.ship_to.name,
            ship_to_address=f"{order_input.ship_to.address_line1}, {order_input.ship_to.city}, {order_input.ship_to.state}",
            orders=[order],
            cartons=[carton],
            total_cartons=1
        )

        # Verify shipment
        assert shipment.shipment_id == "SHIP-001"
        assert len(shipment.orders) == 1
        assert len(shipment.cartons) == 1
        assert shipment.cartons[0].carton_id == "CTN-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
