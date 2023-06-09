from abc import abstractmethod, ABC
from datetime import datetime, timezone

from utils import Led, Color, ip_str, smallfont, font


class View(ABC):
    def __init__(self, app):
        self.app = app

    @staticmethod
    @abstractmethod
    def render(app):
        pass

    @staticmethod
    def buttonA(app):
        pass

    @staticmethod
    def buttonB(app):
        pass

    @staticmethod
    def buttonX(app):
        pass

    @staticmethod
    def buttonY(app):
        pass

    @staticmethod
    def loop(app):
        pass

    loop_period = 3600


class PageView(View):
    @staticmethod
    def render(app):
        print("Page view, idx", app.fidx)
        try:
            app.update_current_weather()
            app.update_forecasts()
        except Exception as exc:
            app.handle(exc)

        weathers = [app.current_weather, *app.forecasts]

        app.paint_weather(weathers[app.fidx])
        app.draw.text(
            xy=(0, 0),
            text="Current" if app.fidx == 0 else "Forecast",
            fill=Color.WHITE,
            font=font,
        )

    @staticmethod
    def buttonA(app):
        app.loadview(FourView)

    @staticmethod
    def buttonB(app):
        app.loadview(ErrorsView)

    @staticmethod
    def buttonX(app):
        app.fidx = max(0, app.fidx - 1)
        app.loadview(PageView)

    @staticmethod
    def buttonY(app):
        app.fidx = min(len(app.forecasts), app.fidx + 1)
        app.loadview(PageView)

    @staticmethod
    def loop(app):
        app.loadview(PageView)


class FourView(View):
    @staticmethod
    def render(app):
        width, height = app.displayhatmini.WIDTH, app.displayhatmini.HEIGHT
        print("Four view, idx", app.fidx)
        try:
            app.displayhatmini.set_led(*Led.YELLOW)
            app.update_current_weather()
            app.update_forecasts()
            app.displayhatmini.set_led(*Led.OFF)
        except Exception as exc:
            app.handle(exc)

        xys = [
            (0, 0),
            (width // 2, 0),
            (0, height // 2),
            (width // 2, height // 2),
        ]

        app.clear()
        weathers = [app.current_weather, *app.forecasts][
                   app.fidx: app.fidx + 4
                   ]
        for weather, xy in zip(weathers, xys):
            app.paint_weather_small(weather, xy)

    @staticmethod
    def buttonA(app):
        app.loadview(PageView)

    @staticmethod
    def buttonB(app):
        app.loadview(ErrorsView)

    @staticmethod
    def buttonX(app):
        app.fidx = max(0, app.fidx - 4)
        app.loadview(FourView)

    @staticmethod
    def buttonY(app):
        app.fidx = min(len(app.forecasts), app.fidx + 4)
        app.loadview(FourView)

    @staticmethod
    def loop(app):
        app.loadview(FourView)


class ErrorsView(View):
    @staticmethod
    def render(app):
        print("Errors view")
        app.displayhatmini.set_led(*Led.OFF)
        app.clear()

        if app.errors:
            app.draw.text(xy=(0, 0), text="Errors", fill=Color.RED, font=font)
            y = 20
            for exc in app.errors:
                print(str(exc))
                app.draw.text(
                    xy=(20, y), text=str(exc), fill=Color.RED, font=font
                )
                y += 20
            app.errors = []

        else:
            app.draw.text(
                xy=(0, 0), text="No errors!", fill=Color.WHITE, font=font
            )

        y = app.displayhatmini.HEIGHT - 60

        app.displayhatmini.set_led(*Led.YELLOW)
        lines = ip_str()
        app.displayhatmini.set_led(*Led.OFF)
        for line in lines:
            app.draw.text(
                xy=(10, y), text=line, fill=Color.WHITE, font=smallfont
            )
            y += 20

    @staticmethod
    def update_time(app):
        width, height = app.displayhatmini.WIDTH, app.displayhatmini.HEIGHT
        timestr = datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S")
        app.draw.rectangle(
            xy=(0, height // 2 - 20, width, height // 2 + 10),
            fill=Color.BLACK,
        )
        app.draw.text(
            xy=(width // 2, height // 2),
            text=timestr,
            fill=Color.RED,
            font=font,
            anchor="mb",
        )
        app.redraw()

    @staticmethod
    def buttonA(app):
        app.loadview(PageView)

    @staticmethod
    def buttonB(app):
        ip_str.cache_clear()
        app.loadview(ErrorsView)

    @staticmethod
    def loop(app):
        ErrorsView.update_time(app)

    loop_period = 0.5
