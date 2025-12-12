"""
Label and SSCC Models
=====================
Data structures for GS1 SSCC-18 generation and shipping label rendering.

Author: Integration Engineering Team
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date
from enum import Enum


class SSCCFormat(str, Enum):
    """SSCC format options."""
    SSCC_18 = "SSCC-18"  # Full 18-digit format (standard)
    SSCC_17 = "SSCC-17"  # 17-digit without check digit


class BarcodeType(str, Enum):
    """Supported barcode formats."""
    GS1_128 = "GS1-128"        # Standard GS1-128 (Code 128)
    CODE_128 = "CODE128"        # Standard Code 128
    QR_CODE = "QR"              # QR Code (2D)


class LabelSize(str, Enum):
    """Standard label sizes."""
    LABEL_4X6 = "4x6"           # 4" x 6" (standard shipping label)
    LABEL_4X8 = "4x8"           # 4" x 8"
    LABEL_6X8 = "6x8"           # 6" x 8"
    LETTER = "8.5x11"           # Standard letter size


class SSCC(BaseModel):
    """
    Represents a GS1 SSCC-18 (Serial Shipping Container Code).

    Structure: (Extension Digit) + (GS1 Company Prefix) + (Serial Reference) + (Check Digit)
    Total: 18 digits

    Example: 0 0614141 123456789 8
             ^ ^       ^         ^
             | |       |         Check digit (mod 10)
             | |       Serial reference (9 digits)
             | GS1 Company Prefix (7 digits)
             Extension digit (0-9)
    """
    extension_digit: str = Field(..., description="Extension digit (0-9)", min_length=1, max_length=1)
    company_prefix: str = Field(..., description="GS1 Company Prefix (7-10 digits)")
    serial_reference: str = Field(..., description="Serial reference number")
    check_digit: str = Field(..., description="Calculated check digit", min_length=1, max_length=1)

    @validator('extension_digit', 'check_digit')
    def validate_digit(cls, v):
        """Ensure value is a single digit."""
        if not v.isdigit() or len(v) != 1:
            raise ValueError("Must be a single digit (0-9)")
        return v

    @validator('company_prefix')
    def validate_company_prefix(cls, v):
        """Ensure company prefix is numeric and correct length."""
        if not v.isdigit():
            raise ValueError("Company prefix must be numeric")
        if len(v) < 7 or len(v) > 10:
            raise ValueError("Company prefix must be 7-10 digits")
        return v

    @validator('serial_reference')
    def validate_serial_reference(cls, v):
        """Ensure serial reference is numeric."""
        if not v.isdigit():
            raise ValueError("Serial reference must be numeric")
        return v

    def get_full_sscc(self) -> str:
        """
        Returns the complete 18-digit SSCC.
        Format: extension + company_prefix + serial_reference + check_digit
        """
        return f"{self.extension_digit}{self.company_prefix}{self.serial_reference}{self.check_digit}"

    def get_sscc_without_check(self) -> str:
        """Returns the 17-digit SSCC without check digit."""
        return f"{self.extension_digit}{self.company_prefix}{self.serial_reference}"

    def get_formatted_sscc(self, separator: str = " ") -> str:
        """
        Returns SSCC with visual separators for readability.
        Example: "0 0614141 123456789 8"
        """
        return f"{self.extension_digit}{separator}{self.company_prefix}{separator}{self.serial_reference}{separator}{self.check_digit}"

    def get_gs1_application_identifier(self) -> str:
        """
        Returns the SSCC with GS1 Application Identifier (AI) prefix.
        AI (00) is used for SSCC in GS1-128 barcodes.
        Format: (00)006141411234567898
        """
        return f"(00){self.get_full_sscc()}"


class SSCCConfig(BaseModel):
    """
    Configuration for SSCC generation.
    """
    company_prefix: str = Field(..., description="GS1 Company Prefix (7-10 digits)")
    extension_digit: str = Field(default="0", description="Default extension digit")
    serial_start: int = Field(default=1, description="Starting serial number", ge=0)
    serial_padding: int = Field(default=9, description="Zero-padding for serial reference", ge=1)

    @validator('company_prefix')
    def validate_company_prefix(cls, v):
        """Validate company prefix format."""
        if not v.isdigit():
            raise ValueError("Company prefix must be numeric")
        if len(v) < 7 or len(v) > 10:
            raise ValueError("Company prefix must be 7-10 digits")
        return v


class ShippingLabel(BaseModel):
    """
    Complete shipping label data structure.
    Contains all information needed to render a carton label.
    """
    # Carton identification
    sscc: SSCC = Field(..., description="SSCC for this carton")
    carton_sequence: int = Field(..., description="Carton X of Y", ge=1)
    total_cartons: int = Field(..., description="Total cartons in shipment", ge=1)

    # Shipment information
    shipment_id: str = Field(..., description="Shipment identifier")
    order_id: Optional[str] = Field(None, description="Order identifier")
    purchase_order: Optional[str] = Field(None, description="Customer PO number")

    # Ship from/to
    ship_from_name: str = Field(..., description="Origin location name")
    ship_from_city: Optional[str] = Field(None, description="Origin city")
    ship_from_state: Optional[str] = Field(None, description="Origin state")

    ship_to_name: str = Field(..., description="Destination name")
    ship_to_address: str = Field(..., description="Destination street address")
    ship_to_city: str = Field(..., description="Destination city")
    ship_to_state: str = Field(..., description="Destination state")
    ship_to_postal: str = Field(..., description="Destination postal code")

    # Carrier information
    carrier_name: Optional[str] = Field(None, description="Carrier name (UPS, FedEx, etc.)")
    service_level: Optional[str] = Field(None, description="Service level (Ground, Express, etc.)")
    tracking_number: Optional[str] = Field(None, description="Tracking number")

    # Carton details
    weight: Optional[float] = Field(None, description="Carton weight (lbs)")
    item_count: Optional[int] = Field(None, description="Total items in carton")

    # Contents summary (for human readability)
    contents_summary: Optional[List[str]] = Field(None, description="Human-readable item list")

    # Dates
    ship_date: Optional[date] = Field(None, description="Ship date")

    @validator('carton_sequence')
    def validate_sequence(cls, v, values):
        """Ensure carton sequence doesn't exceed total."""
        if 'total_cartons' in values and v > values['total_cartons']:
            raise ValueError("Carton sequence cannot exceed total cartons")
        return v


class LabelConfig(BaseModel):
    """
    Configuration for label rendering.
    Controls visual appearance and format.
    """
    # Label size and format
    label_size: LabelSize = Field(default=LabelSize.LABEL_4X6, description="Physical label size")
    output_format: str = Field(default="PDF", description="Output format (PDF, PNG, ZPL)")

    # Barcode settings
    barcode_type: BarcodeType = Field(default=BarcodeType.GS1_128, description="Barcode format")
    barcode_height: int = Field(default=50, description="Barcode height in mm", ge=10)
    include_human_readable: bool = Field(default=True, description="Show human-readable text below barcode")

    # Text settings
    font_size_title: int = Field(default=14, description="Title font size (pt)", ge=8)
    font_size_body: int = Field(default=10, description="Body text font size (pt)", ge=6)
    font_size_small: int = Field(default=8, description="Small text font size (pt)", ge=4)

    # Layout
    margin: float = Field(default=0.25, description="Margin size in inches", ge=0)
    include_logo: bool = Field(default=False, description="Include company logo")
    logo_path: Optional[str] = Field(None, description="Path to logo image")

    # Content options
    show_contents: bool = Field(default=True, description="Show carton contents list")
    max_contents_lines: int = Field(default=5, description="Max lines for contents", ge=1)


class LabelRenderOutput(BaseModel):
    """
    Output from label rendering process.
    """
    sscc: str = Field(..., description="SSCC for this label")
    carton_id: str = Field(..., description="Internal carton identifier")
    file_path: str = Field(..., description="Path to generated label file")
    file_format: str = Field(..., description="File format (PDF, PNG, etc.)")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    generated_at: str = Field(..., description="Generation timestamp (ISO format)")


class LabelBatch(BaseModel):
    """
    Batch of labels for a complete shipment.
    """
    shipment_id: str = Field(..., description="Shipment identifier")
    labels: List[LabelRenderOutput] = Field(..., description="All labels in batch")
    total_labels: int = Field(..., description="Total number of labels generated", ge=0)
    batch_generated_at: str = Field(..., description="Batch generation timestamp")

    # Batch output
    manifest_path: Optional[str] = Field(None, description="Path to JSON manifest file")
    archive_path: Optional[str] = Field(None, description="Path to ZIP archive of all labels")
