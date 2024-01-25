import json
import os
import unittest
from datetime import datetime

from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.5"

PRIVATE_RESOURCES_DIR = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)),
                 "private-resources"))


@unittest.skipIf(os.environ.get("INTEGRATION_TEST_JSON", "False") != "True",
                 "Skipping, INTEGRATION_TEST_JSON=True was not set in the environment")
class TestIntegrationJSON(TestCase):
    """
    The two JSON files committed to "private-resources" can be used as examples for the required syntax.
    Beyond that, any other files added to "private-resources" will be ignore by `.gitignore`.

    TODO: Document here what the JSON needs to look like for it to be loaded properly in to this test class.
    """
    amazon_session = None

    def __init__(self, method_name, filename=None, data=None):
        super(TestIntegrationJSON, self).__init__(method_name)

        self.filename = filename
        self.data = data

    @classmethod
    def setUpClass(cls):
        cls.credentials_found = os.environ.get(
            "AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")

        cls.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                           os.environ.get("AMAZON_PASSWORD"))
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)

    def setUp(self):
        if not self.credentials_found:
            self.fail(
                "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        self.assertTrue(self.amazon_session.is_authenticated)

    def run_json_test(self):
        print("Info: Dynamic test is running from JSON file {}".format(self.filename))

        # GIVEN
        func = self.data.pop("func")

        if func == "get_order_history":
            order_len = self.data.pop("orders_len")
            orders_json = self.data.pop("orders")
            full_details = self.data.get("full_details")

            # WHEN
            orders = self.amazon_orders.get_order_history(**self.data)

            # THEN
            self.assertEqual(order_len, len(orders))
            for index, order_json in orders_json.items():
                order = orders[int(index)]
                self.assertEqual(order.full_details, full_details)
                self.assert_json_items(order, order_json)
        elif func == "get_order":
            order_json = self.data
            order_id = order_json["order_number"]

            # WHEN
            order = self.amazon_orders.get_order(order_id)

            # THEN
            self.assertEqual(order.full_details, True)
            self.assert_json_items(order, order_json)
        else:
            self.fail(
                "Unknown function AmazonOrders.{}, check JSON in test file {}".format(
                    func, self.filename))

    def assert_json_items(self, entity, json_dict):
        for json_key, json_value in json_dict.items():
            entity_attr = getattr(entity, json_key)
            if json_value == "isNone":
                self.assertIsNone(entity_attr)
            elif json_value == "isNotNone":
                self.assertIsNotNone(entity_attr)
            elif isinstance(json_value, list):
                i = 0
                for element in json_value:
                    self.assert_json_items(entity_attr[i], element)
                    i += 1
            elif isinstance(json_value, dict):
                self.assert_json_items(entity_attr, json_value)
            else:
                try:
                    self.assertEqual(
                        datetime.strptime(json_value, "%Y-%m-%d").date(), entity_attr)
                except (TypeError, ValueError):
                    self.assertEqual(json_value, entity_attr)


def load_tests(loader, tests, pattern):
    test_cases = unittest.TestSuite()
    if os.path.exists(PRIVATE_RESOURCES_DIR):
        for filename in os.listdir(PRIVATE_RESOURCES_DIR):
            if filename == ".gitignore":
                continue
            
            with open(os.path.join(PRIVATE_RESOURCES_DIR, filename), "r",
                      encoding="utf-8") as f:
                data = json.loads(f.read())
                test_cases.addTest(
                    TestIntegrationJSON("run_json_test", filename, data))
    return test_cases
