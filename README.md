# FRCBOM CSV to PO Sheet Slack app

This Slack app provides allows users to upload CSVs generated from FRCBOM into the PO Spreadsheet. This keeps all purchases tracked in one place, while allowing us to use quick-ordering features and easily move data between systems

Below is a sample WCP spreadsheet from FRCBOM

```csv
SKU,QTY
wcp-0063,2
wcp-0100,1
```

## Supported Vendors
* West Coast Products (WCP)
* Andymark
* CTR Electronics

Unsupported as of now:
* REV

## Using the App
1. Download the vendor CSV from FRCBom
2. In the #purchasing channel, type / or use the 'Run Shortcuts' menu and launch **Import FRCBom CSV**
3. Upload the CSV and select a needed by date. 
4. Confirm that the app sent a message to the #purchasing channel and that the PO spreadsheet has been updated

## Deploy to Vercel

1. Create or update the Slack app from `manifest.yaml` and install it in the target workspace.
2. Confirm the `files:read`, `chat:write`, `channels:read`, `commands`, and `users:read` bot scopes.
3. Install dependencies with `python -m pip install -r requirements.txt`.
4. Deploy the repository with Vercel. Vercel automatically uses [api/index.py](api/index.py) as the Python function entrypoint.
5. In Slack, set the Interactivity Request URL to `https://YOUR-VERCEL-DOMAIN/api/index`.
6. Add `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID`, and `GOOGLE_WORKSHEET_NAME` as Vercel environment variables. The 
7. Share the Google Sheet with the service account email from `GOOGLE_SERVICE_ACCOUNT_JSON` as an Editor.

Because the app creates a new context with file upload, you need to deploy the application for a persistent lifetime. Running the app locally in your python development environment will not work.


## TODO:
* Support ordering CSVs from REV and other vendors?
* Multiple CSV import?
* Associate orders to parts. Link parts in the PO sheet back to FRCBom? The idea here is to get a better idea of what a part costs
* Send a daily/weekly/whatever digest email to purchasing approvers? Apps script triggered email or Slack DM would work

## Other Slack App Ideas:
* Move programming Slack List statuses around by linking to Github issues

## Adding Support for more vendors
1. Find the URL with all products listed. Many stores will use collections to manage these, you may need to merge multiple collections manually inside the application.
2. Add this URL to ProcessVendorData.py. Using CTRE as an example: `https://store.ctr-electronics.com/collections/all-products/products` . Also add the URL format for an individual product. For most stores this will be the general website URL, like `https://store.ctr-electronics.com/` . This is the data in the shopify store product URL before the `/product/` section of the URL.
3. In the `products_from_csv` function in `slack_app.py`, add a new case to match the SKU format: 

```
 elif handle.startswith("ctre"):
            if ctre_catalog is None:
                ctre_catalog = get_shopify_catalog(CTRE_URL, CTRE_ROOT)

            resolved_handle = get_handle_for_sku(ctre_catalog, handle)
            if resolved_handle is None:
                raise ValueError(f"SKU {handle} is not a valid part for CTR Electronics")

            product = get_shopify_product(resolved_handle, CTRE_ROOT)
            results.append(filter_shopify_info(product, quantity, CTRE_ROOT))
```
The above example calls `get_handle_for_sku` because the store uses handles that are different than the product SKU. For stores that use SKUs as handles, the line calling `get_handle_for_sku` can be omitted.