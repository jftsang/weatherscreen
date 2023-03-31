import logging
import time
from datetime import datetime, timezone
from functools import lru_cache
from threading import Thread, Timer
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont
from displayhatmini import DisplayHATMini
from dotenv import load_dotenv
from netifaces import interfaces, ifaddresses, AF_INET

from openweathermap import OpenWeatherMap

logger = logging.getLogger()

load_dotenv()
owm = OpenWeatherMap()

width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT


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


class CallbackHandler:
    def __init__(self, app):
        self.app = app
        self.action = lambda pin: None

    def act(self, pin):
        self.action(pin)


class LoopHandler:
    def __init__(self, app, action=None):
        self.app = app
        self.action = action

    def act(self):
        if self.action is not None:
            try:
                self.action(self.app)
            except Exception as exc:
                self.app.handle(exc)

        Timer(60, self.act).start()


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


class App:
    def __init__(self):
        print("Initializing app...")
        self.errors: List[Exception] = []

        self.buffer = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.buffer)

        self.displayhatmini = DisplayHATMini(
            buffer=self.buffer, backlight_pwm=True
        )

        # You can only make one call to DisplayHATMini.on_button_pressed
        # so if you want to change the callback dynamically you must use
        # a handler like this.
        self.button_handler = CallbackHandler(self)
        self.displayhatmini.on_button_pressed(self.button_handler.act)

        self.current_weather = None
        self.forecasts = []
        self.last_update_forecasts: float = 0
        self.fidx: int = 0

        self.loop_handler = LoopHandler(self)
        self.loop_handler.act()

        self.errors_view()

    def handle(self, exc: Exception):
        logger.exception(exc)
        self.errors.append(exc)
        self.displayhatmini.set_led(*Led.RED)

    def clear(self):
        self.draw.rectangle(xy=((0, 0), (width, height)), fill=Color.BLACK)

    def redraw(self):
        self.displayhatmini.display()

    def paint_weather(self, weather: Dict[str, Any]):
        self.clear()

        icon = owm.icon(weather["weather"][0]["icon"]).resize((150, 150))
        self.buffer.paste(
            icon,
            box=(width // 2 - 75, 40),
            mask=icon,
        )

        temp = weather["main"]["temp"]
        feels_like = weather["main"]["feels_like"]
        humidity = weather["main"]["humidity"]

        self.draw.text(
            xy=(width // 2, 25),
            text=f"{temp:.1f} °C, {humidity:.0f}% 💧",
            anchor="mt",
            fill=Color.WHITE,
            font=font,
        )
        self.draw.text(
            xy=(width // 2, 45),
            text=f"(feels like {feels_like:.1f} °C)",
            anchor="mt",
            fill=Color.WHITE,
            font=font,
        )

        location = weather.get("name")
        if location is not None:
            self.draw.text(
                xy=(width - font.getlength(location), 0),
                text=location,
                fill=Color.WHITE,
                font=font,
            )

        timestr = timestamp2str(weather["dt"])
        self.draw.text(
            xy=(width - font.getlength(timestr), height - 20),
            text=timestr,
            fill=Color.RED,
            font=font,
        )

    def update_current_weather(self):
        if (
            self.current_weather is not None
            and (time.time() - self.current_weather["dt"]) < 60
        ):
            print("Skipping current weather update...")
            return

        print("Updating current weather...")
        self.displayhatmini.set_led(*Led.YELLOW)
        self.current_weather = owm.current()
        self.displayhatmini.set_led(*Led.OFF)

    def update_forecasts(self):
        if self.forecasts and self.last_update_forecasts >= time.time() - 3600:
            print("Skipping forecast update...")
            return

        print("Updating forecasts...")
        self.displayhatmini.set_led(*Led.YELLOW)
        self.forecasts = owm.forecasts()
        self.last_update_forecasts = time.time()
        self.displayhatmini.set_led(*Led.OFF)

    def page_view(self):
        print("Page view")
        try:
            self.update_current_weather()
            self.update_forecasts()
        except Exception as exc:
            self.handle(exc)

        weathers = [self.current_weather, *self.forecasts]

        self.paint_weather(weathers[self.fidx])
        self.draw.text(
            xy=(0, 0),
            text="Current" if self.fidx == 0 else "Forecast",
            fill=Color.WHITE,
            font=font,
        )

        def button_callback(pin):
            if not self.displayhatmini.read_button(pin):
                return
            if pin == DisplayHATMini.BUTTON_A:
                self.four_view()
            elif pin == DisplayHATMini.BUTTON_B:
                self.errors_view()
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx -= 1
                self.fidx = max(0, self.fidx)
                self.page_view()
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx += 1
                self.fidx = min(len(self.forecasts) + 1, self.fidx)
                self.page_view()

        self.button_handler.action = button_callback
        self.loop_handler.action = App.page_view
        self.redraw()

    def paint_weather_small(self, weather, xy):
        hw = width // 2
        hh = height // 2
        mini = Image.new("RGBA", (hw, hh), Color.BLACK)
        minidraw = ImageDraw.Draw(mini)
        icon = owm.icon(weather["weather"][0]["icon"]).resize((80, 80))
        mini.paste(icon, box=(hw // 2 - 40, hh // 2 - 40), mask=icon)
        timestr = timestamp2str(weather["dt"], short=True)
        minidraw.text(
            xy=((hw - font.getlength(timestr)) // 2, 20),
            text=timestr,
            fill=Color.WHITE,
            font=font,
        )

        tempstr = f'{weather["main"]["temp"]:.1f} °C, {weather["main"]["humidity"]:.0f}%'
        minidraw.text(
            xy=((hw - font.getlength(tempstr)) // 2, hh - 30),
            text=tempstr,
            fill=Color.WHITE,
            font=font,
        )

        self.buffer.paste(mini, box=xy, mask=mini)

    def four_view(self):
        print("Four view")
        try:
            self.displayhatmini.set_led(*Led.YELLOW)
            self.update_current_weather()
            self.update_forecasts()
            self.displayhatmini.set_led(*Led.OFF)
        except Exception as exc:
            self.handle(exc)

        xys = [
            (0, 0),
            (width // 2, 0),
            (0, height // 2),
            (width // 2, height // 2),
        ]

        self.clear()
        weathers = [self.current_weather, *self.forecasts][
            self.fidx : self.fidx + 4
        ]
        for weather, xy in zip(weathers, xys):
            self.paint_weather_small(weather, xy)

        def button_callback(pin):
            if not self.displayhatmini.read_button(pin):
                return
            if pin == DisplayHATMini.BUTTON_A:
                self.page_view()
            elif pin == DisplayHATMini.BUTTON_B:
                self.errors_view()
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx -= 4
                self.fidx = max(0, self.fidx)
                self.four_view()
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx += 4
                self.fidx = min(len(self.forecasts), self.fidx)
                self.four_view()

        self.button_handler.action = button_callback
        self.loop_handler.action = App.four_view
        self.redraw()

    def errors_view(self):
        print("Errors view")
        self.displayhatmini.set_led(*Led.OFF)
        self.clear()

        if self.errors:
            self.draw.text(xy=(0, 0), text="Errors", fill=Color.RED, font=font)
            y = 20
            for exc in self.errors:
                print(str(exc))
                self.draw.text(
                    xy=(20, y), text=str(exc), fill=Color.RED, font=font
                )
                y += 20
            self.errors = []

        else:
            self.draw.text(
                xy=(0, 0), text="No errors!", fill=Color.WHITE, font=font
            )

        y = height - 60
        for line in ip_str():
            self.draw.text(
                xy=(10, y), text=line, fill=Color.WHITE, font=smallfont
            )
            y += 20

        def button_callback(pin):
            if not self.displayhatmini.read_button(pin):
                return
            if pin == DisplayHATMini.BUTTON_A:
                self.page_view()

        self.button_handler.action = button_callback
        self.loop_handler.action = None
        self.redraw()
        print("Errors view done")


app = App()


while True:
    pass
    # time.sleep(1.0 / 30)
