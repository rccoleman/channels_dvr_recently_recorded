# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Home Assistant custom integration (distributed via HACS) that exposes recent recordings from a [Channels DVR](https://getchannels.com/) server as a single sensor, formatted for the [Upcoming Media Card](https://github.com/custom-cards/upcoming-media-card). All code lives in `custom_components/channels_dvr_recently_recorded/`.

There is no build, lint, or test tooling in the repo. The only CI is `.github/workflows/validate.yaml` (HACS validation). To try changes, copy/symlink the component into a Home Assistant `custom_components/` dir and restart HA. When bumping a release, update `version` in `manifest.json`.

## Architecture

- `api.py` — `ChannelsDVR`: thin aiohttp client for the server (`/status`, `/dvr/files?all=true`, `/auth`). `request()` swallows all errors and returns `None`; `request_data()` converts that into `ConnectionFail`, which callers use as the failure signal.
- `__init__.py` — `async_setup_entry` builds a `ChannelsDVR`, calls `init_data()` (fetches server version), stores it in `hass.data[DOMAIN][entry_id]`, and forwards to the `sensor` platform.
- `config_flow.py` — UI-only setup (no YAML). Supports a manual `user` step and a Zeroconf (`_channels_dvr._tcp.local.`) → `confirm` step. Only a single config entry is allowed. `validate_input` hits `/auth` and stores the returned `verification` value in the entry data; the sensor uses it as its `unique_id` and device identifier.
- `sensor.py` — `ChannelsDVRRecentlyRecordedSensor` polls every 30s. `async_update` fetches all files, keeps non-deleted entries with a `JobID` and an `Airing.Raw` block (some recordings lack `Raw`), sorts by `startTime` descending, and truncates to `max`. Attributes are `{"data": [...]}` where the first element holds the card's `*_default` template strings and the rest are per-recording dicts (key names are dictated by the Upcoming Media Card). The state is `"Online"` or the `ConnectionFail` message.
- Poster images (when `dl_images` is on) are downloaded into `<hass config>/www<img_dir><name>/` and exposed as `/local...` URLs; files in that dir matching `p.+\.jpg` that are no longer in the current list are deleted on each update.

Constants (`CONF_*`, `DEFAULT_NAME`) are defined in `sensor.py` and imported by `config_flow.py`; `DOMAIN` is defined in `__init__.py`. Modules import each other via absolute `custom_components.channels_dvr_recently_recorded...` paths.

User-facing option docs live in `README.md`; config-flow UI strings are in `strings.json` and `translations/en.json` (keep both in sync).
