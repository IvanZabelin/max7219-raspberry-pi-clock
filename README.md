# MAX7219 Raspberry Pi Clock

Русская версия: [README.ru.md](README.ru.md)


32x8 LED-matrix clock for Raspberry Pi (MAX7219 + SPI) with CPU temperature, date ticker, auto-brightness and lightweight animations.

## Features

- Right-aligned `HH:MM` clock with custom blinking colon
- CPU temperature widget (`°C`) on the left
- English ASCII date ticker (scrolling line)
- Day/night auto brightness by time window
- Seconds progress bar
- Optional hour sparkle + minute swipe animations
- Runtime configuration via environment variables

## Hardware

- Raspberry Pi (with SPI enabled)
- MAX7219 32x8 LED matrix (4 cascaded 8x8 blocks)
- SPI wiring (default `SPI0 CE0`)

## Software requirements

- Python 3.10+
- `luma.led_matrix`

Install deps:

```bash
pip install -r requirements.txt
```

## Quick start

```bash
python3 led_clock.py
```

## Main environment variables

### Time and text

- `LED_TIME_FMT` (default: `%H:%M`)
- `LED_FONT` (1 = TINY, 2 = SINCLAIR)
- `LED_BLINK_COLON` (0/1)
- `LED_COLON_VGAP` (default: `2`)

### Temperature widget

- `LED_DRAW_TEMP` (0/1)
- `LED_TEMP_SHOW_C` (0/1)

### Date ticker

- `LED_TICKER_EVERY` (sec, default `60`)
- `LED_TICKER_SPEED` (default `0.07`)
- `LED_TICKER_GAP` (default `16`)
- `LED_TICKER_WITH_YEAR` (0/1)
- `LED_TICKER_FONT` (1/2)

### Brightness

- `LED_AUTO_DIM` (0/1)
- `LED_BRIGHTNESS_DAY` (0..255, default `12`)
- `LED_BRIGHTNESS_NIGHT` (0..255, default `3`)
- `LED_NIGHT_FROM` (default `22:30`)
- `LED_NIGHT_TO` (default `07:00`)

### Visuals

- `LED_SECONDS_BAR` (0/1)
- `LED_SECONDS_BAR_DOTTED` (0/1)
- `LED_SPARKLE_ON_HOUR` (0/1)
- `LED_SPARKLE_DURATION` (default `0.45`)
- `LED_SPARKLE_DENSITY` (default `0.15`)
- `LED_SPARKLE_FPS` (default `20`)
- `LED_MINUTE_SWIPE` (0/1)
- `LED_MINUTE_SWIPE_PX` (default `8`)
- `LED_MINUTE_SWIPE_DELAY` (default `0.03`)

### Hardware

- `LED_SPI_PORT` (default `0`)
- `LED_SPI_DEVICE` (default `0`)
- `LED_BUS_HZ` (default `16000000`)
- `LED_CASCADED` (default `4`)
- `LED_ORIENTATION` (default `-90`)
- `LED_ROTATE` (default `0`)

## Autostart with systemd

Files in repo:

- `deploy/systemd/led-clock.service`
- `deploy/systemd/led-clock.env.example`
- `scripts/install-systemd.sh`

Install on Raspberry Pi:

```bash
chmod +x scripts/install-systemd.sh
./scripts/install-systemd.sh
```

Service checks:

```bash
sudo systemctl status led-clock.service
sudo journalctl -u led-clock.service -f
```

Environment config is stored in `/etc/default/led-clock`.

## Notes

- The script handles `SIGINT`/`SIGTERM` and clears display on shutdown.
- CPU temp reads from `/sys/class/thermal/thermal_zone0/temp`, then falls back to `vcgencmd`.

## Project status

Work in progress. Interface and defaults may still change.
