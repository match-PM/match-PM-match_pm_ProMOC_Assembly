"""Bridge unittest discovery to pytest for colcon test."""

from . import test_unittest_bridge


def load_tests(loader, standard_tests, pattern):
    return loader.loadTestsFromModule(test_unittest_bridge)
