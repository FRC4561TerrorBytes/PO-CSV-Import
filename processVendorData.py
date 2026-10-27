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


def get_shopify_handle_for_sku(catalog, sku):
    if not catalog or not sku:
        return None

    normalized_sku = sku.strip().upper()

    for handle, product in catalog.items():
        variants = product.get("variants") or []
        for variant in variants:
            if (variant.get("sku") or "").strip().upper() == normalized_sku:
                return handle

    return None

# Get a graphql token, somehow this doesn't need an API token before??
def get_rev_storefront_token():
    response = requests.get(
        REV_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()

    token_match = re.search(r'graphQLToken\\":\\"([^\\"]+)', response.text)
    if not token_match:
        raise ValueError("Could not find the REV Robotics storefront API token.")
    return token_match.group(1)

# Get and Parse the response from the GraphQL query
def get_rev_product(sku, storefront_token):
    query = """
        query ProductBySku($sku: String!) {
            site {
                product(sku: $sku) {
                    name
                    sku
                    path
                    variants(first: 50) {
                        edges {
                            node {
                                sku
                                prices {
                                    price {
                                        value
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    response = requests.post(
        f"{REV_URL}/graphql",
        headers={
            "Authorization": f"Bearer {storefront_token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": {"sku": sku.strip().upper()}},
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in payload["errors"]
        )
        raise ValueError(f"REV Robotics product lookup failed: {messages}")

    return parse_rev_product_payload(payload, sku)

# Append variants, normalize prices to cents, fail on a malformed product
def parse_rev_product_payload(payload, sku):
    product = (
        payload.get("data", {})
        .get("site", {})
        .get("product")
    )
    if not product:
        return None

    variants = []
    for edge in (product.get("variants") or {}).get("edges") or []:
        variant = edge.get("node") or {}
        variant_price = (
            (variant.get("prices") or {})
            .get("price", {})
            .get("value")
        )
        variants.append({
            "sku": (variant.get("sku") or "").strip(),
            "title": (variant.get("name") or product.get("name") or "").strip(),
            "price": normalize_price_to_cents(variant_price),
        })

    normalized_sku = sku.strip().upper()
    selected_variant = next(
        (variant for variant in variants if variant["sku"].upper() == normalized_sku),
        variants[0] if variants else None,
    )
    product_price = product.get("price")
    price = (
        selected_variant["price"]
        if selected_variant
        else normalize_price_to_cents(product_price)
    )
    path = (product.get("path") or "").strip()
    handle = path.strip("/") or normalized_sku.lower()
    print(variants)
    return {
        "handle": handle,
        "path": path,
        "title": (product.get("name") or normalized_sku).strip(),
        "sku": (product.get("sku") or normalized_sku).strip(),
        "price": price,
        "variants": variants,
    }


def get_andymark_product(handle): #Andymark is also shopify, so this might have the same workflow as WCP
    return -1


def get_ctre_product(handle):
    return -1

# convert a cent or dollar price to cents as an int
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


def filter_rev_info(product, quantity):
    path = product.get("path") or f"/{quote(product.get('handle', ''), safe='')}/"
    return {
        "Title": product.get("title"),
        "Num": quantity,
        "Link": f"{REV_URL.rstrip('/')}/{path.lstrip('/')}",
        "Price": cents_to_dollars(product.get("price")),
    }