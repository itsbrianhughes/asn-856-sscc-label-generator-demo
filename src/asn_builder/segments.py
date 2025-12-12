"""
EDI Segment Generators
======================
Generates individual EDI X12 segments for 856 ASN documents.

Each segment follows X12 standards for ASN/856 transaction sets.

Author: Integration Engineering Team
"""

from datetime import datetime
from typing import List, Optional
import logging

from src.models.internal_models import Shipment, Order, Carton, Item
from src.models.asn_models import ASNHeader

logger = logging.getLogger(__name__)


class SegmentGenerator:
    """
    Generates EDI X12 segments for 856 ASN documents.

    All methods return segment strings WITHOUT terminators.
    The formatter will add terminators later.
    """

    def __init__(self, element_separator: str = "*", subelement_separator: str = ":"):
        """
        Initialize segment generator.

        Args:
            element_separator: Element separator (default: "*")
            subelement_separator: Sub-element separator (default: ":")
        """
        self.element_sep = element_separator
        self.subelement_sep = subelement_separator

    # === ENVELOPE SEGMENTS ===

    def generate_isa(
        self,
        sender_id: str,
        receiver_id: str,
        control_number: str,
        sender_qualifier: str = "ZZ",
        receiver_qualifier: str = "ZZ",
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate ISA (Interchange Control Header) segment.

        ISA format:
        ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *YYMMDD*HHMM*U*00401*000000001*0*P*:~

        Args:
            sender_id: Sender identification (ISA06) - 15 chars padded
            receiver_id: Receiver identification (ISA08) - 15 chars padded
            control_number: Interchange control number (ISA13) - 9 digits
            sender_qualifier: Sender ID qualifier (ISA05)
            receiver_qualifier: Receiver ID qualifier (ISA07)
            timestamp: Interchange date/time (defaults to now)

        Returns:
            ISA segment string
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Format date and time
        date_str = timestamp.strftime("%y%m%d")  # YYMMDD
        time_str = timestamp.strftime("%H%M")    # HHMM

        # Pad sender and receiver IDs to 15 characters
        sender_padded = sender_id.ljust(15)[:15]
        receiver_padded = receiver_id.ljust(15)[:15]

        # Pad control number to 9 digits
        control_padded = control_number.zfill(9)

        # Build ISA segment
        isa = (
            f"ISA"
            f"{self.element_sep}00{self.element_sep}          "  # ISA01-02: Authorization (no security)
            f"{self.element_sep}00{self.element_sep}          "  # ISA03-04: Security (no security)
            f"{self.element_sep}{sender_qualifier}{self.element_sep}{sender_padded}"  # ISA05-06: Sender
            f"{self.element_sep}{receiver_qualifier}{self.element_sep}{receiver_padded}"  # ISA07-08: Receiver
            f"{self.element_sep}{date_str}"  # ISA09: Date
            f"{self.element_sep}{time_str}"  # ISA10: Time
            f"{self.element_sep}U"  # ISA11: Standards ID (U = US EDI Community)
            f"{self.element_sep}00401"  # ISA12: Version (004010)
            f"{self.element_sep}{control_padded}"  # ISA13: Control number
            f"{self.element_sep}0"  # ISA14: Acknowledgment requested (0 = no)
            f"{self.element_sep}P"  # ISA15: Usage indicator (P = Production)
            f"{self.element_sep}{self.subelement_sep}"  # ISA16: Sub-element separator
        )

        logger.debug(f"Generated ISA segment with control number {control_padded}")
        return isa

    def generate_gs(
        self,
        sender_code: str,
        receiver_code: str,
        control_number: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate GS (Functional Group Header) segment.

        GS format:
        GS*SH*SENDER*RECEIVER*YYYYMMDD*HHMM*1*X*004010~

        Args:
            sender_code: Application sender code (GS02)
            receiver_code: Application receiver code (GS03)
            control_number: Group control number (GS06)
            timestamp: Group date/time (defaults to now)

        Returns:
            GS segment string
        """
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y%m%d")  # YYYYMMDD
        time_str = timestamp.strftime("%H%M")     # HHMM
        control_padded = control_number.zfill(9)

        gs = (
            f"GS"
            f"{self.element_sep}SH"  # GS01: Functional ID (SH = Ship Notice/Manifest)
            f"{self.element_sep}{sender_code}"  # GS02: Sender code
            f"{self.element_sep}{receiver_code}"  # GS03: Receiver code
            f"{self.element_sep}{date_str}"  # GS04: Date
            f"{self.element_sep}{time_str}"  # GS05: Time
            f"{self.element_sep}{control_padded}"  # GS06: Control number
            f"{self.element_sep}X"  # GS07: Responsible agency (X = ASC X12)
            f"{self.element_sep}004010"  # GS08: Version (004010)
        )

        logger.debug(f"Generated GS segment with control number {control_padded}")
        return gs

    def generate_ge(self, transaction_count: int, control_number: str) -> str:
        """
        Generate GE (Functional Group Trailer) segment.

        Args:
            transaction_count: Number of transaction sets (ST/SE pairs)
            control_number: Group control number (must match GS06)

        Returns:
            GE segment string
        """
        control_padded = control_number.zfill(9)
        return f"GE{self.element_sep}{transaction_count}{self.element_sep}{control_padded}"

    def generate_iea(self, group_count: int, control_number: str) -> str:
        """
        Generate IEA (Interchange Control Trailer) segment.

        Args:
            group_count: Number of functional groups
            control_number: Interchange control number (must match ISA13)

        Returns:
            IEA segment string
        """
        control_padded = control_number.zfill(9)
        return f"IEA{self.element_sep}{group_count}{self.element_sep}{control_padded}"

    # === TRANSACTION SET SEGMENTS ===

    def generate_st(self, control_number: str) -> str:
        """
        Generate ST (Transaction Set Header) segment.

        Args:
            control_number: Transaction set control number (ST02) - 4 digits

        Returns:
            ST segment string
        """
        control_padded = control_number.zfill(4)
        return f"ST{self.element_sep}856{self.element_sep}{control_padded}"

    def generate_se(self, segment_count: int, control_number: str) -> str:
        """
        Generate SE (Transaction Set Trailer) segment.

        Args:
            segment_count: Number of segments in transaction (including ST/SE)
            control_number: Transaction set control number (must match ST02)

        Returns:
            SE segment string
        """
        control_padded = control_number.zfill(4)
        return f"SE{self.element_sep}{segment_count}{self.element_sep}{control_padded}"

    def generate_bsn(
        self,
        shipment_id: str,
        ship_date: datetime,
        transaction_purpose: str = "00"
    ) -> str:
        """
        Generate BSN (Beginning Segment for Ship Notice) segment.

        Args:
            shipment_id: Shipment identification number (BSN02)
            ship_date: Shipment date/time (BSN03-04)
            transaction_purpose: Purpose code (BSN01) - "00" = Original, "01" = Cancellation

        Returns:
            BSN segment string
        """
        date_str = ship_date.strftime("%Y%m%d")  # YYYYMMDD
        time_str = ship_date.strftime("%H%M")     # HHMM

        return (
            f"BSN"
            f"{self.element_sep}{transaction_purpose}"  # BSN01: Transaction purpose
            f"{self.element_sep}{shipment_id}"  # BSN02: Shipment ID
            f"{self.element_sep}{date_str}"  # BSN03: Date
            f"{self.element_sep}{time_str}"  # BSN04: Time
        )

    # === HIERARCHICAL SEGMENTS ===

    def generate_hl(
        self,
        hl_number: str,
        parent_hl: Optional[str],
        level_code: str,
        has_children: bool = True
    ) -> str:
        """
        Generate HL (Hierarchical Level) segment.

        Args:
            hl_number: Hierarchical ID number (HL01)
            parent_hl: Parent hierarchical ID (HL02) - None for top level
            level_code: Level code (HL03) - S/O/T/P/I
            has_children: Whether this level has children (HL04)

        Returns:
            HL segment string
        """
        parent_str = parent_hl if parent_hl else ""
        child_code = "1" if has_children else "0"

        return (
            f"HL"
            f"{self.element_sep}{hl_number}"
            f"{self.element_sep}{parent_str}"
            f"{self.element_sep}{level_code}"
            f"{self.element_sep}{child_code}"
        )

    # === REFERENCE SEGMENTS ===

    def generate_ref(self, qualifier: str, reference_id: str, description: Optional[str] = None) -> str:
        """
        Generate REF (Reference Identification) segment.

        Common qualifiers:
        - PO: Purchase Order
        - BM: Bill of Lading
        - CN: Carrier PRO Number
        - 0J: SSCC (Serial Shipping Container Code)

        Args:
            qualifier: Reference identifier qualifier (REF01)
            reference_id: Reference identification (REF02)
            description: Optional description (REF03)

        Returns:
            REF segment string
        """
        segment = f"REF{self.element_sep}{qualifier}{self.element_sep}{reference_id}"
        if description:
            segment += f"{self.element_sep}{description}"
        return segment

    def generate_dtm(self, qualifier: str, date_value: datetime, time_code: str = "204") -> str:
        """
        Generate DTM (Date/Time Reference) segment.

        Common qualifiers:
        - 011: Ship date
        - 017: Estimated delivery date

        Args:
            qualifier: Date/time qualifier (DTM01)
            date_value: Date/time value (DTM02)
            time_code: Time format code (DTM03) - "204" = CCYYMMDD

        Returns:
            DTM segment string
        """
        date_str = date_value.strftime("%Y%m%d")  # CCYYMMDD
        return f"DTM{self.element_sep}{qualifier}{self.element_sep}{date_str}{self.element_sep}{time_code}"

    # === PARTY IDENTIFICATION SEGMENTS ===

    def generate_n1(self, entity_code: str, name: str) -> str:
        """
        Generate N1 (Party Identification) segment.

        Common entity codes:
        - SF: Ship From
        - ST: Ship To
        - BY: Buyer
        - SE: Seller

        Args:
            entity_code: Entity identifier code (N101)
            name: Party name (N102)

        Returns:
            N1 segment string
        """
        return f"N1{self.element_sep}{entity_code}{self.element_sep}{name}"

    def generate_n3(self, address_line1: str, address_line2: Optional[str] = None) -> str:
        """
        Generate N3 (Party Location) segment.

        Args:
            address_line1: Address line 1 (N301)
            address_line2: Address line 2 (N302)

        Returns:
            N3 segment string
        """
        segment = f"N3{self.element_sep}{address_line1}"
        if address_line2:
            segment += f"{self.element_sep}{address_line2}"
        return segment

    def generate_n4(self, city: str, state: str, postal_code: str, country: str = "US") -> str:
        """
        Generate N4 (Geographic Location) segment.

        Args:
            city: City name (N401)
            state: State/province code (N402)
            postal_code: Postal code (N403)
            country: Country code (N404)

        Returns:
            N4 segment string
        """
        return f"N4{self.element_sep}{city}{self.element_sep}{state}{self.element_sep}{postal_code}{self.element_sep}{country}"

    # === CARRIER/SHIPMENT DETAILS ===

    def generate_td1(
        self,
        packaging_code: Optional[str] = None,
        lading_quantity: Optional[int] = None,
        weight: Optional[float] = None
    ) -> str:
        """
        Generate TD1 (Carrier Details - Quantity and Weight) segment.

        Args:
            packaging_code: Packaging code (TD101) - e.g., "CTN" for carton
            lading_quantity: Lading quantity (TD102)
            weight: Weight (TD106-07)

        Returns:
            TD1 segment string
        """
        segment = f"TD1"

        # TD101: Packaging code
        segment += f"{self.element_sep}{packaging_code if packaging_code else ''}"

        # TD102: Lading quantity
        segment += f"{self.element_sep}{lading_quantity if lading_quantity else ''}"

        # TD103-105: Skip
        segment += f"{self.element_sep}{self.element_sep}{self.element_sep}"

        # TD106: Weight qualifier (G = Gross weight)
        # TD107: Weight
        # TD108: Unit of measure (LB = pounds)
        if weight is not None:
            segment += f"{self.element_sep}G{self.element_sep}{weight:.2f}{self.element_sep}LB"

        return segment

    def generate_td5(
        self,
        carrier_code: Optional[str] = None,
        routing: str = "B"
    ) -> str:
        """
        Generate TD5 (Carrier Details - Routing Sequence) segment.

        Args:
            carrier_code: Carrier SCAC code (TD502)
            routing: Routing sequence (TD501) - "B" = Origin and Destination Carrier

        Returns:
            TD5 segment string
        """
        segment = f"TD5{self.element_sep}{routing}"

        if carrier_code:
            # TD502: ID Code Qualifier (2 = SCAC)
            # TD503: Carrier code
            segment += f"{self.element_sep}2{self.element_sep}{carrier_code}"

        return segment

    # === ITEM DETAILS ===

    def generate_lin(self, product_id: str, product_id_qualifier: str = "SK") -> str:
        """
        Generate LIN (Item Identification) segment.

        Common qualifiers:
        - SK: Stock Keeping Unit (SKU)
        - UP: UPC
        - UK: GTIN

        Args:
            product_id: Product identifier (LIN03)
            product_id_qualifier: Product ID qualifier (LIN02)

        Returns:
            LIN segment string
        """
        # LIN01: Assigned identification (optional, leave blank)
        return f"LIN{self.element_sep}{self.element_sep}{product_id_qualifier}{self.element_sep}{product_id}"

    def generate_sn1(self, quantity: int, uom: str = "EA") -> str:
        """
        Generate SN1 (Item Detail - Shipment) segment.

        Args:
            quantity: Quantity shipped (SN102)
            uom: Unit of measure (SN103)

        Returns:
            SN1 segment string
        """
        # SN101: Assigned identification (optional, leave blank)
        return f"SN1{self.element_sep}{self.element_sep}{quantity}{self.element_sep}{uom}"

    # === SUMMARY SEGMENTS ===

    def generate_ctt(self, line_count: int, total_weight: Optional[float] = None) -> str:
        """
        Generate CTT (Transaction Totals) segment.

        Args:
            line_count: Total number of line items (CTT01)
            total_weight: Total shipment weight (CTT04)

        Returns:
            CTT segment string
        """
        segment = f"CTT{self.element_sep}{line_count}"

        if total_weight is not None:
            # CTT02-03: Skip
            # CTT04: Weight
            # CTT05: Unit of measure
            segment += f"{self.element_sep}{self.element_sep}{self.element_sep}{total_weight:.2f}{self.element_sep}LB"

        return segment
