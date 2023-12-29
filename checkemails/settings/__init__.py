'''
Init
'''
# pylint: disable=wildcard-import
try:
    from .development import *
except ImportError:
    from .default import *
