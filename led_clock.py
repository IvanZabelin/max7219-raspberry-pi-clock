"""
MAX7219 LED clock (luma.led_matrix), 32x8 friendly.

Features:
- Right-aligned HH:MM with custom colon (two dots; adjustable vertical gap)
- CPU temperature on the left (tiny 3x5 font, width-aware so time never jumps)
- English ASCII date ticker (e.g., "Sun 10 Aug 2025"), scrolls at set interval
- Auto brightness day/night by time window (cross-midnight supported)
- Seconds progress bar along the bottom edge
- Hour "sparkle" animation at the start of each hour
- Minute-change swipe animation (new time slides in from the right)
- Clean shutdown on SIGINT/SIGTERM

All knobs are configurable via environment variables (see cheatsheet at bottom).
"""

import os
import re
import time
import random
import signal
import subprocess
from datetime import datetime

from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.render import canvas
from luma.core.legacy import text as legacy_text, textsize
from luma.core.legacy.font import proportional, TINY_FONT, SINCLAIR_FONT

# ------------------ Globals ------------------
stop = False

# ------------------ ENV helpers ------------------
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

def _env_bool(name: str, default: int = 1) -> bool:
    try:
        return bool(int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return bool(default)

def _parse_hhmm(s: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = map(int, s.split(":"))
        return (h % 24, m % 60)
    except Exception:
        return fallback

def _in_window(now: datetime, start_hm: tuple[int, int], end_hm: tuple[int, int]) -> bool:
    """True if current time is within [start, end) minutes; handles windows crossing midnight."""
    cur = now.hour * 60 + now.minute
    s = start_hm[0] * 60 + start_hm[1]
    e = end_hm[0] * 60 + end_hm[1]
    if s <= e:
        return s <= cur < e            # normal window
    else:
        return cur >= s or cur < e     # crosses midnight

def handle_signal(signum, frame):
    global stop
    stop = True

# ------------------ Sensors ------------------
def get_cpu_temp_c():
    """Return CPU temperature in °C (float) or None if unavailable."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        pass
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], stderr=subprocess.DEVNULL).decode()
        m = re.search(r"temp=([\d\.]+)", out)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None

# ------------------ Tiny 3x5 font for temperature ------------------
DIGITS_3x5 = {
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "100", "100"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    "-": ["000", "000", "111", "000", "000"],
    "C": ["111", "100", "100", "100", "111"],
}

def small35_text_size(txt: str, spacing: int = 1):
    """Compute width/height of 3x5 text."""
    w = 0
    for i, ch in enumerate(txt):
        if ch in DIGITS_3x5:
            w += 3
            if i != len(txt) - 1:
                w += spacing
    return w, 5

def draw_small35(draw, x: int, y: int, txt: str, spacing: int = 1):
    """Draw 3x5 text at (x, y)."""
    cx = x
    for i, ch in enumerate(txt):
        glyph = DIGITS_3x5.get(ch)
        if not glyph:
            continue
        for ry, row in enumerate(glyph):
            for rx, bit in enumerate(row):
                if bit == "1":
                    draw.point((cx + rx, y + ry), fill="white")
        cx += 3
        if i != len(txt) - 1:
            cx += spacing

# ------------------ Time rendering with custom colon ------------------
def draw_time_with_custom_colon(draw, device, timestr: str, font, blink: bool,
                                left_reserved: int, gap: int = 1, colon_w: int = 1,
                                colon_vgap: int = 2, time_offset: int = 0):
    """
    Draw right-aligned time HH:MM.
    Custom colon: two stacked dots in one column, vertical gap = colon_vgap.
    left_reserved = pixels occupied on the left by the widget (temperature).
    time_offset = additional horizontal offset (positive -> move right), used for swipe animation.
    """
    if ":" in timestr:
        hh, mm = timestr.split(":", 1)
    else:
        hh, mm = "88", "88"

    w_h, h = textsize(hh, font=font)
    w_m, _ = textsize(mm, font=font)
    w_time = w_h + gap + colon_w + gap + w_m

    # If not enough room, shrink reserved left area so time never shifts
    if left_reserved + w_time > device.width:
        left_reserved = max(0, device.width - w_time)

    x0 = max(0, device.width - (left_reserved + w_time)) + time_offset
    y = max(0, (device.height - h) // 2)

    # Hours
    legacy_text(draw, (x0 + left_reserved, y), hh, font=font, fill="white")

    # Colon (two dots, vertically separated by colon_vgap)
    cx = x0 + left_reserved + w_h + gap
    if not blink:
        t1 = y + max(0, (h - 1 - colon_vgap) // 2)
        t2 = min(y + h - 1, t1 + colon_vgap)
        draw.point((cx, t1), fill="white")
        draw.point((cx, t2), fill="white")

    # Minutes
    legacy_text(draw, (cx + colon_w + gap, y), mm, font=font, fill="white")

# ------------------ ASCII English date ticker ------------------
WD_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MO_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_en_date(dt: datetime, with_year: bool = True) -> str:
    base = f"{WD_EN[(dt.weekday()) % 7]} {dt.day:02d} {MO_EN[dt.month - 1]}"
    return f"{base} {dt.year}" if with_year else base

def marquee_once_legacy(device, text_ascii: str, font, speed=0.07, gap=16):
    """Scroll ASCII string using legacy font."""
    w, h = textsize(text_ascii, font=font)
    total = device.width + w + gap
    for offset in range(0, total, 1):  # 1 px step
        if stop:
            return
        x = device.width - offset
        y = max(0, (device.height - h) // 2)
        with canvas(device) as draw:
            legacy_text(draw, (x, y), text_ascii, font=font, fill="white")
        time.sleep(speed)

# ------------------ Visual add-ons ------------------
def draw_seconds_bar(draw, now_dt: datetime, width: int, y: int, dotted: bool = False):
    """Bottom progress bar for current second (0..59)."""
    frac = (now_dt.second + now_dt.microsecond / 1_000_000.0) / 60.0
    filled = int(frac * width)
    if dotted:
        for x in range(0, filled, 2):
            draw.point((x, y), fill="white")
    else:
        for x in range(filled):
            draw.point((x, y), fill="white")

def hour_sparkle(device, duration: float = 0.45, density: float = 0.15, fps: int = 20):
    """Short random sparkle animation across the whole display."""
    frame_dt = 1.0 / max(1, fps)
    t_end = time.monotonic() + max(0.05, duration)
    while time.monotonic() < t_end and not stop:
        with canvas(device) as draw:
            for x in range(device.width):
                for y in range(device.height):
                    if random.random() < density:
                        draw.point((x, y), fill="white")
        time.sleep(frame_dt)

def minute_swipe(device, timestr: str, time_font, blink: bool,
                 left_reserved: int, colon_vgap: int,
                 temp_txt: str | None, swipe_px: int = 8, frame_delay: float = 0.03):
    """
    Slide-in animation for minute change: new time slides in from the right by 'swipe_px'.
    Temp widget stays static on the left.
    """
    swipe_px = max(1, swipe_px)
    for dx in range(swipe_px, -1, -1):
        if stop:
            return
        with canvas(device) as draw:
            # draw temp (static)
            if temp_txt:
                y0 = (device.height - 5) // 2
                draw_small35(draw, 0, y0, temp_txt, spacing=1)
            # draw time with positive offset (shift to the right)
            draw_time_with_custom_colon(draw, device, timestr, time_font, blink=False,
                                        left_reserved=left_reserved, gap=1,
                                        colon_w=1, colon_vgap=colon_vgap, time_offset=dx)
        time.sleep(frame_delay)

# ------------------ Main ------------------
def main():
    # --- Display & hardware ---
    port        = _env_int("LED_SPI_PORT", 0)
    device_idx  = _env_int("LED_SPI_DEVICE", 0)
    bus_hz      = _env_int("LED_BUS_HZ", 16_000_000)
    cascaded    = _env_int("LED_CASCADED", 4)
    orientation = _env_int("LED_ORIENTATION", -90)  # -90, 0, 90
    rotate      = _env_int("LED_ROTATE", 0)         # 0..3

    # --- Fonts ---
    time_font_sel   = _env_int("LED_FONT", 1)           # 1=TINY, 2=SINCLAIR
    time_font       = proportional(SINCLAIR_FONT) if time_font_sel == 2 else proportional(TINY_FONT)
    ticker_font_sel = _env_int("LED_TICKER_FONT", 1)    # 1=TINY, 2=SINCLAIR
    ticker_font     = proportional(SINCLAIR_FONT) if ticker_font_sel == 2 else proportional(TINY_FONT)

    # --- Time / colon ---
    time_fmt    = os.getenv("LED_TIME_FMT", "%H:%M")
    blink_colon = _env_int("LED_BLINK_COLON", 1)
    colon_vgap  = _env_int("LED_COLON_VGAP", 2)         # vertical gap between colon dots

    # --- Ticker (English ASCII) ---
    ticker_every     = _env_float("LED_TICKER_EVERY", 60.0)
    ticker_speed     = _env_float("LED_TICKER_SPEED", 0.07)
    ticker_gap       = _env_int("LED_TICKER_GAP", 16)
    ticker_with_year = _env_int("LED_TICKER_WITH_YEAR", 1)

    # --- Temperature widget ---
    show_temp   = _env_int("LED_DRAW_TEMP", 1)
    show_unit_c = _env_int("LED_TEMP_SHOW_C", 1)

    # --- Auto brightness (day/night) ---
    auto_dim   = _env_bool("LED_AUTO_DIM", 1)
    day_brt    = _env_int("LED_BRIGHTNESS_DAY", 12)     # 0..255
    night_brt  = _env_int("LED_BRIGHTNESS_NIGHT", 3)    # 0..255
    night_from = _parse_hhmm(os.getenv("LED_NIGHT_FROM", "22:30"), (22, 30))
    night_to   = _parse_hhmm(os.getenv("LED_NIGHT_TO",   "07:00"), (7, 0))

    # --- Visual toggles ---
    seconds_bar       = _env_bool("LED_SECONDS_BAR", 1)
    seconds_bar_dots  = _env_bool("LED_SECONDS_BAR_DOTTED", 0)
    sparkle_on_hour   = _env_bool("LED_SPARKLE_ON_HOUR", 1)
    sparkle_duration  = _env_float("LED_SPARKLE_DURATION", 0.45)
    sparkle_density   = _env_float("LED_SPARKLE_DENSITY", 0.15)
    sparkle_fps       = _env_int("LED_SPARKLE_FPS", 20)
    minute_swipe_en   = _env_bool("LED_MINUTE_SWIPE", 1)
    minute_swipe_px   = _env_int("LED_MINUTE_SWIPE_PX", 8)
    minute_swipe_dt   = _env_float("LED_MINUTE_SWIPE_DELAY", 0.03)

    # --- Init hardware ---
    serial = spi(port=port, device=device_idx, gpio=noop(), bus_speed_hz=bus_hz)
    device = max7219(serial, cascaded=cascaded, block_orientation=orientation, rotate=rotate)

    # Apply initial brightness based on current time
    def _apply_brightness(now: datetime):
        target = night_brt if _in_window(now, night_from, night_to) else day_brt
        device.contrast(target)
        return target

    current_brt = _apply_brightness(datetime.now())
    last_minute_for_dim = -1

    # Track last rendered minute for swipe
    last_rendered_minute = None

    # Signals
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        last_ticker_ts = time.monotonic()
        while not stop:
            now = datetime.now()

            # Auto-dim check once per minute
            if auto_dim and now.minute != last_minute_for_dim:
                last_minute_for_dim = now.minute
                target = night_brt if _in_window(now, night_from, night_to) else day_brt
                if target != current_brt:
                    device.contrast(target)
                    current_brt = target

            # Hour sparkle at exactly 00 seconds
            if sparkle_on_hour and now.minute == 0 and now.second == 0:
                hour_sparkle(device, duration=sparkle_duration,
                             density=sparkle_density, fps=sparkle_fps)

            # Ticker: scroll date periodically (skip if we are on the exact hour second 0 to avoid conflict)
            if time.monotonic() - last_ticker_ts >= ticker_every and not (now.minute == 0 and now.second == 0):
                txt = format_en_date(now, with_year=bool(ticker_with_year))
                marquee_once_legacy(device, txt, font=ticker_font, speed=ticker_speed, gap=ticker_gap)
                last_ticker_ts = time.monotonic()

            # Build current time string
            s = now.strftime(time_fmt)
            blink = bool(blink_colon and (now.second % 2 == 1))

            # Prepare temperature text and left reservation budget
            # (We precompute widths to keep time stable)
            try:
                hh, mm = s.split(":")
            except ValueError:
                hh, mm = s[:2], s[-2:]
            w_h, h = textsize(hh, font=time_font)
            w_m, _ = textsize(mm, font=time_font)
            w_time = w_h + 1 + 1 + 1 + w_m  # gap=1, colon_w=1, gap=1
            left_alloc_max = max(0, device.width - w_time)

            temp_c = get_cpu_temp_c()
            temp_raw = "--" if temp_c is None else f"{int(round(max(-99, min(199, temp_c))))}"
            w_nn, _  = small35_text_size(temp_raw)
            w_nnC, _ = small35_text_size(temp_raw + ("C" if show_unit_c else ""))

            temp_txt = None
            left_reserved = 0
            if _env_bool("LED_DRAW_TEMP", 1) and left_alloc_max >= 3:
                if show_unit_c and w_nnC <= left_alloc_max:
                    temp_txt = temp_raw + "C"
                elif w_nn <= left_alloc_max:
                    temp_txt = temp_raw
                if temp_txt:
                    left_reserved = min(left_alloc_max, small35_text_size(temp_txt)[0])

            # Minute-change swipe (when minute changed since last render)
            if minute_swipe_en and (last_rendered_minute is None or now.minute != last_rendered_minute):
                # Run swipe with the NEW minute value
                minute_swipe(device, s, time_font, blink=False,
                             left_reserved=left_reserved, colon_vgap=colon_vgap,
                             temp_txt=temp_txt, swipe_px=minute_swipe_px, frame_delay=minute_swipe_dt)
                last_rendered_minute = now.minute
                # After swipe, draw one static frame this iteration (fall-through)

            # Normal frame
            with canvas(device) as draw:
                # Temperature widget (left)
                if temp_txt:
                    y0 = (device.height - 5) // 2
                    draw_small35(draw, 0, y0, temp_txt, spacing=1)

                # Time (right)
                draw_time_with_custom_colon(draw, device, s, time_font, blink=blink,
                                            left_reserved=left_reserved, gap=1,
                                            colon_w=1, colon_vgap=colon_vgap, time_offset=0)

                # Seconds bar at the bottom row
                if seconds_bar:
                    draw_seconds_bar(draw, now, device.width, y=device.height - 1, dotted=seconds_bar_dots)

            time.sleep(0.2)
    finally:
        device.clear()

# ------------------ Entry ------------------
if __name__ == "__main__":
    main()

"""
ENV cheatsheet (systemd unit [Service] -> Environment=...):

# Time & fonts
LED_TIME_FMT=%H:%M
LED_FONT=1                # 1=TINY (narrow), 2=SINCLAIR (taller)
LED_BLINK_COLON=1
LED_COLON_VGAP=2          # vertical gap between colon dots (1..3)

# Temperature widget
LED_DRAW_TEMP=1
LED_TEMP_SHOW_C=1

# Date ticker (English ASCII)
LED_TICKER_EVERY=60       # seconds between scrolls
LED_TICKER_SPEED=0.07     # higher -> slower scroll
LED_TICKER_GAP=16         # blank space after text
LED_TICKER_WITH_YEAR=1
LED_TICKER_FONT=1         # 1=TINY, 2=SINCLAIR (affects ticker only)

# Auto brightness
LED_AUTO_DIM=1
LED_BRIGHTNESS_DAY=12     # 0..255
LED_BRIGHTNESS_NIGHT=3    # 0..255
LED_NIGHT_FROM=22:30
LED_NIGHT_TO=07:00        # can cross midnight

# Visual add-ons
LED_SECONDS_BAR=1
LED_SECONDS_BAR_DOTTED=0

LED_SPARKLE_ON_HOUR=1
LED_SPARKLE_DURATION=0.45
LED_SPARKLE_DENSITY=0.15
LED_SPARKLE_FPS=20

LED_MINUTE_SWIPE=1
LED_MINUTE_SWIPE_PX=8
LED_MINUTE_SWIPE_DELAY=0.03

# Hardware
LED_SPI_PORT=0
LED_SPI_DEVICE=0
LED_BUS_HZ=16000000
LED_CASCADED=4
LED_ORIENTATION=-90
LED_ROTATE=0
"""
