import os

from pythonforandroid.recipes.libhidapi import LibHidapiRecipe
from pythonforandroid.util import load_source

assert LibHidapiRecipe._version == "0.15.0"
assert LibHidapiRecipe.depends == ['python3', 'libusb']
assert LibHidapiRecipe.python_depends == []

util = load_source('util', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'util.py'))


class LibHidapiRecipePinned(util.InheritedRecipeMixin, LibHidapiRecipe):
    sha512sum = "a4ddd13a80a84956872fa52aa861b40e4959f301d8d91afe0feaf9dbd87394561e1fdd20cbf8cf47200845f80a8db8a934bc2e3025fe6f16435e37c17621e7b6"


recipe = LibHidapiRecipePinned()
