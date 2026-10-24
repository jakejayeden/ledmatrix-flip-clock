"""Animated flip-clock plugin for ChuckBuilds/LEDMatrix."""

from datetime import datetime
import time

from PIL import Image, ImageDraw, ImageFont
from src.plugin_system.base_plugin import BasePlugin


class FlipClockPlugin(BasePlugin):
    """128x32-friendly clock with split-flap minute/hour transitions."""

    def __init__(self, plugin_id, config, display_manager, cache_manager, plugin_manager):
        super().__init__(plugin_id, config, display_manager, cache_manager, plugin_manager)
        self._last_dt = None
        self._last_minute_key = None
        self._load_config(config)
        self.logger.info("Flip Clock plugin initialized")

    def _load_config(self, config):
        config = config or {}
        self.use_24_hour = bool(config.get("use_24_hour", True))
        self.show_weekday = bool(config.get("show_weekday", True))
        self.date_uppercase = bool(config.get("date_uppercase", True))
        self.animation_ms = max(120, min(900, int(config.get("animation_ms", 420))))
        self.animation_frames = max(3, min(10, int(config.get("animation_frames", 7))))

    def on_config_change(self, new_config):
        super().on_config_change(new_config)
        self._load_config(self.config)

    def get_update_interval(self):
        return 1

    def update(self):
        return None

    @property
    def _size(self):
        return int(self.display_manager.width), int(self.display_manager.height)

    def _font(self, size, bold=False, mono=False):
        names = []
        if mono and bold:
            names.append("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
        if mono:
            names.append("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
        if bold:
            names.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        names.append("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        for path in names:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _now(self):
        try:
            config_manager = getattr(self.plugin_manager, "config_manager", None)
            tz_name = config_manager.get_timezone() if config_manager else None
            if tz_name:
                try:
                    import pytz
                    return datetime.now(pytz.timezone(tz_name))
                except (ImportError, Exception):
                    pass
        except Exception as exc:
            self.logger.warning("Could not resolve LEDMatrix timezone: %s", exc)
        return datetime.now()

    def _time_text(self, dt):
        if self.use_24_hour:
            return dt.strftime("%H:%M")
        return dt.strftime("%I:%M").lstrip("0")

    def _layout(self):
        width, _ = self._size
        date_width = 46 if width >= 120 else max(34, width // 3)
        gutter = 3
        divider_x = width - date_width - gutter
        return divider_x, divider_x - 2, divider_x + gutter + 1

    def _fit_time_font(self, box_width, height):
        # DejaVu Sans Mono uses a dotted zero. The regular Sans Bold face has
        # clean, open zero counters while retaining tabular-width numerals, so
        # the clock remains aligned without the centre dots.
        for size in range(height, 7, -1):
            font = self._font(size, bold=True, mono=False)
            bbox = font.getbbox("88:88")
            if bbox[2] - bbox[0] <= box_width and bbox[3] - bbox[1] <= height:
                return font
        return self._font(8, bold=True, mono=False)

    @staticmethod
    def _centered_y(draw, text, font, height):
        bbox = draw.textbbox((0, 0), text, font=font)
        return (height - (bbox[3] - bbox[1])) // 2 - bbox[1]

    def _draw_date(self, draw, dt, x, width, height):
        primary = (235, 235, 235)
        secondary = (150, 150, 150)
        small = self._font(7)
        medium = self._font(8, bold=True)
        weekday = dt.strftime("%a")
        day_month = dt.strftime("%d %b")
        year = dt.strftime("%Y")
        if self.date_uppercase:
            weekday, day_month = weekday.upper(), day_month.upper()
        rows = []
        if self.show_weekday:
            rows.append((weekday, small, secondary))
        rows.extend([(day_month, medium, primary), (year, small, secondary)])
        y = max(0, (height - len(rows) * 9) // 2)
        for text, font, colour in rows:
            draw.text((x, y), text, font=font, fill=colour)
            y += 9

    def _base_canvas(self, dt):
        width, height = self._size
        image = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(image)
        divider_x, _, date_x = self._layout()
        draw.line((divider_x, 4, divider_x, height - 5), fill=(55, 55, 55))
        self._draw_date(draw, dt, date_x, width - date_x, height)
        return image

    def _time_geometry(self, text, draw, font, box_width, height):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = max(0, (box_width - tw) // 2 - bbox[0])
        y = self._centered_y(draw, text, font, height)
        advances = []
        cursor = x
        for ch in text:
            advances.append((ch, int(round(cursor))))
            cursor += draw.textlength(ch, font=font)
        return y, advances

    def _render_static(self, dt):
        image = self._base_canvas(dt)
        draw = ImageDraw.Draw(image)
        _, time_right, _ = self._layout()
        text = self._time_text(dt)
        font = self._fit_time_font(time_right, image.height)
        y, advances = self._time_geometry(text, draw, font, time_right, image.height)
        for ch, x in advances:
            draw.text((x, y), ch, font=font, fill="white")
        return image

    def _render_flip_frame(self, old_dt, new_dt, progress):
        image = self._base_canvas(new_dt)
        draw = ImageDraw.Draw(image)
        _, time_right, _ = self._layout()
        old_text = self._time_text(old_dt).rjust(5)
        new_text = self._time_text(new_dt).rjust(5)
        font = self._fit_time_font(time_right, image.height)
        y, new_positions = self._time_geometry(new_text, draw, font, time_right, image.height)
        _, old_positions = self._time_geometry(old_text, draw, font, time_right, image.height)
        hinge = image.height // 2
        for (new_ch, nx), (old_ch, ox) in zip(new_positions, old_positions):
            x = nx
            if old_ch == new_ch:
                draw.text((x, y), new_ch, font=font, fill="white")
                continue
            cell_w = max(1, int(draw.textlength(new_ch if new_ch.strip() else "0", font=font)) + 1)
            old_layer = Image.new("RGB", image.size, "black")
            new_layer = Image.new("RGB", image.size, "black")
            ImageDraw.Draw(old_layer).text((ox, y), old_ch, font=font, fill="white")
            ImageDraw.Draw(new_layer).text((nx, y), new_ch, font=font, fill="white")
            right = min(image.width, x + cell_w)
            if progress < 0.5:
                image.paste(old_layer.crop((x, hinge, right, image.height)), (x, hinge))
                factor = max(0.03, 1.0 - progress * 2.0)
                upper = old_layer.crop((x, 0, right, hinge))
                upper = upper.resize((upper.width, max(1, int(hinge * factor))))
                image.paste(upper, (x, hinge - upper.height))
            else:
                image.paste(new_layer.crop((x, 0, right, hinge)), (x, 0))
                factor = max(0.03, (progress - 0.5) * 2.0)
                lower = new_layer.crop((x, hinge, right, image.height))
                lower = lower.resize((lower.width, max(1, int((image.height - hinge) * factor))))
                image.paste(lower, (x, hinge))
            ImageDraw.Draw(image).line((x, hinge, min(image.width - 1, x + cell_w), hinge), fill=(70, 70, 70))
        return image

    def _push(self, image):
        self.display_manager.image.paste(image, (0, 0))
        self.display_manager.update_display()

    def _animate_flip(self, old_dt, new_dt):
        delay = (self.animation_ms / 1000.0) / self.animation_frames
        for frame in range(1, self.animation_frames + 1):
            self._push(self._render_flip_frame(old_dt, new_dt, frame / self.animation_frames))
            time.sleep(delay)

    def display(self, force_clear=False):
        try:
            now = self._now()
            minute_key = now.strftime("%Y%m%d%H%M")
            if self._last_minute_key and minute_key != self._last_minute_key and self._last_dt:
                elapsed = abs((now - self._last_dt).total_seconds())
                if elapsed <= 90:
                    self._animate_flip(self._last_dt, now)
                else:
                    self._push(self._render_static(now))
            else:
                self._push(self._render_static(now))
            self._last_dt = now
            self._last_minute_key = minute_key
            return True
        except Exception as exc:
            self.logger.error("Flip Clock display failed: %s", exc, exc_info=True)
            return False
