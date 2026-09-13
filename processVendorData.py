import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import requests


REV_URL = "https://www.revrobotics.com"
AM_URL = "https://andymark.com/collections/view-all/products"
AM_ROOT = "https://andymark.com"
CTRE_URL = "https://store.ctr-electronics.com/collections/all-products/products"
CTRE_ROOT = "https://store.ctr-electronics.com/"

def get_shopify_catalog(url, rootUrl):
    handle_catalog = {}

    page = 1
    page_size = 250

    while True:
        params = {"limit": page_size, "page": page}
        response = requests.get(url +".json", params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()

        products = payload.get("products") or []
        if not products:
            break

        for product in products:
            product_handle = (product.get("handle") or "").strip()
            if not product_handle:
                continue

            variants = []
            for variant in product.get("variants") or []:
                variants.append({
                    "id": variant.get("id"),
                    "sku": (variant.get("sku") or "").strip(),
                    "title": (variant.get("title") or "").strip(),
                    "price": variant.get("price"),
                    "available": variant.get("available"),
                })

            handle_catalog[product_handle] = {
                "handle": product_handle,
                "title": (product.get("title") or "").strip(),
                "product_id": product.get("id"),
                "vendor": product.get("vendor"),
                "available": product.get("available"),
                "product_url": f"{rootUrl}/products/{product_handle}",
                "variants": variants,
                "sku": variants[0].get("sku") if variants else None,
                "price": variants[0].get("price") if variants else None,
            }

        if len(products) < page_size:
            break

        page += 1

    return handle_catalog


#Get public Shopify product information using the product handle. For WCP, this is the SKU (E.g. "wcp-0063").
#Returns: dict containing all of the Shopify product information
def get_shopify_product(handle, url):
    base_url = url.rstrip("/")
    product_url = f"{base_url}/products/{handle}.js"

    response = requests.get(
        product_url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get_handle_for_sku(catalog, sku):
    if not catalog or not sku:
        return None

    normalized_sku = sku.strip().upper()

    for handle, product in catalog.items():
        variants = product.get("variants") or []
        for variant in variants:
            if (variant.get("sku") or "").strip().upper() == normalized_sku:
                return handle

    return None


def get_andymark_product(handle): #Andymark is also shopify, so this might have the same workflow as WCP
    return -1


def get_ctre_product(handle):
    return -1


def normalize_price_to_cents(price):
    if price is None:
        return 0

    try:
        if isinstance(price, (int, float, Decimal)):
            return int((Decimal(str(price)) * Decimal(100)).quantize(Decimal("1")))

        text = str(price).strip()
        if not text:
            return 0

        cleaned = text.replace("$", "").replace(",", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned in ("", ".", "-", "-."):
            return 0

        cents = (Decimal(cleaned) * Decimal(100)).quantize(Decimal("1"))
        return int(cents)
    except (InvalidOperation, ValueError, TypeError):
        return 0

#Convert cents to a dollar string formatted as X.XX.
def cents_to_dollars(cents):
    try:
        if cents is None:
            return "0.00"
        dollars = Decimal(cents) / Decimal(100)
        return f"{dollars:,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return f"{cents}" if cents else "0.00"


# Returns product fields needed by the Slack CSV workflow for Shopify store products
def filter_shopify_info(product, quantity, store_url):
    handle = product.get("handle", "")
    variants = product.get("variants") or []

    price_value = product.get("price")
    if price_value is None and variants:
        first_variant = variants[0] if isinstance(variants, list) else {}
        price_value = (first_variant or {}).get("price")

    #Shopify prices are in cents
    price = cents_to_dollars(price_value) if price_value is not None else "0.00"

    return {
        "Title": product.get("title"),
        "Num": quantity,
        "Link": f"{store_url.rstrip('/')}/products/{quote(handle, safe='')}" if handle else None,
        "Price": price,
    }
