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
    CURRENT = auto()
    FOUR = auto()
    FORECAST_PAGES = auto()
    TIME = auto()
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

    return (datetime
            .fromtimestamp(dt, tz=timezone.utc)
            .astimezone()
            .strftime(fmt)
            )


class App:
    def __init__(self):
        self.mode = AppMode.CURRENT
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
        self.forecasts = []
        self.fidx = 0

        self.clear_and_update()

    def handle(self, exc: Exception):
        logger.exception(exc)
        self.errors.append(exc)
        self.displayhatmini.set_led(0.1, 0, 0)

    def clear(self):
        self.draw.rectangle(xy=((0, 0), (width, height)),
                            fill=Color.BLACK)
        self.displayhatmini.display()
        self.displayhatmini.set_backlight(0.2)

    def clear_and_update(self):
        print(self.mode)

        try:
            if self.mode == AppMode.CURRENT:
                self.current_view()
            elif self.mode == AppMode.FOUR:
                self.four_view()
            elif self.mode == AppMode.FORECAST_PAGES:
                self.forecast_page_view()
            elif self.mode == AppMode.TIME:
                self.time_view()
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

        icon = owm.icon(
            weather["weather"][0]["icon"]
        ).resize((150, 150))
        self.buffer.paste(
            icon,
            box=(width//2 - 75, 40),
            mask=icon,
        )

        temp = weather["main"]["temp"]
        feels_like = weather["main"]["feels_like"]
        humidity = weather["main"]["humidity"]

        self.draw.text(
            xy=(width//2, 25),
            text=f"{temp:.1f} C",
            anchor="mt",
            fill=Color.WHITE,
            font=self.font
        )
        self.draw.text(
            xy=(width//2, 45),
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
                anchor="rt",
                fill=Color.WHITE,
                font=self.font,
            )

        timestr = timestamp2str(weather["dt"])
        self.draw.text(
            xy=(width - self.font.getlength(timestr), height - 20),
            text=timestr,
            anchor="rb",
            fill=Color.RED,
            font=self.font,
        )

    def current_view(self):
        try:
            current_weather = owm.current()
        except Exception as exc:
            self.handle(exc)
            return

        print(current_weather)
        self.paint_weather(current_weather)
        self.draw.text(
            xy=(0, 0), text="Current", fill=Color.WHITE, font=self.font
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
        )

        tempstr = f'{weather["main"]["temp"]:.1f} C'
        minidraw.text(
            xy=((hw - self.font.getlength(tempstr))//2, hh - 30),
            text=tempstr,
            anchor="mt",
            fill=Color.WHITE,
            font=self.font
        )

        self.buffer.paste(mini, box=xy, mask=mini)

    def four_view(self):
        try:
            current_weather = owm.current()
            if (not self.forecasts) or (self.forecasts[0]["dt"] < time.time()):
                self.forecasts = owm.forecasts()
        except Exception as exc:
            self.handle(exc)
            return

        xys = [
            (0, 0), (width // 2, 0), (0, height // 2), (width // 2, height // 2)
        ]

        self.clear()
        self.paint_weather_small(current_weather, xys[0])
        self.paint_weather_small(self.forecasts[0], xys[1])
        self.paint_weather_small(self.forecasts[1], xys[2])
        self.paint_weather_small(self.forecasts[2], xys[3])

    def forecast_page_view(self):
        try:
            if (not self.forecasts) or (self.forecasts[0]["dt"] < time.time()):
                self.forecasts = owm.forecasts()
                self.fidx = 0
        except Exception as exc:
            self.handle(exc)
            return

        self.paint_weather(self.forecasts[self.fidx])
        self.draw.text(
            xy=(0, 0), text="Forecast", fill=Color.WHITE, font=self.font
        )

    def time_view(self):
        dt = datetime.now()
        hhmm = dt.strftime("%H:%M %Z")
        dmy = dt.strftime("%a %d %b %Y")
        self.clear()
        self.draw.text(xy=(0, 0), text=hhmm, fill=Color.WHITE, font=self.font)
        self.draw.text(xy=(0, 20), text=dmy, fill=Color.WHITE, font=self.font)

    def errors_view(self):
        self.displayhatmini.set_led(0, 0, 0)
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
            self.draw.text(xy=(20, y), text=str(exc), fill=Color.RED, font=self.font)
            y += 20
        self.errors = []

    def button_callback(self, pin):
        if not self.displayhatmini.read_button(pin):
            return

        if self.mode in {AppMode.CURRENT, AppMode.FOUR}:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.FORECAST_PAGES
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_B:
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_X:
                self.mode = AppMode.FOUR
                self.clear_and_update()

        elif self.mode == AppMode.FORECAST_PAGES:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.TIME
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx += 1
                self.fidx %= len(self.forecasts)
                self.clear_and_update()
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx -= 1
                self.fidx = max(0, self.fidx)
                self.clear_and_update()

        elif self.mode == AppMode.TIME:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.ERRORS
                self.clear_and_update()

        elif self.mode == AppMode.ERRORS:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.CURRENT
                self.clear_and_update()

        else:
            raise RuntimeError("Unknown operating mode")


app = App()

while True:
    time.sleep(1./30)
    # app.clear_and_update()
