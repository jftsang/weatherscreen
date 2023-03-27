import time
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict

from PIL import Image, ImageDraw, ImageFont
from displayhatmini import DisplayHATMini
from dotenv import load_dotenv

from openweathermap import OpenWeatherMap

load_dotenv()
owm = OpenWeatherMap()

width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT


class AppMode(Enum):
    CURRENT = auto()
    FORECAST = auto()


class Color:
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    WHITE = (255, 255, 255)


def timestamp2str(dt: int) -> str:
    return (datetime
            .fromtimestamp(dt, tz=timezone.utc)
            .astimezone()
            .strftime("%a %d %b, %H:%M %Z")
            )


class App:
    def __init__(self):
        self.mode = AppMode.CURRENT

        self.buffer = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.buffer)
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20)

        self.displayhatmini = DisplayHATMini(
            buffer=self.buffer, backlight_pwm=True
        )
        self.displayhatmini.on_button_pressed(self.button_callback)
        self.forecasts = []
        self.fidx = 0

        self.clear_and_update()

    def clear_and_update(self):
        self.draw.rectangle(xy=((0, 0), (width, height)),
                            fill=Color.BLACK)
        self.displayhatmini.display()
        self.displayhatmini.set_backlight(0.2)

        if self.mode == AppMode.CURRENT:
            self.current_view()
        elif self.mode == AppMode.FORECAST:
            self.forecast_view()
        else:
            ...  # NotImplemented

        self.displayhatmini.display()

    def paint_weather(self, weather: Dict[str, Any]):
        print(weather)
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

        self.draw.text(
            xy=(width, 0),
            text=weather.get("name", ""),
            anchor="rt",
            fill=Color.WHITE,
            font=self.font,
        )
        self.draw.text(
            xy=(width, height),
            text=timestamp2str(weather["dt"]),
            anchor="rb",
            fill=Color.WHITE,
            font=self.font,
        )

    def current_view(self):
        current_weather = owm.current()
        print(current_weather)
        self.paint_weather(current_weather)
        self.draw.text(
            xy=(0, 0), text="Current", fill=Color.WHITE, font=self.font
        )

    def forecast_view(self):
        if (not self.forecasts) or (self.forecasts[0]["dt"] < time.time()):
            self.forecasts = owm.forecasts()
            self.fidx = 0

        self.paint_weather(self.forecasts[self.fidx])
        self.draw.text(
            xy=(0, 0), text="Forecast", fill=Color.WHITE, font=self.font
        )

    def button_callback(self, pin):
        if not self.displayhatmini.read_button(pin):
            return

        if self.mode == AppMode.CURRENT:
            if pin == DisplayHATMini.BUTTON_B:
                self.mode = AppMode.FORECAST

        elif self.mode == AppMode.FORECAST:
            if pin == DisplayHATMini.BUTTON_A:
                self.mode = AppMode.CURRENT
            elif pin == DisplayHATMini.BUTTON_X:
                self.fidx += 1
                self.fidx %= len(self.forecasts)
            elif pin == DisplayHATMini.BUTTON_Y:
                self.fidx -= 1
                self.fidx = max(0, self.fidx)

        else:
            raise RuntimeError("Unknown operating mode")

        self.clear_and_update()


App()

while True:
    time.sleep(1.0 / 30)
