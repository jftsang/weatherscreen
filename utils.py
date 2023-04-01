from datetime import datetime, timezone
from functools import lru_cache
from threading import Thread

from PIL import ImageFont
from netifaces import interfaces, ifaddresses, AF_INET


@lru_cache()
def ip_str():
    print("Working out ip addresses...")
    ip_str_lines = []
    for ifaceName in interfaces():
        addresses = [
            i["addr"]
            for i in ifaddresses(ifaceName).setdefault(
                AF_INET, [{"addr": "No IP addr"}]
            )
        ]
        ip_str_lines.append(f"{ifaceName}: {' '.join(addresses)}")

    print("\n".join(ip_str_lines))
    return ip_str_lines


Thread(target=ip_str).run()


class Color:
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    WHITE = (255, 255, 255)


def timestamp2str(dt: int, short: bool = False) -> str:
    if short:
        fmt = "%H:%M %a"
    else:
        fmt = "%a %d %b, %H:%M %Z"

    return (
        datetime.fromtimestamp(dt, tz=timezone.utc).astimezone().strftime(fmt)
    )


class Led:
    OFF = (0, 0, 0)
    YELLOW = (0.1, 0.1, 0)
    RED = (0.1, 0, 0)


try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20
    )
    smallfont = ImageFont.truetype(
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 12
    )
except OSError:
    font = ImageFont.load_default()
    smallfont = ImageFont.load_default()
