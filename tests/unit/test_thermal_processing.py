from hashlib import sha256

from PIL import Image

from thermal_app.application.dto import RenderOptions
from thermal_app.rendering.thermal import DITHERING_ALGORITHMS, thermalize


def gradient() -> Image.Image:
    image = Image.new("L", (32, 32))
    image.putdata([round(x / 31 * 255) for _y in range(32) for x in range(32)])
    return image


def test_all_four_dithering_algorithms_are_deterministic_and_distinct() -> None:
    hashes = {
        algorithm: sha256(thermalize(gradient(), RenderOptions(dithering=algorithm)).tobytes()).hexdigest()
        for algorithm in DITHERING_ALGORITHMS
    }
    assert len(hashes) == 4
    assert len(set(hashes.values())) == 4
    assert hashes == {
        "threshold": "33a6a74827cff825069372a8c0781df4c87564613f4c581c9831172fd644bdfb",
        "floyd-steinberg": "47858a8516ae83284f93a5c700280214f4f98d37823400b6e213e28391bac3bb",
        "atkinson": "45e1fd2bb6c774a61bce08ec4b7035d46633636c6b1d7cd021d6e4a5d831c41e",
        "ordered-bayer": "04c5b44d5e0775e6a771acd1759c35587c6fb493ecdd0b1e4c9aaf9488b9c2df",
    }


def test_invert_changes_thermal_bitmap() -> None:
    normal = thermalize(gradient(), RenderOptions()).tobytes()
    inverted = thermalize(gradient(), RenderOptions(invert=True)).tobytes()
    assert normal != inverted
