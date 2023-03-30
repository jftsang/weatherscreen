import logging
import time
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont
from displayhatmini import DisplayHATMini
from dotenv import load_dotenv

from openweathermap import OpenWeatherMap

logger = logging.getLogger()

load_dotenv()
owm = OpenWeatherMap()

width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT


class AppMode(Enum):
    PAGE = auto()
    FOUR = auto()
    ERRORS = auto()


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


class App:
    def __init__(self):
        self.mode = AppMode.PAGE
        self.errors: List[Exception] = []

        self.buffer = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.buffer)
        try:
            self.font = ImageFont.truetype(
                "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20
            )
        except OSError:
            self.font = ImageFont.load_default()

        self.displayhatmini = DisplayHATMini(
            buffer=self.buffer, backlight_pwm=True
        )
        self.displayhatmini.on_button_pressed(self.button_callback)
        self.current_weather = None
        self.forecasts = []
        self.fidx = 0

        self.clear_and_update()

    def handle(self, exc: Exception):
        logger.exception(exc)
        self.errors.append(exc)
        self.displayhatmini.set_led(*Led.RED)

    def clear(self):
        self.draw.rectangle(xy=((0, 0), (width, height)), fill=Color.BLACK)
        self.displayhatmini.display()
        self.displayhatmini.set_backlight(0.2)

    def clear_and_update(self):
        print(self.mode)

        try:
            if self.mode == AppMode.PAGE:
                self.page_view()
            elif self.mode == AppMode.FOUR:
                self.four_view()
            elif self.mode == AppMode.ERRORS:
                self.errors_view()
            else:
                raise NotImplementedError(f"Can't handle mode {self.mode}")
        except Exception as exc:
            self.handle(exc)

        self.displayhatmini.display()

    def paint_weather(self, weather: Dict[str, Any]):
        print(weather)
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
            text=f"{temp:.1f} C",
            anchor="mt",
            fill=Color.WHITE,
            font=self.font,
        )
        self.draw.text(
            xy=(width // 2, 45),
            text=f"(feels like {feels_like:.1f} C)",
            anchor="mt",
            fill=Color.WHITE,
            font=self.font,
        )

        location = weather.get("name")
        if location is not None:
            self.draw.text(
                xy=(width - self.font.getlength(location), 0),
                text=location,
                fill=Color.WHITE,
                font=self.font,
            )

        timestr = timestamp2str(weather["dt"])
        self.draw.text(
            xy=(width - self.font.getlength(timestr), height - 20),
            text=timestr,
            fill=Color.RED,
            font=self.font,
        )

    def update_current_weather(self):
        if (
            self.current_weather is not None
            and (time.time() - self.current_weather["dt"]) < 300
        ):
            return

        self.displayhatmini.set_led(*Led.YELLOW)
        self.current_weather = owm.current()
        print(self.current_weather)
        self.displayhatmini.set_led(*Led.OFF)

    def update_forecasts(self):
        print(self.forecasts and self.forecasts[0]["dt"])
        print(time.time())
        print(self.forecasts and self.forecasts[0]["dt"] - time.time())
        if (
            self.forecasts
            and self.forecasts[0]["dt"] >= time.time() + 3600 * 1.5
        ):
            print("Skipping an update")
            return

        self.displayhatmini.set_led(*Led.YELLOW)
        self.forecasts = owm.forecasts()
        self.displayhatmini.set_led(*Led.OFF)
        self.fidx = 0

    def page_view(self):
        try:
            self.update_current_weather()
            self.update_forecasts()
        except Exception as exc:
            self.handle(exc)
            return

        print(self.fidx)

        weathers = [self.current_weather, *self.forecasts]
        self.paint_weather(weathers[self.fidx])
        self.draw.text(
            xy=(0, 0),
            text="Current" if self.fidx == 0 else "Forecast",
            fill=Color.WHITE,
            font=self.font,
        )

    def paint_weather_small(self, weather, xy):
        hw = width // 2
        hh = height // 2
        mini = Image.new("RGBA", (hw, hh), Color.BLACK)
        minidraw = ImageDraw.Draw(mini)
        icon = owm.icon(weather["weather"][0]["icon"]).resize((80, 80))
        mini.paste(icon, box=(hw // 2 - 40, hh // 2 - 40), mask=icon)
        timestr = timestamp2str(weather["dt"], short=True)
        minidraw.text(
            xy=((hw - self.font.getlength(timestr)) // 2, 20),
            text=timestr,
            fill=Color.WHITE,
            font=self.font,
        )

        tempstr = f'{weather["main"]["temp"]:.1f} C'
        minidraw.text(
            xy=((hw - self.font.getlength(tempstr)) // 2, hh - 30),
            text=tempstr,
            fill=Color.WHITE,
            font=self.font,
        )

        self.buffer.paste(mini, box=xy, mask=mini)

    def four_view(self):
        try:
            self.displayhatmini.set_led(*Led.YELLOW)
            self.update_current_weather()
            self.update_forecasts()
            self.displayhatmini.set_led(*Led.OFF)
        except Exception as exc:
            self.handle(exc)
            return

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
        # self.paint_weather_small(self.current_weather, xys[0])
        # self.paint_weather_small(self.forecasts[0], xys[1])
        # self.paint_weather_small(self.forecasts[1], xys[2])
        # self.paint_weather_small(self.forecasts[2], xys[3])

    def errors_view(self):
        self.displayhatmini.set_led(*Led.OFF)
        self.clear()

        if not self.errors:
            self.draw.text(
                xy=(0, 0), text="No errors!", fill=Color.WHITE, font=self.font
            )
            return

        self.draw.text(
            xy=(0, 0), text="Errors", fill=Color.RED, font=self.font
        )
        y = 20
        for exc in self.errors:
            print(str(exc))
            self.draw.text(
                xy=(20, y), text=str(exc), fill=Color.RED, font=self.font
            )
            y += 20
        self.errors = []

    def button_callback(self, pin):
        if not self.displayhatmini.read_button(pin):
            return

        if self.mode == AppMode.PAGE:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.FOUR
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx -= 1
                self.fidx = max(0, self.fidx)
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx += 1
                self.fidx = min(len(self.forecasts) + 1, self.fidx)
                self.clear_and_update()

        elif self.mode == AppMode.FOUR:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.ERRORS
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx -= 4
                self.fidx = max(0, self.fidx)
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx += 4
                self.fidx = min(len(self.forecasts), self.fidx)
                self.clear_and_update()

        elif self.mode == AppMode.ERRORS:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.PAGE
                self.clear_and_update()

        else:
            raise RuntimeError("Unknown operating mode")


app = App()

while True:
    time.sleep(1.0 / 30)
    # app.clear_and_update()
