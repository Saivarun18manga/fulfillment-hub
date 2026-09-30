# Fulfillment Hub

A simple fulfillment control center for XYZ's warehouse operations.

## What this demo solves

The application focuses on the operational problems that are most likely to cause missed shipments or fulfillment errors:

- Priority orders staying visible and moving before their cutoff
- Inventory shortages blocking orders
- Stock transfers from the secondary warehouse to the main warehouse
- A guided picking → packing → staging → shipping workflow
- Exceptions that are visible and can be resolved instead of being handled informally

## Tech stack

- Python
- Flask
- SQLite
- HTML/CSS/JavaScript

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000/

## Main demo workflow

1. Open **Dashboard**.
2. Select priority order **#1044 – Priya Shah**.
3. The order is blocked because the main warehouse does not have enough SKU-101 stock.
4. Click **Request stock transfer**.
5. The application calculates the shortage and moves the required quantity from the secondary warehouse to the main warehouse.
6. The inventory exception is resolved and the order moves to **Picking**.
7. Open the Picking task, enter the scanned SKU, exact variant, and picked quantity for every item. The app rejects mismatches and only then moves the order to Packing; continue through staging and shipping.
8. Review the transfer history and exception state.

## Important note

The data is dummy operational data created specifically for the take-home project. No real store, marketplace, or courier integrations are used.
