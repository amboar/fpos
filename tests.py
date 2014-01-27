#!/usr/bin/python3

import unittest
import tests

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)
