# PART 2 — Cartonization Engine Documentation

## Overview

The Cartonization Engine is responsible for converting validated order inputs into shipment packages with:
- Items packed into cartons using configurable rules
- Unique SSCC-18 assigned to each carton
- Weight and dimension calculations
- Complete shipment hierarchy (Shipment → Order → Cartons → Items)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                 Cartonization Engine                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────┐         ┌──────────────────┐      │
│  │  SSCC          │         │  Cartonization   │      │
│  │  Generator     │────────▶│  Engine          │      │
│  │                │         │                  │      │
│  │  - GS1 check   │         │  - Packing logic │      │
│  │    digit calc  │         │  - Weight calc   │      │
│  │  - Sequential  │         │  - SSCC assign   │      │
│  │    numbering   │         │  - Shipment      │      │
│  └────────────────┘         │    building      │      │
│                             └──────────────────┘      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Cartonization Config                     │  │
│  │  - Max items per carton                          │  │
│  │  - Max weight per carton                         │  │
│  │  - Packing strategy                              │  │
│  │  - SSCC configuration                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
OrderInput (from PART 1)
    ↓
Convert OrderLineItems → Items
    ↓
Apply Packing Rules
    ↓
Create Cartons
    ↓
Generate & Assign SSCCs
    ↓
Calculate Weights
    ↓
Build Order & Shipment Structures
    ↓
ShipmentPackage (ready for PART 3: ASN Builder)
```

---

## SSCC Generator (`src/sscc/generator.py`)

### Purpose
Generates GS1-compliant SSCC-18 (Serial Shipping Container Code) numbers with proper check digit calculation.

### SSCC-18 Structure

```
Total: 18 digits

┌───┬──────────────┬────────────────┬─────────┐
│ 0 │   0614141    │   123456789    │    8    │
└───┴──────────────┴────────────────┴─────────┘
  ^        ^              ^              ^
  │        │              │              └─ Check Digit (mod-10)
  │        │              └─────────────── Serial Reference (9 digits, padded)
  │        └───────────────────────────── GS1 Company Prefix (7-10 digits)
  └────────────────────────────────────── Extension Digit (0-9)
```

### Check Digit Algorithm (GS1 Mod-10)

The check digit ensures SSCC integrity using the GS1 mod-10 algorithm:

1. Start from the right (excluding check digit position)
2. Multiply each digit alternately by **3** and **1**
3. Sum all products
4. Subtract sum from nearest equal or higher multiple of 10
5. Result is the check digit (0-9)

**Example Calculation:**

```
SSCC: 0 0614141 123456789 ?

Position:  16 15 14 13 12 11 10 9  8  7  6  5  4  3  2  1  0
Digit:     0  0  6  1  4  1  4  1  1  2  3  4  5  6  7  8  9
Weight:    3  1  3  1  3  1  3  1  3  1  3  1  3  1  3  1  3
Product:   0  0  18 1  12 1  12 1  3  2  9  4  15 6  21 8  27

Sum: 0 + 0 + 18 + 1 + 12 + 1 + 12 + 1 + 3 + 2 + 9 + 4 + 15 + 6 + 21 + 8 + 27 = 140

Check digit: 150 - 140 = 10 → 0 (if 10, use 0)

Final SSCC: 0 0614141 123456789 8
```

### Class: `SSCCGenerator`

#### Constructor

```python
from src.sscc.generator import SSCCGenerator, create_sscc_generator
from src.models.label_models import SSCCConfig

# Using config object
config = SSCCConfig(
    company_prefix="0614141",
    extension_digit="0",
    serial_start=1,
    serial_padding=9
)
generator = SSCCGenerator(config)

# Or using convenience function
generator = create_sscc_generator(
    company_prefix="0614141",
    extension_digit="0",
    serial_start=1,
    serial_padding=9
)
```

#### Methods

##### `generate_next() -> SSCC`
Generates the next SSCC in sequence with check digit.

```python
sscc = generator.generate_next()
print(sscc.get_full_sscc())  # 006141410000000018
```

##### `generate_batch(count: int) -> list[SSCC]`
Generates multiple SSCCs at once.

```python
batch = generator.generate_batch(10)
for sscc in batch:
    print(sscc.get_full_sscc())
```

##### `reset(start_serial: Optional[int] = None)`
Resets the serial counter.

```python
generator.reset()  # Reset to config start value
generator.reset(start_serial=1000)  # Reset to specific value
```

##### `peek_next_sscc() -> str`
Preview next SSCC without incrementing counter.

```python
next_sscc = generator.peek_next_sscc()
print(f"Next SSCC will be: {next_sscc}")
```

##### `validate_sscc(sscc: SSCC) -> bool` (static)
Validates an SSCC's check digit.

```python
is_valid = SSCCGenerator.validate_sscc(sscc)
```

---

## Cartonization Configuration (`src/cartonization/config.py`)

### Class: `CartonizationConfig`

Configures packing rules and behavior.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_items_per_carton` | int | 50 | Maximum units per carton |
| `max_weight_per_carton` | float | 50.0 | Maximum weight in lbs (None = no limit) |
| `default_carton_length` | float | 18.0 | Default carton length (inches) |
| `default_carton_width` | float | 12.0 | Default carton width (inches) |
| `default_carton_height` | float | 10.0 | Default carton height (inches) |
| `pack_by_sku` | bool | False | Keep same SKUs together |
| `single_item_cartons` | bool | False | Each SKU gets separate cartons |
| `carton_id_prefix` | str | "CTN" | Prefix for carton IDs |
| `carton_id_padding` | int | 4 | Zero-padding for carton numbers |
| `sscc_company_prefix` | str | "0614141" | GS1 company prefix for SSCC |
| `sscc_extension_digit` | str | "0" | SSCC extension digit |
| `sscc_serial_start` | int | 1 | Starting SSCC serial number |

#### Example Usage

```python
from src.cartonization.config import CartonizationConfig

config = CartonizationConfig(
    max_items_per_carton=30,
    max_weight_per_carton=75.0,
    single_item_cartons=True,  # Separate cartons per SKU
    sscc_company_prefix="0614141"
)
```

---

## Cartonization Engine (`src/cartonization/engine.py`)

### Class: `CartonizationEngine`

Main engine for packing orders into cartons.

#### Constructor

```python
from src.cartonization.engine import CartonizationEngine
from src.cartonization.config import CartonizationConfig

# Default configuration
engine = CartonizationEngine()

# Custom configuration
config = CartonizationConfig(max_items_per_carton=25)
engine = CartonizationEngine(config)
```

#### Main Method: `cartonize_order(order_input: OrderInput) -> ShipmentPackage`

Converts an order into a complete shipment package.

**Process:**
1. Validates input order
2. Converts `OrderLineItem` → `Item` objects
3. Packs items into cartons using configured rules
4. Assigns SSCC to each carton
5. Calculates weights and dimensions
6. Builds `Order` and `Shipment` structures
7. Returns `ShipmentPackage`

**Example:**

```python
from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine

# Load order
order = OrderInput.parse_file("examples/sample_orders/order_001.json")

# Cartonize
engine = CartonizationEngine()
shipment_package = engine.cartonize_order(order)

# Access results
shipment = shipment_package.shipment
print(f"Created {shipment.total_cartons} carton(s)")
print(f"Total weight: {shipment.total_weight} lbs")

for carton in shipment.cartons:
    print(f"Carton {carton.sequence_number}: SSCC {carton.sscc}")
```

---

## Packing Algorithms

### 1. Single-Item Cartons Mode (`single_item_cartons=True`)

Each SKU type gets its own carton(s).

**Use Case:** When SKUs should not be mixed (e.g., temperature-sensitive items, fragile items).

**Logic:**
- For each item type:
  - Calculate how many fit per carton (by quantity and weight limits)
  - Create as many cartons as needed
  - Assign sequential SSCCs

**Example:**
```python
config = CartonizationConfig(single_item_cartons=True)
```

### 2. Greedy Packing Mode (`single_item_cartons=False`, default)

Items are packed sequentially until limits are reached.

**Use Case:** General-purpose packing to minimize carton count.

**Logic:**
- Start with empty carton
- For each item type:
  - Add as many units as fit (respecting quantity and weight limits)
  - If carton is full, start new carton
  - Continue until all items packed

**Example:**
```python
config = CartonizationConfig(
    max_items_per_carton=50,
    max_weight_per_carton=75.0
)
```

### Constraints Applied

Both algorithms enforce:
1. **Quantity Limit:** No carton exceeds `max_items_per_carton`
2. **Weight Limit:** No carton exceeds `max_weight_per_carton` (if set)
3. **Minimum 1 Item:** Every carton has at least 1 item (even if it exceeds weight limit)

---

## Testing

### Test Coverage

**`tests/test_sscc.py`** — 30+ test cases:
- ✅ Check digit calculation (multiple examples)
- ✅ SSCC generation (single and batch)
- ✅ Sequential numbering
- ✅ Validation logic
- ✅ Formatting methods
- ✅ Edge cases (overflow, different prefix lengths)

**`tests/test_cartonization.py`** — 25+ test cases:
- ✅ Simple order (single carton)
- ✅ Multi-carton by quantity
- ✅ Multi-carton by weight
- ✅ Multiple item types
- ✅ Packing modes (single-item vs. greedy)
- ✅ SSCC assignment uniqueness
- ✅ Shipment structure validation
- ✅ Weight calculations
- ✅ Real sample order files
- ✅ Edge cases (empty orders, large quantities)

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run SSCC tests only
pytest tests/test_sscc.py -v

# Run cartonization tests only
pytest tests/test_cartonization.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Demo Scripts

### `examples/demo_cartonization.py`

Interactive demo showing:
1. Simple order cartonization
2. Multi-carton order
3. SSCC generation and validation
4. Different packing strategies

**Run:**
```bash
python examples/demo_cartonization.py
```

**Output:**
```
================================================================================
  CARTONIZATION ENGINE DEMO
  Project 3: ASN 856 + SSCC Label Generator
================================================================================

================================================================================
  Demo 1: Simple Order (Single Carton)
================================================================================

Loading order from: examples/sample_orders/order_001.json
Order ID: ORD-2025-001
Purchase Order: PO-ACME-12345
Ship Date: 2025-12-15
Items: 3 line items

Cartonizing order...

✅ Cartonization complete!
Shipment ID: SHIP-ORD-2025-001
Total Cartons: 1
Total Weight: 111.00 lbs

Carton Details:

  Carton 1 (CTN-0001):
    SSCC: 006141410000000018
    Items: 100 units
    Weight: 111.00 lbs
    Contents:
      - WIDGET-A-100: 50 EA (Premium Widget Type A - Blue)
      - GADGET-B-200: 30 EA (Standard Gadget Type B - Red)
      - DEVICE-C-300: 20 EA (Advanced Device Type C - Green)
```

---

## Usage Examples

### Example 1: Basic Cartonization

```python
from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine

# Load order
order = OrderInput.parse_file("examples/sample_orders/order_001.json")

# Create engine with defaults
engine = CartonizationEngine()

# Process order
result = engine.cartonize_order(order)

# Access shipment
shipment = result.shipment
print(f"Shipment ID: {shipment.shipment_id}")
print(f"Cartons: {shipment.total_cartons}")
print(f"Weight: {shipment.total_weight} lbs")
```

### Example 2: Custom Configuration

```python
from src.cartonization.engine import CartonizationEngine
from src.cartonization.config import CartonizationConfig

# Configure smaller cartons
config = CartonizationConfig(
    max_items_per_carton=20,
    max_weight_per_carton=30.0,
    single_item_cartons=True
)

engine = CartonizationEngine(config)
result = engine.cartonize_order(order)
```

### Example 3: Accessing Carton Details

```python
result = engine.cartonize_order(order)

for carton in result.shipment.cartons:
    print(f"\nCarton {carton.sequence_number}:")
    print(f"  ID: {carton.carton_id}")
    print(f"  SSCC: {carton.sscc}")
    print(f"  Dimensions: {carton.length}x{carton.width}x{carton.height} inches")
    print(f"  Weight: {carton.calculate_weight()} lbs")
    print(f"  Items:")
    for item in carton.items:
        print(f"    - {item.sku}: {item.quantity} {item.uom}")
```

### Example 4: SSCC Validation

```python
from src.sscc.generator import SSCCGenerator

for carton in shipment.cartons:
    # Parse SSCC back into object
    from src.models.label_models import SSCC
    sscc = SSCC(
        extension_digit=carton.sscc[0],
        company_prefix=carton.sscc[1:8],
        serial_reference=carton.sscc[8:17],
        check_digit=carton.sscc[17]
    )

    # Validate
    is_valid = SSCCGenerator.validate_sscc(sscc)
    print(f"SSCC {carton.sscc}: {'✅ Valid' if is_valid else '❌ Invalid'}")
```

---

## Configuration Best Practices

### 1. Setting Carton Limits

```python
# For standard corrugated boxes
config = CartonizationConfig(
    max_items_per_carton=50,
    max_weight_per_carton=50.0,  # OSHA single-person lift limit
    default_carton_length=18.0,
    default_carton_width=12.0,
    default_carton_height=10.0
)
```

### 2. Separating Incompatible Items

```python
# Use single_item_cartons for items that shouldn't mix
config = CartonizationConfig(
    single_item_cartons=True,  # Each SKU separate
    max_items_per_carton=100
)
```

### 3. High-Volume Picking

```python
# Optimize for pick efficiency
config = CartonizationConfig(
    max_items_per_carton=100,  # Larger cartons
    max_weight_per_carton=None,  # No weight limit
    pack_by_sku=True  # Keep SKUs together
)
```

---

## Output Structure

### `ShipmentPackage` Hierarchy

```
ShipmentPackage
├── shipment: Shipment
│   ├── shipment_id: str
│   ├── ship_date: datetime
│   ├── ship_from_name: str
│   ├── ship_from_address: str
│   ├── ship_to_name: str
│   ├── ship_to_address: str
│   ├── carrier_code: str
│   ├── service_level: str
│   ├── total_cartons: int
│   ├── total_weight: float
│   ├── orders: List[Order]
│   │   └── order: Order
│   │       ├── order_id: str
│   │       ├── purchase_order: str
│   │       └── carton_ids: List[str]
│   └── cartons: List[Carton]
│       └── carton: Carton
│           ├── carton_id: str
│           ├── sscc: str (18 digits)
│           ├── sequence_number: int
│           ├── weight: float
│           ├── length/width/height: float
│           └── items: List[Item]
│               └── item: Item
│                   ├── sku: str
│                   ├── description: str
│                   ├── quantity: int
│                   ├── uom: str
│                   └── unit_weight: float
├── generated_at: datetime
├── sender_id: str (optional)
└── receiver_id: str (optional)
```

---

## Integration Points

### Inputs (from PART 1)
- `OrderInput` — Validated order from JSON/CSV
- `OrderLineItem` — Individual line items
- `Address` — Ship-from/ship-to addresses

### Outputs (to PART 3)
- `ShipmentPackage` — Complete shipment ready for ASN generation
- `Shipment` — Top-level shipment with metadata
- `Carton` — Packed cartons with SSCCs assigned
- `Item` — Individual SKUs with quantities

---

## Troubleshooting

### Issue: "Serial number exceeds maximum padding"

**Cause:** SSCC serial number has exceeded the configured padding length.

**Solution:**
```python
config = CartonizationConfig(
    sscc_serial_start=1,  # Lower starting point
    # Or increase padding in SSCCConfig if needed
)
```

### Issue: "Order must have at least one item"

**Cause:** Empty order items list.

**Solution:** Validate order before cartonization:
```python
if not order.items:
    raise ValueError("Order must contain items")
```

### Issue: Cartons are too heavy

**Cause:** Items are too heavy relative to `max_weight_per_carton`.

**Solution:** Adjust weight limit:
```python
config = CartonizationConfig(
    max_weight_per_carton=100.0,  # Increase limit
    # Or set to None to disable weight checking
)
```

---

## Next Steps

With PART 2 complete, proceed to:

**PART 3 — ASN Builder**
- Build EDI 856 hierarchical structure
- Generate proper HL loops
- Create compliant X12 segments
- Output formatted EDI file

---

## File Structure

```
src/
├── sscc/
│   ├── __init__.py
│   └── generator.py          # SSCC generation logic
├── cartonization/
│   ├── __init__.py
│   ├── config.py             # Configuration
│   └── engine.py             # Main cartonization logic

tests/
├── test_sscc.py              # SSCC generator tests (30+ cases)
└── test_cartonization.py     # Cartonization tests (25+ cases)

examples/
└── demo_cartonization.py     # Interactive demo script

docs/
└── PART_2_CARTONIZATION.md   # This file
```

---

**Author:** Integration Engineering Team
**Last Updated:** December 2025
**Status:** ✅ PART 2 Complete
