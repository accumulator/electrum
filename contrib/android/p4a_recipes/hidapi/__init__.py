import os

from pythonforandroid.recipes.hidapi import HidapiRecipe
from pythonforandroid.util import load_source

util = load_source('util', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'util.py'))


# assert HidapiRecipe._version == "0.15.0"
assert HidapiRecipe._version == '0b5671548f20d4e2cb4bbb95b7821839da5de146'
assert HidapiRecipe.depends == ['python3', 'libusb', 'libhidapi']
assert HidapiRecipe.python_depends == []


class HidapiRecipePinned(util.InheritedRecipeMixin, HidapiRecipe):
    pass
#     sha512sum = "590ca0f7515792617126d3b619b7db68d926aedafd6fe5eb735677c760ff816dd715ab757fb032100797faa3f2aea0406f30b356099b42d404b9bb11298fb6b4"


recipe = HidapiRecipePinned()
