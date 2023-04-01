import logging
import time
from threading import Timer
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont
from displayhatmini import DisplayHATMini
from dotenv import load_dotenv

from openweathermap import OpenWeatherMap
from utils import Led, Color, timestamp2str, font
from views import ErrorsView

logger = logging.getLogger()

load_dotenv()
owm = OpenWeatherMap()

width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT


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

        self.loadview(ErrorsView)

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

    def loadview(self, viewcls):
        print("loading", viewcls)
        viewcls.render(self)

        def button_callback(pin):
            if not self.displayhatmini.read_button(pin):
                return

            {
                DisplayHATMini.BUTTON_A: viewcls.buttonA,
                DisplayHATMini.BUTTON_B: viewcls.buttonB,
                DisplayHATMini.BUTTON_X: viewcls.buttonX,
                DisplayHATMini.BUTTON_Y: viewcls.buttonY,
            }[pin](self)

        self.button_handler.action = button_callback

        self.loop_handler.action = viewcls.loop
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


app = App()

while True:
    pass
    # time.sleep(1.0 / 30)
