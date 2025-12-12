"""
Input Data Models
=================
Defines the structure for incoming order data (JSON or CSV).
These models represent the external API contract.

Author: Integration Engineering Team
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date


class Address(BaseModel):
    """
    Represents a shipping address (ship-to or ship-from).
    """
    name: str = Field(..., description="Company or location name")
    address_line1: str = Field(..., description="Street address line 1")
    address_line2: Optional[str] = Field(None, description="Street address line 2")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/Province code (2-letter)")
    postal_code: str = Field(..., description="ZIP or postal code")
    country: str = Field(default="US", description="ISO country code")

    @validator('state')
    def validate_state(cls, v):
        """Ensure state code is uppercase and 2 characters."""
        if len(v) != 2:
            raise ValueError("State must be 2-letter code")
        return v.upper()


class OrderLineItem(BaseModel):
    """
    Represents a single line item in an order.
    """
    line_number: int = Field(..., description="Line sequence number", ge=1)
    sku: str = Field(..., description="Stock keeping unit / item number")
    description: str = Field(..., description="Human-readable item description")
    quantity: int = Field(..., description="Quantity ordered", ge=1)
    uom: str = Field(default="EA", description="Unit of measure (EA, CS, etc.)")
    unit_weight: Optional[float] = Field(None, description="Weight per unit in lbs", ge=0)

    @validator('sku')
    def validate_sku(cls, v):
        """Ensure SKU is not empty and trimmed."""
        if not v or not v.strip():
            raise ValueError("SKU cannot be empty")
        return v.strip()


class OrderInput(BaseModel):
    """
    The top-level order input structure.
    This is what clients submit via JSON or CSV transformation.
    """
    order_id: str = Field(..., description="Unique order identifier")
    purchase_order: str = Field(..., description="Customer PO number")
    ship_date: date = Field(..., description="Scheduled ship date")

    ship_from: Address = Field(..., description="Origin address")
    ship_to: Address = Field(..., description="Destination address")

    carrier_code: Optional[str] = Field(None, description="SCAC carrier code (e.g., UPSN, FEDX)")
    service_level: Optional[str] = Field(None, description="Service level (e.g., Ground, 2-Day)")

    items: List[OrderLineItem] = Field(
        ..., description="List of order line items"
    )

    # Optional metadata
    customer_account: Optional[str] = Field(None, description="Customer account number")
    notes: Optional[str] = Field(None, description="Special instructions or notes")

    @validator('items')
    def validate_unique_line_numbers(cls, v):
        """Ensure line numbers are unique."""
        line_numbers = [item.line_number for item in v]
        if len(line_numbers) != len(set(line_numbers)):
            raise ValueError("Line numbers must be unique")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD-2025-001",
                "purchase_order": "PO-12345",
                "ship_date": "2025-12-15",
                "ship_from": {
                    "name": "ACME Warehouse",
                    "address_line1": "123 Industrial Blvd",
                    "city": "Dallas",
                    "state": "TX",
                    "postal_code": "75201",
                    "country": "US"
                },
                "ship_to": {
                    "name": "Retail Store #42",
                    "address_line1": "456 Commerce St",
                    "city": "Austin",
                    "state": "TX",
                    "postal_code": "78701",
                    "country": "US"
                },
                "carrier_code": "UPSN",
                "service_level": "Ground",
                "items": [
                    {
                        "line_number": 1,
                        "sku": "WIDGET-A",
                        "description": "Premium Widget Type A",
                        "quantity": 50,
                        "uom": "EA",
                        "unit_weight": 0.5
                    },
                    {
                        "line_number": 2,
                        "sku": "GADGET-B",
                        "description": "Standard Gadget Type B",
                        "quantity": 30,
                        "uom": "EA",
                        "unit_weight": 1.2
                    }
                ]
            }
        }
