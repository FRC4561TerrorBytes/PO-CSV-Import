import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import requests


REV_URL = "https://www.revrobotics.com"


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


def parse_rev_product_payload(payload, handle):
    product = (payload or {}).get("data", {}).get("site", {}).get("product")
    if not product:
        raise ValueError(f"REV SKU {handle} was not found on Revrobotics.com")

    variants = product.get("variants", {}).get("edges") or []
    variant = None
    normalized_handle = (handle or "").upper()
    for edge in variants:
        node = edge.get("node") or {}
        if (node.get("sku") or "").upper() == normalized_handle:
            variant = node
            break

    if variant is None and variants:
        variant = variants[0].get("node") or {}

    title = (product.get("name") or variant.get("name") or handle or "").strip()
    price_value = None
    if variant:
        price_value = (variant.get("prices") or {}).get("price", {}).get("value")
    if price_value is None:
        price_value = product.get("price")
    price = normalize_price_to_cents(price_value)

    normalized_variant = dict(variant or {})
    normalized_variant["price"] = price
    normalized_variant["handle"] = handle

    product_dict = {
        "handle": handle,
        "title": title,
        "price": price,
        "variants": [normalized_variant],
    }
    if product.get("sku"):
        product_dict["sku"] = product.get("sku")
    return product_dict


def get_rev_storefront_token(store_url):
    response = requests.get(store_url, timeout=20)
    response.raise_for_status()
    match = re.search(r'const\s+STOREFRONT_TOKEN\s*=\s*"([^"]+)"', response.text)
    if not match:
        raise ValueError("Could not find the Rev storefront token on the public storefront page.")
    return match.group(1)


def get_rev_product(handle):
    if not handle:
        raise ValueError("REV product handle is required.")

    handle = str(handle).strip()
    store_url = REV_URL.rstrip("/")
    token = get_rev_storefront_token(store_url)
    query = """
        query ProductBySku($sku: String!) {
          site {
            product(variantSku: $sku) {
              entityId
              name
              sku
              variants(first: 50) {
                edges {
                  node {
                    entityId
                    sku
                    name
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
        f"{store_url}/graphql",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={
            "query": query,
            "variables": {"sku": handle.upper()},
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return parse_rev_product_payload(payload, handle)


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
