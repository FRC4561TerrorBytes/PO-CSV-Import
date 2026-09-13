import unittest

from processVendorData import normalize_price_to_cents, parse_rev_product_payload


class RevParsingTests(unittest.TestCase):
    def test_parse_rev_product_payload_extracts_title_and_price(self):
        payload = {
            "data": {
                "site": {
                    "product": {
                        "name": "REV-21-2812 Test Product",
                        "sku": "REV-21-2812",
                        "variants": {
                            "edges": [
                                {
                                    "node": {
                                        "sku": "REV-21-2812",
                                        "name": "REV-21-2812 Test Product",
                                        "prices": {"price": {"value": "12.99"}},
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }

        product = parse_rev_product_payload(payload, "rev-21-2812")

        self.assertEqual(product["handle"], "rev-21-2812")
        self.assertEqual(product["title"], "REV-21-2812 Test Product")
        self.assertEqual(product["price"], 1299)
        self.assertEqual(product["variants"][0]["price"], 1299)

    def test_normalize_price_to_cents_handles_string_values(self):
        self.assertEqual(normalize_price_to_cents("12.99"), 1299)
        self.assertEqual(normalize_price_to_cents("$12.99"), 1299)
        self.assertEqual(normalize_price_to_cents(12.99), 1299)


if __name__ == "__main__":
    unittest.main()
