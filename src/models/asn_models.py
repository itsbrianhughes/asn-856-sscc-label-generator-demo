"""
ASN (EDI 856) Data Models
=========================
Structures specific to EDI 856 Advance Ship Notice generation.
Maps internal business objects to EDI hierarchical levels.

Author: Integration Engineering Team
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, ClassVar
from datetime import datetime
from enum import Enum


class HLLevelCode(str, Enum):
    """
    HL (Hierarchical Level) codes for EDI 856.
    Defines the type of each level in the hierarchy.
    """
    SHIPMENT = "S"  # Shipment level (top)
    ORDER = "O"     # Order level
    TARE = "T"      # Tare/Carton level (packaging)
    PACK = "P"      # Pack level (inner pack)
    ITEM = "I"      # Item level (SKU)


class SegmentType(str, Enum):
    """Common EDI 856 segment identifiers."""
    ISA = "ISA"  # Interchange Control Header
    GS = "GS"    # Functional Group Header
    ST = "ST"    # Transaction Set Header
    BSN = "BSN"  # Beginning Segment for Ship Notice
    HL = "HL"    # Hierarchical Level
    TD1 = "TD1"  # Carrier Details (Quantity and Weight)
    TD5 = "TD5"  # Carrier Details (Routing Sequence)
    REF = "REF"  # Reference Identification
    DTM = "DTM"  # Date/Time Reference
    N1 = "N1"    # Party Identification
    N3 = "N3"    # Party Location
    N4 = "N4"    # Geographic Location
    LIN = "LIN"  # Item Identification
    SN1 = "SN1"  # Item Detail (Shipment)
    CTT = "CTT"  # Transaction Totals
    SE = "SE"    # Transaction Set Trailer
    GE = "GE"    # Functional Group Trailer
    IEA = "IEA"  # Interchange Control Trailer


class HierarchicalLevel(BaseModel):
    """
    Represents an HL segment in EDI 856.
    Each HL defines a node in the shipment hierarchy.
    """
    hl_id: str = Field(..., description="Unique hierarchical ID number")
    parent_hl_id: Optional[str] = Field(None, description="Parent HL ID (None for top level)")
    level_code: HLLevelCode = Field(..., description="Type of hierarchical level")
    child_code: Optional[str] = Field(None, description="1 = has children, 0 = no children")

    # Associated data for this level
    data: Dict[str, Any] = Field(default_factory=dict, description="Level-specific data")

    # Child levels
    children: List["HierarchicalLevel"] = Field(default_factory=list, description="Child HL segments")

    class Config:
        use_enum_values = True


class ASNHeader(BaseModel):
    """
    Header information for the ASN (BSN segment and envelope data).
    """
    # BSN segment fields
    transaction_set_purpose: str = Field(default="00", description="00=Original, 01=Cancellation")
    shipment_id: str = Field(..., description="Unique shipment identification number")
    shipment_date: datetime = Field(..., description="Ship date/time")
    ship_time: Optional[str] = Field(None, description="Ship time (HHMM format)")

    # ISA/GS envelope information
    sender_id: str = Field(..., description="Sender's EDI ID (ISA06/GS02)")
    receiver_id: str = Field(..., description="Receiver's EDI ID (ISA08/GS03)")
    control_number: str = Field(..., description="Control number for this transaction")

    # Optional identifiers
    isa_qualifier_sender: str = Field(default="ZZ", description="ISA05 Sender ID qualifier")
    isa_qualifier_receiver: str = Field(default="ZZ", description="ISA07 Receiver ID qualifier")


class ASNSummary(BaseModel):
    """
    Summary/totals for the ASN (CTT segment).
    """
    total_line_items: int = Field(..., description="Total number of line items", ge=0)
    total_quantity: Optional[int] = Field(None, description="Total quantity shipped")
    total_weight: Optional[float] = Field(None, description="Total weight (lbs)")
    total_cartons: Optional[int] = Field(None, description="Total number of cartons")


class ASNDocument(BaseModel):
    """
    Complete EDI 856 ASN document structure.
    Contains header, hierarchical levels, and summary.
    """
    header: ASNHeader = Field(..., description="ASN header information")
    hierarchy: HierarchicalLevel = Field(..., description="Root hierarchical level (shipment)")
    summary: ASNSummary = Field(..., description="Transaction summary totals")

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")

    # Configuration
    segment_terminator: str = Field(default="~", description="EDI segment terminator")
    element_separator: str = Field(default="*", description="EDI element separator")
    subelement_separator: str = Field(default=":", description="EDI sub-element separator")

    def get_control_numbers(self) -> Dict[str, str]:
        """
        Generate control numbers for ISA/GS/ST envelopes.
        In production, these would come from a sequence service.
        """
        base = self.header.control_number
        return {
            "isa_control": base.zfill(9),      # ISA13: 9 digits
            "gs_control": base.zfill(9),       # GS06: 9 digits
            "st_control": base.zfill(4)        # ST02: 4 digits
        }


class ReferenceIdentification(BaseModel):
    """
    Represents a REF segment (reference identification).
    Used for PO numbers, BOL numbers, tracking numbers, etc.
    """
    qualifier: str = Field(..., description="Reference identifier qualifier")
    reference_id: str = Field(..., description="Reference identification value")
    description: Optional[str] = Field(None, description="Reference description")

    # Common qualifiers
    QUALIFIER_PO: ClassVar[str] = "PO"          # Purchase Order
    QUALIFIER_BOL: ClassVar[str] = "BM"         # Bill of Lading
    QUALIFIER_PRO: ClassVar[str] = "CN"         # Carrier PRO Number
    QUALIFIER_TRACKING: ClassVar[str] = "CT"    # Tracking Number
    QUALIFIER_SSCC: ClassVar[str] = "0J"        # SSCC (Serial Shipping Container Code)


class PartyIdentification(BaseModel):
    """
    Represents a party (N1/N3/N4 segments).
    Used for ship-from, ship-to, buyer, seller, etc.
    """
    entity_code: str = Field(..., description="Entity identifier code")
    name: str = Field(..., description="Party name")

    # Address components (N3/N4)
    address_line1: Optional[str] = Field(None, description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country code")

    # Common entity codes
    ENTITY_SHIP_FROM: ClassVar[str] = "SF"  # Ship From
    ENTITY_SHIP_TO: ClassVar[str] = "ST"    # Ship To
    ENTITY_BUYER: ClassVar[str] = "BY"      # Buyer
    ENTITY_SELLER: ClassVar[str] = "SE"     # Seller


class CarrierDetail(BaseModel):
    """
    Represents carrier information (TD5 segment).
    """
    routing_sequence: str = Field(default="B", description="Routing sequence (B=Both origin and destination)")
    id_code_qualifier: Optional[str] = Field(None, description="ID code qualifier (2=SCAC)")
    carrier_code: Optional[str] = Field(None, description="Carrier alpha code (SCAC)")
    service_level: Optional[str] = Field(None, description="Service level description")
    routing: Optional[str] = Field(None, description="Routing details")


class PackagingDetail(BaseModel):
    """
    Represents packaging information (TD1 segment).
    """
    packaging_code: Optional[str] = Field(None, description="Packaging code (CTN, PLT, etc.)")
    lading_quantity: Optional[int] = Field(None, description="Number of units")
    weight_qualifier: str = Field(default="G", description="Weight qualifier (G=Gross Weight)")
    weight: Optional[float] = Field(None, description="Weight value")
    weight_uom: str = Field(default="LB", description="Weight unit of measure")

    # Dimensions (optional)
    volume: Optional[float] = Field(None, description="Volume")
    volume_uom: Optional[str] = Field(None, description="Volume unit of measure")


class ItemIdentification(BaseModel):
    """
    Represents an item (LIN segment).
    """
    assigned_identification: Optional[str] = Field(None, description="Line item ID")
    product_id_qualifier: str = Field(..., description="Product ID qualifier (SK=SKU, UP=UPC)")
    product_id: str = Field(..., description="Product identifier value")

    # Common qualifiers
    QUALIFIER_SKU: ClassVar[str] = "SK"       # Stock Keeping Unit
    QUALIFIER_UPC: ClassVar[str] = "UP"       # UPC
    QUALIFIER_GTIN: ClassVar[str] = "UK"      # GTIN
    QUALIFIER_VENDOR: ClassVar[str] = "VN"    # Vendor Part Number


class ItemDetail(BaseModel):
    """
    Represents item quantity (SN1 segment).
    """
    assigned_identification: Optional[str] = Field(None, description="Line item ID")
    quantity: int = Field(..., description="Quantity shipped", ge=0)
    uom: str = Field(default="EA", description="Unit of measure")


# Update forward references
HierarchicalLevel.model_rebuild()
