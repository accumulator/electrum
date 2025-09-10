import os

from pythonforandroid.recipes.hidapi import HidapiRecipe
from pythonforandroid.util import load_source

util = load_source('util', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'util.py'))


# assert HidapiRecipe._version == "0.14.0.post2"
assert HidapiRecipe._version == 'bb52ce495fc9c9fcdc0909cb9902666138f9e3cd'
assert HidapiRecipe.depends == ['python3', 'libusb', 'libhidapi']
assert HidapiRecipe.python_depends == []


class HidapiRecipePinned(util.InheritedRecipeMixin, HidapiRecipe):
    pass
#     sha512sum = "565184520e5733b8602c5f81607f071b20268c7deeead31982ed035810ce66fc67c923456e8dd2c823fbad3231c80dcea84b34cceb88719a45badda9c3a873f9"


recipe = HidapiRecipePinned()
