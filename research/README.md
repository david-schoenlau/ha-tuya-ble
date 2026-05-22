# Research

Reference materials for building our Pi-as-Tuya-BLE-Gateway + HA integration.
Nothing here is original code — these are inputs we pull, analyze, and cite
from the actual implementation under `standalone/` and `custom_components/`.

## Layout

- `01-tuya-official/`   — Tuya developer-site docs (PDF/MD snapshots)
- `02-tuya-sdks/`       — Read-only SDK clones (C, Python)
- `03-community-impls/` — Existing HA / Python / ESP32 implementations
- `04-reverse-engineering/` — Protocol analyses, sniffer captures
- `05-bluez-pi-internals/`  — BlueZ + Bleak behavior on Linux/Pi
- `06-prior-art-pi-gateways/` — Anyone else built this
- `07-pair-handshake/`  — Deep dive on the pair flow (we need this most)

## Ground rules

- This dir is for **inputs** only. Code we write lives in `standalone/` and
  `custom_components/`.
- When citing a source in our code or docs, link the file under `research/`
  so anyone reading the repo can find the original.
- Keep size sane: snapshot Markdown/HTML, link to PDFs, only clone repos
  that are essential — don't pull every fork.

## Indexed sources (so far)

Populated by the research agents we spawned 2026-05-22.
