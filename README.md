# Kobo e-ink dashboard

A small home dashboard for an old **Kobo Mini** (5" e-ink screen). A Raspberry Pi draws a
600×800 grayscale image in French (current weather, what the kids should wear, today's
calendar, top headlines) and the Kobo downloads and displays it on a schedule.

| Day | Night |
|---|---|
| ![Day preview](docs/preview-day.png) | ![Night preview](docs/preview-night.png) |

*(The previews use sample data; real headlines and events come from your own config.)*

## Table of contents

1. [How it works](#how-it-works)
2. [Project status](#project-status)
3. [Repository layout](#repository-layout)
4. [Example values used in this README](#example-values-used-in-this-readme)
5. [Server setup (Raspberry Pi + nginx)](#server-setup-raspberry-pi--nginx)
6. [Configuration](#configuration)
7. [Kobo setup](#kobo-setup)
8. [Keeping the Kobo awake](#keeping-the-kobo-awake)
9. [Troubleshooting](#troubleshooting)
10. [Roadmap](#roadmap)
11. [Credits](#credits)

## How it works

```
 Open-Meteo (weather)  ─┐
 News RSS feed         ─┼─►  Raspberry Pi                       Kobo Mini
 Calendar (.ics URL)   ─┘    server/dashboard.py                kobo/kobo_fetch.sh
                             writes output/dashboard.png  ──►    curl the PNG, show it with FBInk
                             (cron, every 30 min)                (loop, every 30 min)
                             nginx serves that one file
```

The Kobo stays "dumb": it only downloads one finished image and draws it. All the logic
(weather, clothing rules, layout, French text) lives on the Pi, which is much easier to
change than anything running on a 2012 e-reader.

**Screen layout (600×800):**

- **Top half, left:** big weather icon (sun, moon at night, clouds, rain, snow, fog,
  storm), the condition in French, the current temperature, and the day's min/max.
- **Top half, right:** up to 6 clothing icons for the children. Before noon they are for
  today (based on the feels-like temperature); from noon on they switch to tomorrow
  (based on the average of tomorrow's min and max).
- **Bottom half, left:** today's calendar events that are not over yet (all-day events
  first). Shows "Calendrier non configuré" if no calendar URL is set.
- **Bottom half, right:** the top headlines from a news RSS feed.

If a data source fails (no network, bad URL), that block shows a short French message
("Météo indisponible", "Nouvelles indisponibles", "Calendrier indisponible") instead of
breaking the whole image, and the error is printed to stderr.

## Project status

| Part | Status |
|---|---|
| Image generator (layout, icons, French text, day/night) | Working, tested with simulated data |
| Weather (Open-Meteo) | Implemented; not yet verified end-to-end on the Pi |
| News headlines | Implemented; the default Radio-Canada feed is listed as working by a third-party feed aggregator, not yet tested from the Pi |
| Calendar (.ics) | Implemented (recurring events, all-day events, time zones); tested only with synthetic calendars, not yet with a real Google/Outlook one |
| Kobo fetch + display script | Written; needs on-device testing |
| Staying awake / scheduled wake-up | Keep-awake test script provided; RTC wake untested |

## Repository layout

```
kobo_dashboard/
├── README.md
├── config.example.ini        template for your private config (copy to config.ini)
├── config.ini                YOUR config: not committed (.gitignore)
├── output/                   generated image and log: not committed (.gitignore)
│   └── dashboard.png
├── docs/                     preview images used in this README
├── server/                   runs on the Raspberry Pi
│   ├── dashboard.py          entry point: fetches data, lays out, writes the image
│   ├── config.py             loads config.ini
│   ├── calendar_events.py    reads an .ics URL, returns today's events
│   ├── draw_utils.py         fonts, text fitting and wrapping helpers
│   ├── icons.py              hand-drawn weather and clothing icons
│   └── requirements.txt      Python dependencies
└── kobo/                     runs on the Kobo
    ├── kobo_fetch.sh         download the image (and optionally display it, or loop)
    └── kobo_loop_test.sh     display a local image in a loop to test that the Kobo stays awake
```

## Example values used in this README

So that the commands can be copy-pasted as they are, the README assumes:

| What | Example value |
|---|---|
| Raspberry Pi address | `192.168.1.135` |
| Pi user | `pi` |
| Project folder on the Pi | `/home/pi/kobo_dashboard` |
| Location | Montréal (`45.5017`, `-73.5673`) |

Replace them with your own where they differ. Give the Pi a fixed IP (or a reserved DHCP
lease on your router) so its address never changes.

## Server setup (Raspberry Pi + nginx)

This assumes nginx is already installed and running on the Pi. The generated image always
stays inside the project folder (`output/dashboard.png`); nginx just serves that one file.

**1. Get the project onto the Pi** (replace the URL with your repository's):

```sh
cd /home/pi
git clone https://github.com/YOUR_USER/kobo_dashboard.git
cd kobo_dashboard
```

**2. Install dependencies.** Pillow and requests come from apt (reliable on Raspberry Pi
OS), the rest from pip inside a virtual environment that can see the apt packages:

```sh
sudo apt install python3-pil python3-requests fonts-dejavu-core
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r server/requirements.txt
```

**3. Create your config** from the template and edit it (see
[Configuration](#configuration)):

```sh
cp config.example.ini config.ini
nano config.ini
```

**4. Generate the image once** to check that everything works:

```sh
.venv/bin/python server/dashboard.py
```

This writes `/home/pi/kobo_dashboard/output/dashboard.png`. Open it (for example copy it
to your computer with `scp`) to check how it looks.

**5. Add a small nginx server block for the Kobo.** If your existing sites are HTTPS-only
(for example with Certbot and a redirect from port 80), don't put the `location` inside
those blocks: the Kobo would get redirected to HTTPS, and Certbot manages those blocks.
Add a separate `server { }` block instead, in the same file, **after** the existing ones
and at the same level (not inside another block):

```nginx
server {
    listen 80;
    server_name 192.168.1.135;

    # Only allow devices on the home network
    allow 192.168.1.0/24;
    deny all;

    location = /dashboard.png {
        alias /home/pi/kobo_dashboard/output/dashboard.png;
        add_header Cache-Control "no-store";
    }

    location / {
        return 404;
    }
}
```

Then check the configuration, reload, and test:

```sh
sudo nginx -t && sudo systemctl reload nginx
curl -I http://192.168.1.135/dashboard.png
```

You should get `HTTP/1.1 200 OK` with `Content-Type: image/png`.

- nginx picks the server block from the host name in the request, so requests to
  `192.168.1.135` land here, while your domain keeps going to its own HTTPS blocks.
- The `allow`/`deny` lines restrict the image to your home network (adjust
  `192.168.1.0/24` to your range). This matters if your domain is public, since the image
  shows your calendar events.
- `no-store` tells caches to always fetch the latest image, and `location / { return 404; }`
  keeps nginx from serving a default page on that address.
- A `location` directive outside a `server { }` block makes nginx fail with
  `"location" directive is not allowed here`.

If you get **403 Forbidden**, nginx (user `www-data`) can't traverse your home directory.
Allow it to pass through (without being able to list files):

```sh
chmod o+x /home/pi
```

**6. Regenerate the image every 30 minutes** with cron. This command adds the job without
opening an editor:

```sh
(crontab -l 2>/dev/null; echo '*/30 * * * * /home/pi/kobo_dashboard/.venv/bin/python /home/pi/kobo_dashboard/server/dashboard.py >> /home/pi/kobo_dashboard/output/dashboard.log 2>&1') | crontab -
```

Errors (unreachable weather service, bad calendar URL, …) end up in
`output/dashboard.log`. The image is written atomically, so nginx never serves a
half-written file.

## Configuration

All your personal values live in **`config.ini`** at the project root. It is listed in
`.gitignore`, so it never gets committed. The committed template is `config.example.ini`
(with Montréal as the example location). The file is read each time the image is
generated, so changes apply on the next run.

| Section | Key | Meaning |
|---|---|---|
| `[location]` | `latitude`, `longitude` | Where the weather is for |
| `[location]` | `timezone` | IANA time zone name, e.g. `America/Toronto` (also used to decide "today" and the noon switch) |
| `[news]` | `feed_url` | RSS feed of headlines. Empty shows "Nouvelles non configurées" |
| `[news]` | `headlines` | How many headlines to show (default 2) |
| `[calendar]` | `ics_url` | Private iCal (.ics) address. Empty shows "Calendrier non configuré" |

**Calendar URL:** in Google Calendar, use *Settings → your calendar → Integrate calendar →
"Secret address in iCal format"*. Anyone with that address can read your calendar, so treat
it like a password. This is exactly why it belongs in `config.ini` and never in the repo.
`webcal://` addresses are accepted.

**Other settings live in the code:**

| Setting | Where | Notes |
|---|---|---|
| Clothing rules | `clothes()` in `server/dashboard.py` | Coat under 20°, boots and tuque under 5°, mittens under 0°, snow pants under -10°, umbrella if rain or 50%+ chance, sun hat if 25°+ and sunny |
| Noon switch | `now.hour >= 12` in `draw_weather()` | When clothing icons switch to tomorrow |
| Icons | `server/icons.py` | Drawn with Pillow primitives in a 100×100 virtual box |
| Fonts | `FONT_CANDIDATES` in `server/draw_utils.py` | Tries a font next to the script, then Linux, Windows, macOS paths |

Weather data comes from [Open-Meteo](https://open-meteo.com/) (no API key). It returns a
standard WMO weather code and an `is_day` flag, which the script maps to an icon and a
French label.

## Kobo setup

Target device: **Kobo Mini (N705)**. The older Kobo Touch should work similarly.

**1. Update the firmware.** If the automatic update doesn't work on an old firmware, install
it manually: download the firmware package for your model from a Kobo firmware archive,
extract `KoboRoot.tgz`, copy it into the hidden `.kobo` folder on the device over USB, then
eject. It installs on reboot. Back up the `.kobo` folder first. (If you're on a very old
version, an intermediate firmware may be needed.)

**2. Install KOReader.** Follow the official instructions on the KOReader wiki:
<https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices>. KOReader provides
the launcher setup and the terminal emulator used below.

**3. Copy the scripts.** Create a folder on the device, for example `/mnt/onboard/dash/`,
and copy the contents of `kobo/` into it. The scripts keep the image in a `Dashboard/`
subfolder next to themselves.

**4. Test the display.** Put any 600×800 PNG at `dash/Dashboard/dashboard.png`, then run
from KOReader's terminal emulator:

```sh
sh /mnt/onboard/dash/kobo_loop_test.sh
```

See [Keeping the Kobo awake](#keeping-the-kobo-awake) for how to read the result.

**5. Connect to the Pi.** `kobo_fetch.sh` already points to
`http://192.168.1.135/dashboard.png`. If your Pi has another address, edit `URL` in the
script or set `DASH_URL`. Turn wifi on, then:

```sh
sh /mnt/onboard/dash/kobo_fetch.sh        # download only
sh /mnt/onboard/dash/kobo_fetch.sh show   # download and display
sh /mnt/onboard/dash/kobo_fetch.sh loop   # every 30 minutes
```

Plain `http://` is deliberate: the old Kobo firmware may struggle with modern HTTPS
certificates, and this only travels over your home network.

Notes: the scripts assume `fbink` is bundled with KOReader at
`/mnt/onboard/.adds/koreader/fbink`, and fall back to any `fbink` in the `PATH`. If neither
exists, download a standalone FBInk build for Kobo from its GitHub releases.

## Keeping the Kobo awake

By default a Kobo suspends after a few minutes and only wakes on a button press or USB
plug-in. For a dashboard that refreshes on its own, there are three options:

1. **Stay awake and plugged in (recommended first version).** A loop fetches, draws, and
   sleeps. The e-ink screen holds the image with no power, so the idle cost is small.
2. **Wake with the hardware clock (RTC).** Program the RTC alarm, suspend, wake, refresh,
   repeat, for weeks of battery life. Untested on the Kobo Mini's old kernel.
3. **Manual refresh.** Wake it by hand when you want fresh data.

**Validating option 1:** run `kobo/kobo_loop_test.sh` for 30 minutes or more with the Kobo on
its charger. It redraws the image at each interval, prints a counter and timestamp at the
bottom of the screen, and appends to `test_loop.log`.

- If the counter matches elapsed time divided by the interval, it never slept.
- In the log, a gap between two lines larger than the interval means the device suspended.

If it suspends while running under KOReader, disable KOReader's own auto-suspend in its
settings and test again. The final setup should stop KOReader and the stock Kobo software
while the loop runs, since they have their own sleep logic and will fight over the screen
and wifi.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'icalendar'` (or another module), e.g. on
  Windows:** dependencies aren't installed. Run `py -m pip install -r server\requirements.txt`
  (the `apt` commands are for the Pi only). `icalendar` is only needed when a calendar URL is
  set in `config.ini`.
- **`Fichier de configuration introuvable`:** you haven't created `config.ini`. Run
  `cp config.example.ini config.ini`.
- **`Configuration invalide` or `Fuseau horaire inconnu`:** check the keys and values in
  `config.ini` against `config.example.ini`. On Windows, time zones need
  `pip install tzdata` (included in `requirements.txt`).
- **Tiny text or broken accents (`d▯gag▯`):** the script couldn't find a TrueType font and
  fell back to Pillow's built-in bitmap font. It prints a warning. On Windows it should find
  Arial automatically; otherwise put `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` in `server/`.
- **"Météo indisponible", "Nouvelles indisponibles" or "Calendrier indisponible" on the
  image:** the Pi couldn't reach that source or couldn't read it. The exact error is in
  `output/dashboard.log` (or on screen if you ran the script by hand).
- **"Calendrier non configuré" / "Nouvelles non configurées":** `ics_url` / `feed_url` is
  empty in `config.ini`.
- **nginx returns 404:** `output/dashboard.png` doesn't exist yet (run the script once), or
  the `alias` path doesn't match your install folder.
- **nginx returns 403:** see the `chmod o+x /home/pi` step above.
- **`fbink introuvable` on the Kobo:** see the note in [Kobo setup](#kobo-setup).
- **Download fails on the Kobo:** check wifi, and test the address from the Kobo's terminal
  with `curl -I http://192.168.1.135/dashboard.png`.
- **KOReader redraws over the image:** expected while KOReader owns the screen. It matters
  only for testing; the final setup stops it.
- **The image is stale:** check the small clock in the bottom-right corner, then the cron
  job and `output/dashboard.log` on the Pi.

## Roadmap

- Test the calendar against a real Google Calendar / Outlook `.ics` feed.
- Run the Kobo loop without KOReader and the stock software, with wifi on/off handling.
- Try RTC wake for battery operation.
- Optional: swap the hand-drawn weather icons for an icon set (e.g. the Weather Icons font)
  if the current ones aren't polished enough.
- Other ideas: sunrise/sunset, school closure or snow alerts, a countdown to an event.

## Credits

- Weather data: [Open-Meteo](https://open-meteo.com/)
- E-ink drawing: [FBInk](https://github.com/NiLuJe/FBInk)
- Reader software and launcher: [KOReader](https://github.com/koreader/koreader)
- Calendar parsing: [icalendar](https://pypi.org/project/icalendar/) and
  [recurring-ical-events](https://pypi.org/project/recurring-ical-events/)
- Fonts: DejaVu Sans
