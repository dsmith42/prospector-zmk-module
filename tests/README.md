# Reference config

The module cannot be built on its own — a ZMK module is only compiled when a
keyboard config pulls it in. `reference-config/` is the smallest config that
exercises this one, and CI builds it on every push and pull request.

```
reference-config/
├── west.yml                       ZMK only — see "How the module is supplied"
├── targets.yaml                   what CI builds; add entries here
├── ref.keymap                     binds every behaviour this module adds
└── boards/shields/ref_dongle/     a keyless split central for the display
```

## Adding a build target

Append to `targets.yaml`. No workflow changes are needed — the matrix is
generated from this file.

```yaml
- name: my-target          # appears in the check name; short and unique
  board: xiao_ble//zmk     # any ZMK board target
  shield: ref_dongle prospector_adapter
  cmake-args: -DCONFIG_PROSPECTOR_STATUS_SCREEN_DIAL=y   # optional
```

All five status screen layouts are built by default, so a change to shared code
— fonts, symbols, the status screen dispatch in `custom_status_screen.c` —
cannot break one layout while another still compiles. Those four files are easy
to forget: adding a layout means touching `Kconfig`, the shield `CMakeLists.txt`,
`custom_status_screen.c` and `include/fonts.h`, and only the first two are
discoverable from the directory structure.

## How the module is supplied

`west.yml` deliberately does **not** list `prospector-zmk-module`. CI passes the
checked-out module with `ZEPHYR_EXTRA_MODULES` instead.

This matters. If west fetched the module by branch, a pull request would be
validated against whatever that branch's tip happens to be — that is, against
its own base rather than against itself — and a broken pull request would go
green. Supplying the checkout directly is what makes the check meaningful.

The same reasoning is why this workflow is hand written rather than using ZMK's
`build-user-config.yml`: that workflow assumes west owns every dependency.

## What `ref.keymap` is for

It binds every behaviour the module adds — `&blk` at each length plus
`BLK_START` and `BLK_STOP`, and `&bri` in both directions. A behaviour that
stops resolving in devicetree then fails CI, which a widget-only build would
not catch.

Note the behaviours are declared in the **keymap**, not in the shield overlay.
Split peripherals compile the keymap without the display, so a binding declared
only in a dongle-side overlay fails to resolve on the halves with
`undefined node label`.

## Building it locally

Run this from an empty directory, not from the module checkout — `west init -l`
roots the workspace in the *parent* of the config directory, so initialising in
place would put it inside `tests/`.

```sh
MODULE=/path/to/prospector-zmk-module

mkdir -p ~/zmk-ws && cd ~/zmk-ws
cp -r "$MODULE/tests/reference-config" config
west init -l config
west update
west zephyr-export

west build -s zmk/app -b "xiao_ble//zmk" -- \
  -DZMK_CONFIG="$PWD/config" \
  -DZEPHYR_EXTRA_MODULES="$MODULE" \
  -DSHIELD="ref_dongle prospector_adapter" \
  -DCONFIG_PROSPECTOR_STATUS_SCREEN_DIAL=y
```
