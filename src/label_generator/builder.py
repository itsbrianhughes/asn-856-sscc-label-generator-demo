"""
Label Builder
=============
Builds ShippingLabel objects from carton and shipment data.

Author: Integration Engineering Team
"""

from typing import List, Optional
from datetime import datetime
import logging

from src.models.internal_models import ShipmentPackage, Shipment, Carton
from src.models.label_models import ShippingLabel, SSCC, LabelBatch, LabelRenderOutput, LabelConfig
from src.label_generator.renderer import LabelRenderer

logger = logging.getLogger(__name__)


class LabelBuilder:
    """
    Builds shipping labels from shipment and carton data.

    Transforms internal shipment models into ShippingLabel objects
    ready for rendering.
    """

    def __init__(self, config: Optional[LabelConfig] = None):
        """
        Initialize label builder.

        Args:
            config: Label configuration (optional)
        """
        self.config = config or LabelConfig()
        self.renderer = LabelRenderer(self.config)
        logger.info("Label builder initialized")

    def build_label_for_carton(
        self,
        carton: Carton,
        shipment: Shipment,
        carton_index: int
    ) -> ShippingLabel:
        """
        Build a ShippingLabel for a single carton.

        Args:
            carton: Carton object
            shipment: Parent shipment object
            carton_index: Index of this carton in shipment (0-based)

        Returns:
            ShippingLabel object

        Raises:
            ValueError: If carton or shipment data is invalid
        """
        # Validate SSCC
        if not carton.sscc:
            raise ValueError(f"Carton {carton.carton_id} must have an SSCC")

        # Parse SSCC into SSCC object
        sscc = self._parse_sscc(carton.sscc)

        # Parse addresses
        ship_to_parts = self._parse_address(shipment.ship_to_address)
        ship_from_parts = self._parse_address(shipment.ship_from_address)

        # Build contents summary
        contents = self._build_contents_summary(carton)

        # Get order info
        order = shipment.orders[0] if shipment.orders else None
        purchase_order = order.purchase_order if order else None

        # Create ShippingLabel
        label = ShippingLabel(
            sscc=sscc,
            carton_sequence=carton.sequence_number,
            total_cartons=shipment.total_cartons,
            shipment_id=shipment.shipment_id,
            order_id=order.order_id if order else None,
            purchase_order=purchase_order,
            ship_from_name=shipment.ship_from_name,
            ship_from_city=ship_from_parts.get("city"),
            ship_from_state=ship_from_parts.get("state"),
            ship_to_name=shipment.ship_to_name,
            ship_to_address=ship_to_parts.get("street", ""),
            ship_to_city=ship_to_parts.get("city", ""),
            ship_to_state=ship_to_parts.get("state", ""),
            ship_to_postal=ship_to_parts.get("postal", ""),
            carrier_name=self._get_carrier_name(shipment.carrier_code),
            service_level=shipment.service_level,
            tracking_number=shipment.tracking_number,
            weight=carton.weight or carton.calculate_weight(),
            item_count=carton.get_total_units(),
            contents_summary=contents if self.config.show_contents else None,
            ship_date=shipment.ship_date.date() if shipment.ship_date else None
        )

        logger.debug(f"Built label for carton {carton.carton_id}")
        return label

    def build_labels_for_shipment(
        self,
        shipment_package: ShipmentPackage
    ) -> List[ShippingLabel]:
        """
        Build ShippingLabels for all cartons in a shipment.

        Args:
            shipment_package: Complete shipment package

        Returns:
            List of ShippingLabel objects
        """
        shipment = shipment_package.shipment
        labels = []

        logger.info(f"Building labels for shipment {shipment.shipment_id}")

        for i, carton in enumerate(shipment.cartons):
            label = self.build_label_for_carton(carton, shipment, i)
            labels.append(label)

        logger.info(f"Built {len(labels)} labels")
        return labels

    def render_labels_for_shipment(
        self,
        shipment_package: ShipmentPackage,
        output_dir: str
    ) -> LabelBatch:
        """
        Build and render labels for all cartons in a shipment.

        Args:
            shipment_package: Complete shipment package
            output_dir: Directory to save label files

        Returns:
            LabelBatch with metadata about rendered labels
        """
        shipment = shipment_package.shipment
        logger.info(f"Rendering labels for shipment {shipment.shipment_id}")

        # Build labels
        labels = self.build_labels_for_shipment(shipment_package)

        # Render labels
        output_paths = self.renderer.render_batch(labels, output_dir)

        # Build LabelBatch metadata
        label_outputs = []
        for label, output_path in zip(labels, output_paths):
            output = LabelRenderOutput(
                sscc=label.sscc.get_full_sscc(),
                carton_id=f"CTN-{label.carton_sequence:04d}",
                file_path=output_path,
                file_format="PDF",
                generated_at=datetime.utcnow().isoformat()
            )
            label_outputs.append(output)

        batch = LabelBatch(
            shipment_id=shipment.shipment_id,
            labels=label_outputs,
            total_labels=len(label_outputs),
            batch_generated_at=datetime.utcnow().isoformat()
        )

        logger.info(f"Label batch complete: {batch.total_labels} labels")
        return batch

    def _parse_sscc(self, sscc_string: str) -> SSCC:
        """
        Parse SSCC string into SSCC object.

        Args:
            sscc_string: 18-digit SSCC string

        Returns:
            SSCC object

        Raises:
            ValueError: If SSCC format is invalid
        """
        if len(sscc_string) != 18:
            raise ValueError(f"SSCC must be 18 digits, got {len(sscc_string)}")

        return SSCC(
            extension_digit=sscc_string[0],
            company_prefix=sscc_string[1:8],
            serial_reference=sscc_string[8:17],
            check_digit=sscc_string[17]
        )

    def _parse_address(self, address_string: str) -> dict:
        """
        Parse address string into components.

        Simple parser for comma-separated addresses.
        Format: "Street, City, State ZIP"

        Args:
            address_string: Address as string

        Returns:
            Dictionary with address components
        """
        parts = {}

        if not address_string:
            return parts

        # Split by comma
        segments = [s.strip() for s in address_string.split(",")]

        if len(segments) >= 1:
            parts["street"] = segments[0]

        if len(segments) >= 2:
            parts["city"] = segments[1]

        if len(segments) >= 3:
            # Last segment should be "State ZIP"
            last = segments[-1].strip()
            tokens = last.split()
            if len(tokens) >= 2:
                parts["state"] = tokens[0]
                parts["postal"] = tokens[1]
            elif len(tokens) == 1:
                # Could be just state or just postal
                if tokens[0].isdigit():
                    parts["postal"] = tokens[0]
                else:
                    parts["state"] = tokens[0]

        return parts

    def _build_contents_summary(self, carton: Carton) -> List[str]:
        """
        Build human-readable contents summary.

        Args:
            carton: Carton object

        Returns:
            List of strings describing contents
        """
        summary = []

        for item in carton.items:
            # Format: "SKU: Description (Qty)"
            text = f"{item.sku}: {item.description} ({item.quantity} {item.uom})"
            summary.append(text)

        return summary

    def _get_carrier_name(self, carrier_code: Optional[str]) -> Optional[str]:
        """
        Convert carrier SCAC code to friendly name.

        Args:
            carrier_code: SCAC carrier code

        Returns:
            Friendly carrier name
        """
        if not carrier_code:
            return None

        # Common SCAC to name mappings
        carrier_map = {
            "UPSN": "UPS",
            "FDEG": "FedEx Ground",
            "FDXE": "FedEx Express",
            "FXFE": "FedEx Freight",
            "FEDX": "FedEx",
            "UPGF": "UPS Freight",
            "RDWY": "YRC Freight",
            "DHRN": "DHL",
            "USPS": "USPS"
        }

        return carrier_map.get(carrier_code, carrier_code)


def create_label_builder(config: Optional[LabelConfig] = None) -> LabelBuilder:
    """
    Convenience function to create a label builder.

    Args:
        config: Label configuration (optional)

    Returns:
        LabelBuilder instance
    """
    return LabelBuilder(config)
