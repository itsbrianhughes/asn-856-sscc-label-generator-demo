# PART 1 — Data Models Documentation

## Overview

This document describes the complete data model architecture for the ASN 856 + SSCC Label Generator system. The models are organized into four logical layers:

1. **Input Models** — External data contracts (JSON/CSV)
2. **Internal Models** — Business processing objects
3. **ASN Models** — EDI 856 hierarchical structures
4. **Label Models** — SSCC and shipping label data

---

## 1. Input Models (`src/models/input_models.py`)

### Purpose
Defines the schema for incoming order data. These models validate and normalize external input.

### Key Classes

#### `Address`
Represents shipping addresses (origin and destination).

**Fields:**
- `name` (str) — Company or location name
- `address_line1` (str) — Street address
- `address_line2` (Optional[str]) — Additional address info
- `city` (str) — City name
- `state` (str) — 2-letter state code
- `postal_code` (str) — ZIP/postal code
- `country` (str) — ISO country code (default: "US")

**Validations:**
- State must be exactly 2 characters (uppercase)

---

#### `OrderLineItem`
Represents a single SKU line item in an order.

**Fields:**
- `line_number` (int) — Sequence number (≥1)
- `sku` (str) — Stock keeping unit identifier
- `description` (str) — Human-readable item name
- `quantity` (int) — Quantity ordered (≥1)
- `uom` (str) — Unit of measure (default: "EA")
- `unit_weight` (Optional[float]) — Weight per unit in lbs

**Validations:**
- SKU cannot be empty or whitespace
- Quantity must be positive

---

#### `OrderInput`
Top-level order structure submitted by clients.

**Fields:**
- `order_id` (str) — Unique order identifier
- `purchase_order` (str) — Customer PO number
- `ship_date` (date) — Scheduled ship date
- `ship_from` (Address) — Origin address
- `ship_to` (Address) — Destination address
- `carrier_code` (Optional[str]) — SCAC carrier code (e.g., "UPSN")
- `service_level` (Optional[str]) — Service level (e.g., "Ground")
- `items` (List[OrderLineItem]) — Line items (≥1)
- `customer_account` (Optional[str]) — Customer account number
- `notes` (Optional[str]) — Special instructions

**Validations:**
- Must have at least one item
- Line numbers must be unique

**Example:**
```json
{
  "order_id": "ORD-2025-001",
  "purchase_order": "PO-12345",
  "ship_date": "2025-12-15",
  "ship_from": { ... },
  "ship_to": { ... },
  "items": [ ... ]
}
```

---

## 2. Internal Models (`src/models/internal_models.py`)

### Purpose
Core business objects used during processing. These represent the normalized domain model.

### Key Classes

#### `PackagingLevel` (Enum)
Defines GS1/EDI packaging hierarchy levels.

**Values:**
- `SHIPMENT` ("S") — Top-level shipment
- `ORDER` ("O") — Customer order
- `TARE` ("T") — Carton/container
- `PACK` ("P") — Inner pack
- `ITEM` ("I") — Individual SKU

---

#### `Item`
Represents a single SKU with quantity (used in cartons).

**Fields:**
- `sku` (str) — Stock keeping unit
- `description` (str) — Item description
- `quantity` (int) — Quantity (≥1)
- `uom` (str) — Unit of measure (default: "EA")
- `unit_weight` (Optional[float]) — Weight per unit in lbs
- `upc` (Optional[str]) — UPC/GTIN barcode
- `vendor_part_number` (Optional[str]) — Vendor SKU

**Methods:**
- `get_total_weight()` — Calculates total weight (quantity × unit_weight)

---

#### `Carton`
Represents a packed carton/case in the shipment.

**Fields:**
- `carton_id` (str) — Internal carton identifier
- `sscc` (Optional[str]) — GS1 SSCC-18 serial number
- `sequence_number` (int) — Carton number in shipment (≥1)
- `items` (List[Item]) — Items in this carton (≥1)
- `weight` (Optional[float]) — Total carton weight in lbs
- `length/width/height` (Optional[float]) — Dimensions in inches
- `packaging_code` (str) — Type code (default: "CTN")

**Methods:**
- `calculate_weight()` — Sum item weights
- `get_total_units()` — Count total units across all items

---

#### `Order`
Represents a customer order within a shipment.

**Fields:**
- `order_id` (str) — Unique order identifier
- `purchase_order` (str) — Customer PO number
- `carton_ids` (List[str]) — Associated carton IDs
- `customer_account` (Optional[str]) — Customer account
- `order_date` (Optional[datetime]) — Order date

---

#### `Shipment`
Top-level shipment structure containing orders and cartons.

**Fields:**
- `shipment_id` (str) — Unique shipment identifier
- `ship_date` (datetime) — Ship date/time
- `ship_from_name/address` (str) — Origin info
- `ship_to_name/address` (str) — Destination info
- `carrier_code` (Optional[str]) — SCAC code
- `service_level` (Optional[str]) — Service description
- `tracking_number` (Optional[str]) — Master tracking number
- `orders` (List[Order]) — Orders in shipment (≥1)
- `cartons` (List[Carton]) — All cartons (≥1)
- `total_weight` (Optional[float]) — Total shipment weight
- `total_cartons` (int) — Carton count

**Methods:**
- `calculate_totals()` — Updates totals from cartons

---

#### `ShipmentPackage`
Complete normalized shipment ready for ASN generation.

**Fields:**
- `shipment` (Shipment) — The shipment data
- `generated_at` (datetime) — Generation timestamp
- `sender_id` (Optional[str]) — EDI sender ID
- `receiver_id` (Optional[str]) — EDI receiver ID

---

## 3. ASN Models (`src/models/asn_models.py`)

### Purpose
EDI 856-specific structures for building compliant ASN documents.

### Key Classes

#### `HLLevelCode` (Enum)
Hierarchical level codes for HL segments.

**Values:**
- `SHIPMENT` ("S")
- `ORDER` ("O")
- `TARE` ("T")
- `PACK` ("P")
- `ITEM` ("I")

---

#### `SegmentType` (Enum)
Common EDI segment identifiers.

**Values:** ISA, GS, ST, BSN, HL, TD1, TD5, REF, DTM, N1, N3, N4, LIN, SN1, CTT, SE, GE, IEA

---

#### `HierarchicalLevel`
Represents an HL segment in the EDI hierarchy.

**Fields:**
- `hl_id` (str) — Unique hierarchical ID
- `parent_hl_id` (Optional[str]) — Parent HL ID
- `level_code` (HLLevelCode) — Level type
- `child_code` (Optional[str]) — "1" if has children, "0" if leaf
- `data` (Dict) — Level-specific data
- `children` (List[HierarchicalLevel]) — Child levels

---

#### `ASNHeader`
Header information for the ASN (BSN segment + envelope).

**Fields:**
- `transaction_set_purpose` (str) — "00" = Original, "01" = Cancellation
- `shipment_id` (str) — Shipment identifier
- `shipment_date` (datetime) — Ship date
- `ship_time` (Optional[str]) — Ship time (HHMM)
- `sender_id` (str) — EDI sender ID (ISA06/GS02)
- `receiver_id` (str) — EDI receiver ID (ISA08/GS03)
- `control_number` (str) — Transaction control number
- `isa_qualifier_sender/receiver` (str) — ID qualifiers

---

#### `ASNSummary`
Transaction totals (CTT segment).

**Fields:**
- `total_line_items` (int) — Total line count
- `total_quantity` (Optional[int]) — Total units shipped
- `total_weight` (Optional[float]) — Total weight
- `total_cartons` (Optional[int]) — Carton count

---

#### `ASNDocument`
Complete EDI 856 document structure.

**Fields:**
- `header` (ASNHeader) — Header info
- `hierarchy` (HierarchicalLevel) — Root HL (shipment)
- `summary` (ASNSummary) — Transaction totals
- `generated_at` (datetime) — Generation timestamp
- `segment_terminator` (str) — Default: "~"
- `element_separator` (str) — Default: "*"
- `subelement_separator` (str) — Default: ":"

**Methods:**
- `get_control_numbers()` — Generates ISA/GS/ST control numbers

---

#### Supporting Classes

**`ReferenceIdentification`** — REF segments for PO, BOL, tracking numbers, SSCC

**`PartyIdentification`** — N1/N3/N4 segments for ship-from/ship-to parties

**`CarrierDetail`** — TD5 segment for carrier and routing info

**`PackagingDetail`** — TD1 segment for package dimensions and weight

**`ItemIdentification`** — LIN segment for item identifiers

**`ItemDetail`** — SN1 segment for item quantities

---

## 4. Label Models (`src/models/label_models.py`)

### Purpose
GS1 SSCC generation and shipping label rendering.

### Key Classes

#### `SSCCFormat` (Enum)
SSCC format options.

**Values:**
- `SSCC_18` — Full 18-digit format (standard)
- `SSCC_17` — 17-digit without check digit

---

#### `BarcodeType` (Enum)
Supported barcode formats.

**Values:**
- `GS1_128` — GS1-128 (Code 128)
- `CODE_128` — Standard Code 128
- `QR_CODE` — QR Code (2D)

---

#### `LabelSize` (Enum)
Standard label sizes.

**Values:**
- `LABEL_4X6` — 4" × 6" (standard)
- `LABEL_4X8` — 4" × 8"
- `LABEL_6X8` — 6" × 8"
- `LETTER` — 8.5" × 11"

---

#### `SSCC`
Represents a GS1 SSCC-18 (Serial Shipping Container Code).

**Structure:**
```
(Extension) + (Company Prefix) + (Serial Reference) + (Check Digit)
    1 digit      7-10 digits         variable            1 digit
Total: 18 digits

Example: 0 0614141 123456789 8
```

**Fields:**
- `extension_digit` (str) — Extension (0-9)
- `company_prefix` (str) — GS1 company prefix (7-10 digits)
- `serial_reference` (str) — Serial number
- `check_digit` (str) — Calculated mod-10 check digit

**Methods:**
- `get_full_sscc()` — Returns 18-digit SSCC
- `get_sscc_without_check()` — Returns 17-digit SSCC
- `get_formatted_sscc()` — Returns human-readable format with separators
- `get_gs1_application_identifier()` — Returns SSCC with AI (00) prefix

**Validations:**
- Extension and check digit must be single digits
- Company prefix must be 7-10 numeric digits
- Serial reference must be numeric

---

#### `SSCCConfig`
Configuration for SSCC generation.

**Fields:**
- `company_prefix` (str) — GS1 company prefix (7-10 digits)
- `extension_digit` (str) — Default extension (default: "0")
- `serial_start` (int) — Starting serial number (default: 1)
- `serial_padding` (int) — Zero-padding length (default: 9)

---

#### `ShippingLabel`
Complete shipping label data.

**Fields:**
- `sscc` (SSCC) — Carton SSCC
- `carton_sequence` (int) — Carton X of Y
- `total_cartons` (int) — Total cartons
- `shipment_id` (str) — Shipment identifier
- `order_id/purchase_order` (Optional[str]) — Order references
- `ship_from_*` — Origin location info
- `ship_to_*` — Destination address info
- `carrier_name/service_level` — Carrier details
- `tracking_number` (Optional[str]) — Tracking number
- `weight` (Optional[float]) — Carton weight
- `item_count` (Optional[int]) — Item count
- `contents_summary` (Optional[List[str]]) — Human-readable contents
- `ship_date` (Optional[date]) — Ship date

---

#### `LabelConfig`
Configuration for label rendering.

**Fields:**
- `label_size` (LabelSize) — Physical size (default: 4×6)
- `output_format` (str) — PDF, PNG, or ZPL (default: "PDF")
- `barcode_type` (BarcodeType) — Barcode format (default: GS1-128)
- `barcode_height` (int) — Height in mm (default: 50)
- `include_human_readable` (bool) — Show text below barcode (default: True)
- `font_size_*` (int) — Font sizes for title/body/small text
- `margin` (float) — Margin in inches (default: 0.25)
- `include_logo/logo_path` — Logo settings
- `show_contents` (bool) — Display contents list (default: True)
- `max_contents_lines` (int) — Max lines for contents (default: 5)

---

#### `LabelRenderOutput`
Output from label rendering.

**Fields:**
- `sscc` (str) — SSCC for this label
- `carton_id` (str) — Internal carton ID
- `file_path` (str) — Path to generated file
- `file_format` (str) — File format
- `file_size_bytes` (Optional[int]) — File size
- `generated_at` (str) — Timestamp (ISO format)

---

#### `LabelBatch`
Batch of labels for complete shipment.

**Fields:**
- `shipment_id` (str) — Shipment identifier
- `labels` (List[LabelRenderOutput]) — All labels
- `total_labels` (int) — Label count
- `batch_generated_at` (str) — Batch timestamp
- `manifest_path` (Optional[str]) — JSON manifest path
- `archive_path` (Optional[str]) — ZIP archive path

---

## Model Relationships

```
OrderInput
  ↓ (validate & normalize)
ShipmentPackage
  ├─ Shipment
  │   ├─ Order (1+)
  │   └─ Carton (1+)
  │       ├─ SSCC
  │       └─ Item (1+)
  ↓ (transform)
ASNDocument
  ├─ ASNHeader
  ├─ HierarchicalLevel (recursive tree)
  │   ├─ Shipment (root)
  │   └─ Order
  │       └─ Tare (Carton)
  │           └─ Item
  └─ ASNSummary

ShipmentPackage → Carton
  ↓ (for each carton)
ShippingLabel → LabelRenderOutput
```

---

## Usage Example

```python
from src.models.input_models import OrderInput
from src.models.internal_models import Shipment
from src.models.asn_models import ASNDocument
from src.models.label_models import ShippingLabel

# 1. Parse input
order_input = OrderInput.parse_file("examples/sample_orders/order_001.json")

# 2. Convert to internal model (handled by cartonization engine)
shipment = convert_to_shipment(order_input)

# 3. Build ASN (handled by ASN builder)
asn_doc = build_asn(shipment)

# 4. Generate labels (handled by label generator)
for carton in shipment.cartons:
    label = create_shipping_label(carton, shipment)
    render_label(label)
```

---

## Validation Rules Summary

### Input Models
- ✅ State codes must be 2 characters
- ✅ SKUs cannot be empty
- ✅ Quantities must be positive (≥1)
- ✅ Line numbers must be unique
- ✅ Must have at least one item

### Internal Models
- ✅ Carton sequence cannot exceed total cartons
- ✅ Items list cannot be empty
- ✅ Weights must be non-negative

### SSCC Models
- ✅ Extension digit must be 0-9
- ✅ Company prefix must be 7-10 numeric digits
- ✅ Check digit must be single digit
- ✅ Serial reference must be numeric

### Label Models
- ✅ Carton sequence ≤ total cartons
- ✅ SSCC must follow GS1 format

---

## Next Steps

With data models complete, we can proceed to:

**PART 2** — Cartonization Engine (packing logic + SSCC assignment)
**PART 3** — 856 ASN Builder (hierarchical segment generation)
**PART 4** — SSCC Generator (check digit calculation)
**PART 5** — Label Renderer (PDF/PNG generation with barcodes)

---

## File Structure

```
src/models/
├── __init__.py
├── input_models.py      # External API contracts
├── internal_models.py   # Business domain objects
├── asn_models.py        # EDI 856 structures
└── label_models.py      # SSCC and shipping labels

examples/sample_orders/
├── order_001.json                # Simple order example
└── order_002_multi_carton.json   # Multi-carton example

docs/
└── PART_1_DATA_MODELS.md   # This file
```

---

**Author:** Integration Engineering Team
**Last Updated:** December 2025
**Status:** ✅ PART 1 Complete
