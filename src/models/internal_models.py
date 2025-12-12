"""
Internal Business Models
========================
Core data structures used during processing.
These represent the normalized business objects after input validation.

Author: Integration Engineering Team
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class PackagingLevel(str, Enum):
    """
    GS1/EDI packaging hierarchy levels.
    Maps to HL segment LIN01 codes in EDI 856.
    """
    SHIPMENT = "S"  # Top-level shipment
    ORDER = "O"     # Customer order within shipment
    TARE = "T"      # Carton/container (tare = packaging)
    PACK = "P"      # Pack level (inner pack)
    ITEM = "I"      # Individual item/SKU


class Item(BaseModel):
    """
    Represents a single SKU with quantity.
    Used within cartons and orders.
    """
    sku: str = Field(..., description="Stock keeping unit")
    description: str = Field(..., description="Item description")
    quantity: int = Field(..., description="Quantity of this SKU", ge=1)
    uom: str = Field(default="EA", description="Unit of measure")
    unit_weight: Optional[float] = Field(None, description="Weight per unit (lbs)", ge=0)

    # Optional fields for EDI
    upc: Optional[str] = Field(None, description="UPC/GTIN barcode")
    vendor_part_number: Optional[str] = Field(None, description="Vendor SKU")

    def get_total_weight(self) -> Optional[float]:
        """Calculate total weight for this item quantity."""
        if self.unit_weight is not None:
            return self.quantity * self.unit_weight
        return None


class Carton(BaseModel):
    """
    Represents a single carton/case in the shipment.
    Each carton has a unique SSCC and contains one or more items.
    """
    carton_id: str = Field(..., description="Internal carton identifier")
    sscc: Optional[str] = Field(None, description="GS1 SSCC-18 serial shipping container code")
    sequence_number: int = Field(..., description="Carton sequence in shipment", ge=1)

    items: List[Item] = Field(..., description="Items packed in this carton", min_items=1)

    # Physical attributes
    weight: Optional[float] = Field(None, description="Total carton weight (lbs)", ge=0)
    length: Optional[float] = Field(None, description="Length (inches)")
    width: Optional[float] = Field(None, description="Width (inches)")
    height: Optional[float] = Field(None, description="Height (inches)")

    # Carton type
    packaging_code: str = Field(default="CTN", description="Packaging type code (CTN, PLT, etc.)")

    def calculate_weight(self) -> float:
        """
        Calculate total carton weight from items.
        Returns 0 if no weights are available.
        """
        total = 0.0
        for item in self.items:
            item_weight = item.get_total_weight()
            if item_weight:
                total += item_weight
        return total

    def get_total_units(self) -> int:
        """Get total unit count across all items in carton."""
        return sum(item.quantity for item in self.items)


class Order(BaseModel):
    """
    Represents a customer order within a shipment.
    An order can span multiple cartons.
    """
    order_id: str = Field(..., description="Unique order identifier")
    purchase_order: str = Field(..., description="Customer PO number")

    # References to cartons
    carton_ids: List[str] = Field(default_factory=list, description="List of carton IDs for this order")

    # Customer information
    customer_account: Optional[str] = Field(None, description="Customer account number")

    # Order metadata
    order_date: Optional[datetime] = Field(None, description="Original order date")


class Shipment(BaseModel):
    """
    Top-level shipment structure.
    Contains one or more orders and their associated cartons.
    """
    shipment_id: str = Field(..., description="Unique shipment identifier")
    ship_date: datetime = Field(..., description="Actual or scheduled ship date")

    # Addresses
    ship_from_name: str = Field(..., description="Ship from location name")
    ship_from_address: str = Field(..., description="Ship from full address")
    ship_to_name: str = Field(..., description="Ship to location name")
    ship_to_address: str = Field(..., description="Ship to full address")

    # Carrier information
    carrier_code: Optional[str] = Field(None, description="SCAC carrier code")
    service_level: Optional[str] = Field(None, description="Service level description")
    tracking_number: Optional[str] = Field(None, description="Master tracking/PRO number")

    # Hierarchical data
    orders: List[Order] = Field(
        default_factory=list,
        description="Orders in this shipment",
    )
    cartons: List[Carton] = Field(
        default_factory=list,
        description="All cartons in shipment",
    )

    # Totals
    total_weight: Optional[float] = Field(None, description="Total shipment weight (lbs)")
    total_cartons: int = Field(
        default=0,
        description="Total number of cartons",
    )

    def calculate_totals(self):
        """Calculate and update shipment totals from cartons."""
        self.total_cartons = len(self.cartons)

        # Calculate total weight
        total_weight = 0.0
        for carton in self.cartons:
            if carton.weight:
                total_weight += carton.weight
            else:
                total_weight += carton.calculate_weight()

        self.total_weight = total_weight if total_weight > 0 else None


class ShipmentPackage(BaseModel):
    """
    Complete package of shipment data ready for ASN generation.
    This is the final normalized structure before EDI transformation.
    """
    shipment: Shipment = Field(..., description="The shipment data")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of generation")

    # Metadata
    sender_id: Optional[str] = Field(None, description="EDI sender ID (ISA06)")
    receiver_id: Optional[str] = Field(None, description="EDI receiver ID (ISA08)")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment": {
                    "shipment_id": "SHIP-2025-001",
                    "ship_date": "2025-12-15T08:00:00Z",
                    "ship_from_name": "ACME Warehouse",
                    "ship_from_address": "123 Industrial Blvd, Dallas, TX 75201",
                    "ship_to_name": "Retail Store #42",
                    "ship_to_address": "456 Commerce St, Austin, TX 78701",
                    "carrier_code": "UPSN",
                    "service_level": "Ground",
                    "total_cartons": 2,
                    "orders": [
                        {
                            "order_id": "ORD-2025-001",
                            "purchase_order": "PO-12345",
                            "carton_ids": ["CTN-001", "CTN-002"]
                        }
                    ],
                    "cartons": [
                        {
                            "carton_id": "CTN-001",
                            "sequence_number": 1,
                            "items": [
                                {
                                    "sku": "WIDGET-A",
                                    "description": "Premium Widget",
                                    "quantity": 50,
                                    "unit_weight": 0.5
                                }
                            ]
                        }
                    ]
                }
            }
        }
