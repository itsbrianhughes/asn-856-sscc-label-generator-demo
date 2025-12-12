"""
Cartonization Configuration
============================
Configuration for cartonization rules and packing logic.

Author: Integration Engineering Team
"""

from pydantic import BaseModel, Field
from typing import Optional


class CartonizationConfig(BaseModel):
    """
    Configuration for cartonization logic.
    Defines rules for how items are packed into cartons.
    """

    # Basic packing rules
    max_items_per_carton: int = Field(
        default=50,
        description="Maximum number of items (units) per carton",
        ge=1
    )

    max_weight_per_carton: Optional[float] = Field(
        default=50.0,
        description="Maximum weight per carton in lbs (None = no limit)",
        ge=0
    )

    # Carton physical attributes (defaults)
    default_carton_length: float = Field(
        default=18.0,
        description="Default carton length in inches",
        ge=0
    )

    default_carton_width: float = Field(
        default=12.0,
        description="Default carton width in inches",
        ge=0
    )

    default_carton_height: float = Field(
        default=10.0,
        description="Default carton height in inches",
        ge=0
    )

    # Packing strategy
    pack_by_sku: bool = Field(
        default=False,
        description="If True, try to keep same SKUs together in cartons"
    )

    single_item_cartons: bool = Field(
        default=False,
        description="If True, each line item gets its own carton(s)"
    )

    # Carton identification
    carton_id_prefix: str = Field(
        default="CTN",
        description="Prefix for generated carton IDs"
    )

    carton_id_padding: int = Field(
        default=4,
        description="Zero-padding for carton ID numbers",
        ge=1
    )

    # SSCC configuration
    sscc_company_prefix: str = Field(
        default="0614141",
        description="GS1 company prefix for SSCC generation"
    )

    sscc_extension_digit: str = Field(
        default="0",
        description="SSCC extension digit"
    )

    sscc_serial_start: int = Field(
        default=1,
        description="Starting serial number for SSCC generation",
        ge=0
    )

    def get_carton_id(self, sequence: int) -> str:
        """
        Generate a carton ID based on sequence number.

        Args:
            sequence: Carton sequence number (1-based)

        Returns:
            Formatted carton ID (e.g., "CTN-0001")
        """
        return f"{self.carton_id_prefix}-{str(sequence).zfill(self.carton_id_padding)}"


# Default configuration instance
DEFAULT_CARTONIZATION_CONFIG = CartonizationConfig()
