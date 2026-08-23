# Reference config

The module cannot be built on its own — a ZMK module is only compiled when a
keyboard config pulls it in. This is the smallest config that
exercises this one, and CI builds it on every push and pull request.

```
reference-config/
├── west.yml                       ZMK only — see "How the module is supplied"
├── build.yaml                     what CI builds; add entries here
├── ref.keymap                     binds every behaviour this module adds
└── boards/shields/ref_dongle/     a keyless split central for the display
```

## Adding a build target

Append to `build.yaml`, which is ZMK's standard build matrix format. No
workflow changes are needed.

```yaml
  - board: xiao_ble//zmk
    shield: ref_dongle prospector_adapter
    cmake-args: -DCONFIG_PROSPECTOR_STATUS_SCREEN_DIAL=y   # optional
    artifact-name: ref-dial
```

All five status screen layouts are built by default, so a change to shared code
— fonts, symbols, the status screen dispatch in `custom_status_screen.c` —
cannot break one layout while another still compiles. Those four files are easy
to forget: adding a layout means touching `Kconfig`, the shield `CMakeLists.txt`,
`custom_status_screen.c` and `include/fonts.h`, and only the first two are
discoverable from the directory structure.

## How the module is supplied

`west.yml` deliberately does **not** list `prospector-zmk-module`.

ZMK's `build-user-config.yml` detects that this repo is itself a module — it
looks for `zephyr/module.yml` at the root — and then passes the checkout as
`ZMK_EXTRA_MODULES`, building in an isolated workspace so the module is not
inside the workspace it is being added to.

This matters. If west fetched the module by branch, a pull request would be
validated against whatever that branch's tip happens to be — its own base
rather than itself — and a broken pull request would go green.

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
cp -r "$MODULE/reference-config" config
west init -l config
west update
west zephyr-export

west build -s zmk/app -b "xiao_ble//zmk" -- \
  -DZMK_CONFIG="$PWD/config" \
  -DZEPHYR_EXTRA_MODULES="$MODULE" \
  -DSHIELD="ref_dongle prospector_adapter" \
  -DCONFIG_PROSPECTOR_STATUS_SCREEN_DIAL=y
```

## Why this sits at the repository root

ZMK's `build-user-config.yml` creates its isolated workspace with a
non-recursive `mkdir "$base_dir/$config_path"`, so a nested `config_path` such
as `tests/reference-config` fails before anything is built. A single-level
directory is the only shape that works.
