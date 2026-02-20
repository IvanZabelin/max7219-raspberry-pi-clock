# Часы на MAX7219 для Raspberry Pi

Проект часов для LED-матрицы 32x8 (MAX7219 + SPI) с отображением времени, температуры CPU, бегущей даты, автояркости и анимаций.

## Возможности

- Право-выравненное время `HH:MM` с кастомным мигающим двоеточием
- Температура CPU слева (`°C`)
- Бегущая строка даты (ASCII, англ.)
- Автояркость день/ночь по временному окну
- Индикатор секунд (прогресс-бар)
- Опциональные анимации: sparkles на каждом часе и swipe при смене минуты
- Гибкая настройка через переменные окружения

## Что нужно по железу

- Raspberry Pi (с включенным SPI)
- LED-матрица MAX7219 32x8 (4 каскада по 8x8)
- Подключение по SPI (по умолчанию `SPI0 CE0`)

## Требования по софту

- Python 3.10+
- `luma.led_matrix`

Установка зависимостей:

```bash
pip install -r requirements.txt
```

## Быстрый запуск

```bash
python3 led_clock.py
```

## Основные переменные окружения

### Время и текст

- `LED_TIME_FMT` (по умолчанию: `%H:%M`)
- `LED_FONT` (1 = TINY, 2 = SINCLAIR)
- `LED_BLINK_COLON` (0/1)
- `LED_COLON_VGAP` (по умолчанию: `2`)

### Виджет температуры

- `LED_DRAW_TEMP` (0/1)
- `LED_TEMP_SHOW_C` (0/1)

### Бегущая дата

- `LED_TICKER_EVERY` (сек, по умолчанию `60`)
- `LED_TICKER_SPEED` (по умолчанию `0.07`)
- `LED_TICKER_GAP` (по умолчанию `16`)
- `LED_TICKER_WITH_YEAR` (0/1)
- `LED_TICKER_FONT` (1/2)

### Яркость

- `LED_AUTO_DIM` (0/1)
- `LED_BRIGHTNESS_DAY` (0..255, по умолчанию `12`)
- `LED_BRIGHTNESS_NIGHT` (0..255, по умолчанию `3`)
- `LED_NIGHT_FROM` (по умолчанию `22:30`)
- `LED_NIGHT_TO` (по умолчанию `07:00`)

### Визуальные эффекты

- `LED_SECONDS_BAR` (0/1)
- `LED_SECONDS_BAR_DOTTED` (0/1)
- `LED_SPARKLE_ON_HOUR` (0/1)
- `LED_SPARKLE_DURATION` (по умолчанию `0.45`)
- `LED_SPARKLE_DENSITY` (по умолчанию `0.15`)
- `LED_SPARKLE_FPS` (по умолчанию `20`)
- `LED_MINUTE_SWIPE` (0/1)
- `LED_MINUTE_SWIPE_PX` (по умолчанию `8`)
- `LED_MINUTE_SWIPE_DELAY` (по умолчанию `0.03`)

### Параметры железа

- `LED_SPI_PORT` (по умолчанию `0`)
- `LED_SPI_DEVICE` (по умолчанию `0`)
- `LED_BUS_HZ` (по умолчанию `16000000`)
- `LED_CASCADED` (по умолчанию `4`)
- `LED_ORIENTATION` (по умолчанию `-90`)
- `LED_ROTATE` (по умолчанию `0`)

## Автозапуск через systemd

Файлы в репозитории:

- `deploy/systemd/led-clock.service`
- `deploy/systemd/led-clock.env.example`
- `scripts/install-systemd.sh`

Установка на Raspberry Pi:

```bash
chmod +x scripts/install-systemd.sh
./scripts/install-systemd.sh
```

Проверка сервиса:

```bash
sudo systemctl status led-clock.service
sudo journalctl -u led-clock.service -f
```

Конфигурация переменных хранится в `/etc/default/led-clock`.

## Примечания

- Скрипт корректно обрабатывает `SIGINT`/`SIGTERM` и очищает дисплей при завершении.
- Температура CPU читается из `/sys/class/thermal/thermal_zone0/temp`, при неудаче — через `vcgencmd`.

## Статус

Проект в разработке, интерфейс и значения по умолчанию ещё могут меняться.
