"""
ASN Hierarchy Builder
=====================
Builds the hierarchical HL loop structure for EDI 856 ASN documents.

Hierarchy structure:
  HL Shipment (S)
    HL Order (O)
      HL Tare/Carton (T)
        HL Item (I)

Author: Integration Engineering Team
"""

from typing import List, Tuple
import logging

from src.models.internal_models import Shipment, Order, Carton, Item
from src.asn_builder.segments import SegmentGenerator

logger = logging.getLogger(__name__)


class HierarchyNode:
    """
    Represents a node in the HL hierarchy tree.
    """

    def __init__(
        self,
        hl_number: str,
        parent_hl: str,
        level_code: str,
        segments: List[str],
        children: List["HierarchyNode"] = None
    ):
        """
        Initialize a hierarchy node.

        Args:
            hl_number: Hierarchical ID number
            parent_hl: Parent hierarchical ID (empty string for root)
            level_code: Level code (S/O/T/I)
            segments: List of segment strings for this level
            children: Child nodes
        """
        self.hl_number = hl_number
        self.parent_hl = parent_hl
        self.level_code = level_code
        self.segments = segments
        self.children = children or []

    def has_children(self) -> bool:
        """Check if this node has children."""
        return len(self.children) > 0

    def get_all_segments(self) -> List[str]:
        """
        Get all segments for this node and its children (depth-first).

        Returns:
            List of segment strings in proper order
        """
        all_segments = self.segments.copy()

        for child in self.children:
            all_segments.extend(child.get_all_segments())

        return all_segments

    def count_nodes(self) -> int:
        """Count total number of nodes in this subtree."""
        count = 1  # This node
        for child in self.children:
            count += child.count_nodes()
        return count


class HierarchyBuilder:
    """
    Builds the HL loop hierarchy for an 856 ASN document.
    """

    def __init__(self, segment_generator: SegmentGenerator):
        """
        Initialize hierarchy builder.

        Args:
            segment_generator: Segment generator instance
        """
        self.seg_gen = segment_generator
        self.hl_counter = 0

    def _get_next_hl(self) -> str:
        """Get next HL number."""
        self.hl_counter += 1
        return str(self.hl_counter)

    def build_hierarchy(self, shipment: Shipment) -> HierarchyNode:
        """
        Build complete HL hierarchy for a shipment.

        Args:
            shipment: Shipment object

        Returns:
            Root HierarchyNode (Shipment level)
        """
        logger.info(f"Building hierarchy for shipment {shipment.shipment_id}")

        # Reset counter
        self.hl_counter = 0

        # Build shipment level (root)
        shipment_node = self._build_shipment_level(shipment)

        logger.info(
            f"Hierarchy complete: {shipment_node.count_nodes()} total nodes, "
            f"{len(shipment_node.get_all_segments())} segments"
        )

        return shipment_node

    def _build_shipment_level(self, shipment: Shipment) -> HierarchyNode:
        """
        Build HL Shipment level (S).

        Args:
            shipment: Shipment object

        Returns:
            Shipment-level HierarchyNode
        """
        hl_number = self._get_next_hl()
        parent_hl = ""  # No parent (root)

        # Generate segments for shipment level
        segments = []

        # HL segment
        segments.append(
            self.seg_gen.generate_hl(hl_number, parent_hl, "S", has_children=True)
        )

        # TD5: Carrier details
        if shipment.carrier_code:
            segments.append(
                self.seg_gen.generate_td5(carrier_code=shipment.carrier_code)
            )

        # DTM: Ship date
        segments.append(
            self.seg_gen.generate_dtm("011", shipment.ship_date)
        )

        # N1/N3/N4: Ship From
        segments.append(
            self.seg_gen.generate_n1("SF", shipment.ship_from_name)
        )
        # Parse address (simplified - assumes address is formatted)
        if ", " in shipment.ship_from_address:
            parts = shipment.ship_from_address.split(", ")
            if len(parts) >= 1:
                segments.append(self.seg_gen.generate_n3(parts[0]))

        # N1/N3/N4: Ship To
        segments.append(
            self.seg_gen.generate_n1("ST", shipment.ship_to_name)
        )
        if ", " in shipment.ship_to_address:
            parts = shipment.ship_to_address.split(", ")
            if len(parts) >= 1:
                segments.append(self.seg_gen.generate_n3(parts[0]))

        # Build child order nodes
        children = []
        for order in shipment.orders:
            order_node = self._build_order_level(order, hl_number, shipment)
            children.append(order_node)

        logger.debug(f"Built shipment level HL{hl_number} with {len(children)} order(s)")

        return HierarchyNode(hl_number, parent_hl, "S", segments, children)

    def _build_order_level(self, order: Order, parent_hl: str, shipment: Shipment) -> HierarchyNode:
        """
        Build HL Order level (O).

        Args:
            order: Order object
            parent_hl: Parent HL number (shipment)
            shipment: Parent shipment object

        Returns:
            Order-level HierarchyNode
        """
        hl_number = self._get_next_hl()

        segments = []

        # HL segment
        segments.append(
            self.seg_gen.generate_hl(hl_number, parent_hl, "O", has_children=True)
        )

        # REF: Purchase Order
        segments.append(
            self.seg_gen.generate_ref("PO", order.purchase_order)
        )

        # Build child carton nodes
        children = []
        for carton_id in order.carton_ids:
            # Find carton in shipment
            carton = next((c for c in shipment.cartons if c.carton_id == carton_id), None)
            if carton:
                carton_node = self._build_carton_level(carton, hl_number)
                children.append(carton_node)

        logger.debug(f"Built order level HL{hl_number} with {len(children)} carton(s)")

        return HierarchyNode(hl_number, parent_hl, "O", segments, children)

    def _build_carton_level(self, carton: Carton, parent_hl: str) -> HierarchyNode:
        """
        Build HL Tare/Carton level (T).

        Args:
            carton: Carton object
            parent_hl: Parent HL number (order)

        Returns:
            Carton-level HierarchyNode
        """
        hl_number = self._get_next_hl()

        segments = []

        # HL segment
        segments.append(
            self.seg_gen.generate_hl(hl_number, parent_hl, "T", has_children=True)
        )

        # REF: SSCC
        if carton.sscc:
            segments.append(
                self.seg_gen.generate_ref("0J", carton.sscc)
            )

        # TD1: Package details
        weight = carton.weight if carton.weight else carton.calculate_weight()
        segments.append(
            self.seg_gen.generate_td1(
                packaging_code=carton.packaging_code,
                lading_quantity=1,
                weight=weight
            )
        )

        # Build child item nodes
        children = []
        for item in carton.items:
            item_node = self._build_item_level(item, hl_number)
            children.append(item_node)

        logger.debug(
            f"Built carton level HL{hl_number} (SSCC: {carton.sscc}) "
            f"with {len(children)} item(s)"
        )

        return HierarchyNode(hl_number, parent_hl, "T", segments, children)

    def _build_item_level(self, item: Item, parent_hl: str) -> HierarchyNode:
        """
        Build HL Item level (I).

        Args:
            item: Item object
            parent_hl: Parent HL number (carton)

        Returns:
            Item-level HierarchyNode
        """
        hl_number = self._get_next_hl()

        segments = []

        # HL segment (no children at item level)
        segments.append(
            self.seg_gen.generate_hl(hl_number, parent_hl, "I", has_children=False)
        )

        # LIN: Item identification
        segments.append(
            self.seg_gen.generate_lin(item.sku, product_id_qualifier="SK")
        )

        # SN1: Item quantity
        segments.append(
            self.seg_gen.generate_sn1(item.quantity, item.uom)
        )

        logger.debug(f"Built item level HL{hl_number} for SKU {item.sku}")

        return HierarchyNode(hl_number, parent_hl, "I", segments, [])

    def get_line_item_count(self, root: HierarchyNode) -> int:
        """
        Count total number of line items (I-level nodes) in hierarchy.

        Args:
            root: Root hierarchy node

        Returns:
            Count of item-level nodes
        """
        count = 0

        if root.level_code == "I":
            count = 1
        else:
            for child in root.children:
                count += self.get_line_item_count(child)

        return count
