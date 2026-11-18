from pythonforandroid.recipes.cryptography import CryptographyRecipe
from pythonforandroid.util import load_source, HashPinnedDependency

assert CryptographyRecipe._version == "46.0.3"
assert CryptographyRecipe.depends == ['openssl', 'cffi', 'python3'], CryptographyRecipe.depends
assert CryptographyRecipe.python_depends == []


class CryptographyRecipePinned(CryptographyRecipe):
    version = "46.0.7"
    sha512sum = "dea8eaae15d1053e0aa22391c8a4ff84bf002e01e85bb2d694629f74abd5876ba492e982f49c3e928eecc6e1d21376f640d9ca88b4892f05981159e793ec344b"
    hostpython_prerequisites = [
        HashPinnedDependency(
            package="pycparser==3.12",
            hashes=['sha256:a076f3f489b39b43ed13563a1dafe42447445bec2e294154ec5c57fcdda4c85e']),
        HashPinnedDependency(
            package="cffi==2.1.1",
            hashes=['sha256:34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632']),
        HashPinnedDependency(
            package="maturin==1.16.0",
            hashes=['sha256:837db2f4d93d4899c3ac393fb3cc9eebf35b6002336e5d574f4a4fb6c49fe283']),
        ]


recipe = CryptographyRecipePinned()
