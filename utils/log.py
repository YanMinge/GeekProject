import time 
import os

PRINT_LEVEL_NONE = 5
PRINT_LEVEL_VERBOSE = 4
PRINT_LEVEL_DEBUG = 3
PRINT_LEVEL_INFO = 2
PRINT_LEVEL_WARN = 1
PRINT_LEVEL_ERROR = 0

print_level = PRINT_LEVEL_DEBUG

def verbose_print(args):
    if print_level >= PRINT_LEVEL_VERBOSE:
        print(args)

def debug_print(args):
    if print_level >= PRINT_LEVEL_DEBUG:
        print(args)

def warn_print(args):
    if print_level >= PRINT_LEVEL_WARN:
        print(args)

def info_print(args):
    if print_level >= PRINT_LEVEL_INFO:
        print(args)

def error_print(args):
    if print_level >= PRINT_LEVEL_ERROR:
        print(args)