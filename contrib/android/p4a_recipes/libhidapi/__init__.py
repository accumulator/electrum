import os

from pythonforandroid.recipes.libhidapi import LibHidapiRecipe
from pythonforandroid.util import load_source

assert LibHidapiRecipe._version == "0.14.0"
assert LibHidapiRecipe.depends == ['python3', 'libusb']
assert LibHidapiRecipe.python_depends == []

util = load_source('util', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'util.py'))


class LibHidapiRecipePinned(util.InheritedRecipeMixin, LibHidapiRecipe):
    sha512sum = "66a045144f90b41438898b82f0398e80223323ebfe6e4f197d2713696bb3ae60f36aea5a37a9999b34b12294783fd7e4c28c6e785462559cbe21276009da1eac"


recipe = LibHidapiRecipePinned()
