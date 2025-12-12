## Quick Start Guide

# ASN 856 + SSCC Label Generator - Quick Start

Get started in 5 minutes! This guide shows you how to process your first order.

---

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PROJECT-3-ASN-856-GENERATOR-DEMO
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Your First Order

### Step 1: View Available Examples

```bash
python main.py examples
```

### Step 2: Validate Sample Order

```bash
python main.py validate examples/sample_orders/order_001.json
```

Expected output:
```
🔍 Validating Order
   File: examples/sample_orders/order_001.json

✅ Validation Passed

📋 Order Details:
   Order ID: ORD-2025-001
   PO Number: PO-ACME-12345
   ...
```

### Step 3: Process Complete Order

```bash
python main.py process --input examples/sample_orders/order_001.json
```

This will:
1. ✅ Load and validate the order
2. ✅ Cartonize items into shipping cartons
3. ✅ Generate SSCCs for each carton
4. ✅ Create EDI 856 ASN file
5. ✅ Render PDF shipping labels

### Step 4: Check Output

```bash
ls -la output/
```

You should see:
```
output/
├── 856_SHIP-ORD-2025-001.txt    # EDI 856 ASN
└── labels/
    └── label_carton_1_*.pdf      # Shipping label PDF
```

---

## Common Commands

### Process Order (Complete Pipeline)

```bash
python main.py process -i examples/sample_orders/order_001.json
```

### Generate ASN Only

```bash
python main.py generate-asn -i order.json -o output/856.txt
```

### Generate Labels Only

```bash
python main.py generate-labels -i order.json -o output/labels/
```

### Custom Carton Limits

```bash
python main.py process -i order.json --max-items 30 --max-weight 75.0
```

### Skip Label Generation

```bash
python main.py process -i order.json --skip-labels
```

### Custom EDI IDs

```bash
python main.py process -i order.json --sender-id ACME --receiver-id CUSTOMER
```

---

## View Generated Files

### View ASN (EDI 856)

```bash
cat output/856_SHIP-ORD-2025-001.txt
```

Or with line numbers:
```bash
cat -n output/856_SHIP-ORD-2025-001.txt | head -20
```

### View Label (PDF)

```bash
# Linux
xdg-open output/labels/label_carton_*.pdf

# Mac
open output/labels/label_carton_*.pdf

# Windows
start output\labels\label_carton_*.pdf
```

---

## Create Your Own Order

### 1. Copy Example Template

```bash
cp examples/sample_orders/order_001.json my_order.json
```

### 2. Edit Order Details

Open `my_order.json` and modify:

```json
{
  "order_id": "MY-ORDER-001",
  "purchase_order": "PO-MY-12345",
  "ship_date": "2025-12-20",
  "ship_from": {
    "name": "My Warehouse",
    "address_line1": "123 Warehouse St",
    "city": "YourCity",
    "state": "CA",
    "postal_code": "90210",
    "country": "US"
  },
  "ship_to": {
    "name": "Customer Name",
    "address_line1": "456 Customer Ave",
    "city": "CustomerCity",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "carrier_code": "UPSN",
  "service_level": "Ground",
  "items": [
    {
      "line_number": 1,
      "sku": "MY-SKU-001",
      "description": "My Product",
      "quantity": 50,
      "uom": "EA",
      "unit_weight": 1.5
    }
  ]
}
```

### 3. Validate Your Order

```bash
python main.py validate my_order.json
```

### 4. Process Your Order

```bash
python main.py process -i my_order.json -o my_output/
```

---

## Getting Help

### Command Help

```bash
python main.py --help
python main.py process --help
python main.py generate-asn --help
```

### Examples

```bash
python main.py examples
```

### Documentation

See `docs/` directory for detailed documentation:
- `PART_1_DATA_MODELS.md` — Data structure reference
- `PART_2_CARTONIZATION.md` — Cartonization logic
- Full API documentation

---

## Troubleshooting

### Issue: "python-barcode not installed"

**Solution:**
```bash
pip install python-barcode
```

### Issue: "reportlab not installed"

**Solution:**
```bash
pip install reportlab
```

### Issue: "pydantic validation error"

**Solution:**
Check your order JSON format. Use `validate` command to see detailed error:
```bash
python main.py validate your_order.json
```

### Issue: "No such file or directory"

**Solution:**
Make sure you're in the project root directory:
```bash
cd PROJECT-3-ASN-856-GENERATOR-DEMO
python main.py process -i examples/sample_orders/order_001.json
```

---

## Next Steps

### Learn More

- Read the full documentation in `docs/`
- Explore source code in `src/`
- Check out test examples in `tests/`

### Advanced Usage

- Configure custom cartonization rules
- Customize label layouts
- Integrate with external systems
- Automate with scripts

### Contributing

See `CONTRIBUTING.md` (if available) for contribution guidelines.

---

## Summary

You've successfully:
- ✅ Installed the ASN Generator
- ✅ Validated a sample order
- ✅ Processed a complete order
- ✅ Generated EDI 856 ASN
- ✅ Created shipping labels

**Need help?** Check the full documentation or open an issue on GitHub.

---

**Happy Shipping! 📦**
