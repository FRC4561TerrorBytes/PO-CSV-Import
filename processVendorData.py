import requests
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

#Get public Shopify product information using the product handle. For WCP, this is the SKU (E.g. "wcp-0063").
#Returns: dict containing all of the Shopify product information
def get_shopify_product(handle):

    store_url = store_url.rstrip("/")
    url = f"https://wcproducts.com/products/{handle}.js"

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=10
    )

    response.raise_for_status()
    
    return response.json()

def get_andymark_product(): #Andymark is also shopify, so this might have the same workflow as WCP
    return -1

def get_ctre_product():
    return -1

def get_rev_product():
    return -1

#Convert cents to a dollar string formatted as X.XX.
def cents_to_dollars(cents):
    try:
        dollars = Decimal(cents) / Decimal(100)
        return f"{dollars:,.2f}"
    except (InvalidOperation, ValueError):
        return f"{cents}" if cents else "0.00"

# Returns product fields needed by the Slack CSV workflow for Shopify store products
def filter_shopify_info(product, quantity, store_url):

    handle = product.get("handle", "")
    variants = product.get("variants") or []

    #Shopify prices are in cents
    price = cents_to_dollars(product.get("price"))

    if price is None and variants:
        price = cents_to_dollars(variants[0].get("price"))

    return {
        "Title": product.get("title"),
        "Num": quantity,
        "Link": f"{store_url.rstrip('/')}/products/{quote(handle, safe='')}" if handle else None,
        "Price": price,
    }
