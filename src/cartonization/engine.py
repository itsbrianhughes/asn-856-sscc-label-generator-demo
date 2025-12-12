"""
Cartonization Engine
====================
Packs order items into cartons using configurable rules.

This is a simplified cartonization algorithm for demonstration purposes.
Production systems would use more sophisticated bin-packing algorithms
considering dimensions, fragility, product compatibility, etc.

Author: Integration Engineering Team
"""

from typing import List, Tuple
from datetime import datetime
import logging

from src.models.input_models import OrderInput, OrderLineItem
from src.models.internal_models import Item, Carton, Order, Shipment, ShipmentPackage
from src.cartonization.config import CartonizationConfig, DEFAULT_CARTONIZATION_CONFIG
from src.sscc.generator import SSCCGenerator, create_sscc_generator

logger = logging.getLogger(__name__)


class CartonizationEngine:
    """
    Handles packing of order items into cartons with SSCC assignment.

    Algorithm:
    1. Convert OrderLineItems to Item objects
    2. Apply packing rules (simple greedy algorithm)
    3. Create Carton objects
    4. Assign SSCC to each carton
    5. Build Shipment and Order structures
    6. Return ShipmentPackage ready for ASN generation
    """

    def __init__(self, config: CartonizationConfig = DEFAULT_CARTONIZATION_CONFIG):
        """
        Initialize the cartonization engine.

        Args:
            config: Cartonization configuration
        """
        self.config = config
        self.sscc_generator = create_sscc_generator(
            company_prefix=config.sscc_company_prefix,
            extension_digit=config.sscc_extension_digit,
            serial_start=config.sscc_serial_start
        )
        logger.info("Cartonization engine initialized")

    def cartonize_order(self, order_input: OrderInput) -> ShipmentPackage:
        """
        Convert an order into a shipment with packed cartons.

        Args:
            order_input: Validated order input

        Returns:
            ShipmentPackage with shipment, orders, and cartons

        Raises:
            ValueError: If order cannot be processed
        """
        logger.info(f"Starting cartonization for order: {order_input.order_id}")

        # Step 1: Validate input
        if not order_input.items:
            raise ValueError("Order must have at least one item")

        # Step 2: Convert line items to internal Item objects
        items = self._convert_line_items_to_items(order_input.items)

        # Step 3: Pack items into cartons
        cartons = self._pack_items_into_cartons(items)

        # Step 4: Assign SSCCs to cartons
        for carton in cartons:
            sscc = self.sscc_generator.generate_next()
            carton.sscc = sscc.get_full_sscc()
            logger.debug(f"Assigned SSCC {carton.sscc} to {carton.carton_id}")

        # Step 5: Calculate carton weights
        for carton in cartons:
            if carton.weight is None:
                carton.weight = carton.calculate_weight()

        # Step 6: Build Order object
        order = Order(
            order_id=order_input.order_id,
            purchase_order=order_input.purchase_order,
            carton_ids=[c.carton_id for c in cartons],
            customer_account=order_input.customer_account,
            order_date=datetime.combine(order_input.ship_date, datetime.min.time())
        )

        # Step 7: Build Shipment object
        shipment = self._build_shipment(order_input, order, cartons)

        # Step 8: Create ShipmentPackage
        shipment_package = ShipmentPackage(
            shipment=shipment,
            generated_at=datetime.utcnow()
        )

        logger.info(
            f"Cartonization complete: {len(cartons)} carton(s) generated "
            f"for order {order_input.order_id}"
        )

        return shipment_package

    def _convert_line_items_to_items(self, line_items: List[OrderLineItem]) -> List[Item]:
        """
        Convert OrderLineItem objects to internal Item objects.

        Args:
            line_items: List of order line items

        Returns:
            List of Item objects
        """
        items = []
        for line_item in line_items:
            item = Item(
                sku=line_item.sku,
                description=line_item.description,
                quantity=line_item.quantity,
                uom=line_item.uom,
                unit_weight=line_item.unit_weight
            )
            items.append(item)
            logger.debug(f"Converted line item: {item.sku} x {item.quantity}")

        return items

    def _pack_items_into_cartons(self, items: List[Item]) -> List[Carton]:
        """
        Pack items into cartons using configured rules.

        This is a simplified greedy algorithm:
        - If single_item_cartons=True: Each item type gets separate cartons
        - Otherwise: Pack items sequentially until limits are reached

        Args:
            items: List of items to pack

        Returns:
            List of packed Carton objects
        """
        cartons = []
        carton_sequence = 1

        if self.config.single_item_cartons:
            # Each item type gets its own carton(s)
            for item in items:
                item_cartons = self._pack_single_item_type(item, carton_sequence)
                cartons.extend(item_cartons)
                carton_sequence += len(item_cartons)
        else:
            # Pack items together using greedy algorithm
            cartons = self._pack_greedy(items, carton_sequence)

        logger.info(f"Packed {len(items)} item type(s) into {len(cartons)} carton(s)")
        return cartons

    def _pack_single_item_type(self, item: Item, start_sequence: int) -> List[Carton]:
        """
        Pack a single item type into one or more cartons.

        Args:
            item: Item to pack
            start_sequence: Starting carton sequence number

        Returns:
            List of cartons containing this item type
        """
        cartons = []
        remaining_qty = item.quantity
        sequence = start_sequence

        while remaining_qty > 0:
            # Determine how many units fit in this carton
            carton_qty = min(remaining_qty, self.config.max_items_per_carton)

            # Check weight constraint if applicable
            if self.config.max_weight_per_carton and item.unit_weight:
                max_qty_by_weight = int(
                    self.config.max_weight_per_carton / item.unit_weight
                )
                carton_qty = min(carton_qty, max_qty_by_weight)

                # Ensure at least 1 item per carton
                if carton_qty < 1:
                    carton_qty = 1

            # Create carton with this quantity
            carton_item = Item(
                sku=item.sku,
                description=item.description,
                quantity=carton_qty,
                uom=item.uom,
                unit_weight=item.unit_weight,
                upc=item.upc,
                vendor_part_number=item.vendor_part_number
            )

            carton = Carton(
                carton_id=self.config.get_carton_id(sequence),
                sequence_number=sequence,
                items=[carton_item],
                length=self.config.default_carton_length,
                width=self.config.default_carton_width,
                height=self.config.default_carton_height
            )

            cartons.append(carton)
            remaining_qty -= carton_qty
            sequence += 1

            logger.debug(
                f"Created carton {carton.carton_id} with {carton_qty} units of {item.sku}"
            )

        return cartons

    def _pack_greedy(self, items: List[Item], start_sequence: int) -> List[Carton]:
        """
        Pack items using a simple greedy algorithm.

        Sequentially adds items to cartons until limits are reached.

        Args:
            items: List of items to pack
            start_sequence: Starting carton sequence number

        Returns:
            List of packed cartons
        """
        cartons = []
        current_carton_items = []
        current_carton_qty = 0
        current_carton_weight = 0.0
        sequence = start_sequence

        for item in items:
            remaining_qty = item.quantity

            while remaining_qty > 0:
                # Calculate how much space is available in current carton (by item count)
                space_remaining = self.config.max_items_per_carton - current_carton_qty

                # Determine qty to add to current carton
                # Start with the minimum of remaining_qty and space_remaining
                qty_to_add = min(remaining_qty, int(space_remaining))

                # If weight constraints are active, also check weight limit
                if self.config.max_weight_per_carton and item.unit_weight:
                    # Calculate how many units can fit given weight constraint
                    weight_remaining = (
                        self.config.max_weight_per_carton - current_carton_weight
                    ) / item.unit_weight
                    # Take the minimum of current qty_to_add and weight-based limit
                    qty_to_add = min(qty_to_add, int(weight_remaining))

                if qty_to_add <= 0:
                    # Current carton is full, start a new one
                    if current_carton_items:
                        cartons.append(self._create_carton(
                            current_carton_items,
                            sequence
                        ))
                        sequence += 1

                    current_carton_items = []
                    current_carton_qty = 0
                    current_carton_weight = 0.0
                    continue

                # Add items to current carton
                carton_item = Item(
                    sku=item.sku,
                    description=item.description,
                    quantity=qty_to_add,
                    uom=item.uom,
                    unit_weight=item.unit_weight,
                    upc=item.upc,
                    vendor_part_number=item.vendor_part_number
                )

                current_carton_items.append(carton_item)
                current_carton_qty += qty_to_add
                if item.unit_weight:
                    current_carton_weight += qty_to_add * item.unit_weight

                remaining_qty -= qty_to_add

        # Add final carton if it has items
        if current_carton_items:
            cartons.append(self._create_carton(current_carton_items, sequence))

        return cartons

    def _create_carton(self, items: List[Item], sequence: int) -> Carton:
        """
        Create a Carton object from a list of items.

        Args:
            items: Items to pack in this carton
            sequence: Carton sequence number

        Returns:
            Carton object
        """
        carton = Carton(
            carton_id=self.config.get_carton_id(sequence),
            sequence_number=sequence,
            items=items,
            length=self.config.default_carton_length,
            width=self.config.default_carton_width,
            height=self.config.default_carton_height
        )

        logger.debug(
            f"Created carton {carton.carton_id} with {len(items)} item type(s), "
            f"{carton.get_total_units()} total units"
        )

        return carton

    def _build_shipment(
        self,
        order_input: OrderInput,
        order: Order,
        cartons: List[Carton]
    ) -> Shipment:
        """
        Build a Shipment object from order and cartons.

        Args:
            order_input: Original order input
            order: Order object
            cartons: List of cartons

        Returns:
            Shipment object
        """
        # Generate shipment ID
        shipment_id = f"SHIP-{order_input.order_id}"

        # Format addresses
        ship_from_address = self._format_address(order_input.ship_from)
        ship_to_address = self._format_address(order_input.ship_to)

        # Create shipment
        shipment = Shipment(
            shipment_id=shipment_id,
            ship_date=datetime.combine(order_input.ship_date, datetime.min.time()),
            ship_from_name=order_input.ship_from.name,
            ship_from_address=ship_from_address,
            ship_to_name=order_input.ship_to.name,
            ship_to_address=ship_to_address,
            carrier_code=order_input.carrier_code,
            service_level=order_input.service_level,
            orders=[order],
            cartons=cartons,
            total_cartons=len(cartons)
        )

        # Calculate totals
        shipment.calculate_totals()

        logger.info(
            f"Built shipment {shipment.shipment_id}: "
            f"{len(cartons)} carton(s), {shipment.total_weight:.2f} lbs"
        )

        return shipment

    @staticmethod
    def _format_address(address) -> str:
        """
        Format an Address object as a string.

        Args:
            address: Address object

        Returns:
            Formatted address string
        """
        parts = [address.address_line1]
        if address.address_line2:
            parts.append(address.address_line2)
        parts.append(f"{address.city}, {address.state} {address.postal_code}")
        return ", ".join(parts)
