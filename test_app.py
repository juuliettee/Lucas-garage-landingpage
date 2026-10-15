"""
Root runner for Lucas Garage test suite.
Delegates to tests/test_app.py.
"""
from tests.test_app import run_tests

if __name__ == '__main__':
    run_tests()
