import unittest

from tests.test_etsy_to_lexoffice import TestEtsyConverter  # Assuming correct relative import

# Create a test suite
suite = unittest.TestSuite()

# Add tests to the suite
suite.addTest(unittest.makeSuite(TestEtsyConverter))

# Create a test runner
runner = unittest.TextTestRunner()

# Run the suite
runner.run(suite)