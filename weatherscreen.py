from enum import Enum, auto

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


class App:
    def __init__(self):
        self.mode = AppMode.CURRENT

        self.buffer = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.buffer)
        self.font = ImageFont.load_default()

        self.displayhatmini = DisplayHATMini(
            buffer=self.buffer, backlight_pwm=True
        )
        self.displayhatmini.on_button_pressed(self.button_callback)
        self.clear_and_update()

    def clear_and_update(self):
        self.draw.rectangle(xy=((0, 0), (100, 50)),
                            fill=Color.BLACK)
        self.displayhatmini.set_backlight(0.2)

        if self.mode == AppMode.CURRENT:
            self.current_view()
        elif self.mode == AppMode.FORECAST:
            self.forecast_view()
        else:
            ...  # NotImplemented

        self.displayhatmini.display()

    def current_view(self):
        self.draw.text(xy=(0, 0), text="Current", fill=Color.BLACK, font=self.font)

    def forecast_view(self):
        self.draw.text(xy=(0, 0), text="5-day forecast", fill=Color.BLACK, font=self.font)

    def button_callback(self, pin):
        if not self.displayhatmini.read_button(pin):
            return

        if pin == DisplayHATMini.BUTTON_A:
            self.mode = AppMode.CURRENT
        elif pin == DisplayHATMini.BUTTON_B:
            self.mode = AppMode.FORECAST
        else:
            ...  # NotImplemented


# App().clear_and_update()
App()

OpenWeatherMap().current()
