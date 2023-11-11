# klipper-gcode-loader

`virtual_sdcard` alternative providing ability to pause and cancel print during macro execution, run macros as prints
and reload macros without restart

## Installation

```
cd ~
git clone https://github.com/vertexbz/klipper-gcode-loader.git
cd ~/klipper/klippy/extras/
ln -s ~/klipper-gcode-loader/src gcode_loader
```

### Moonraker

To add the extension to the update manager you can use following config

```
[update_manager klipper_gcode_loader]
type: git_repo
path: ~/klipper-gcode-loader
origin: https://github.com/vertexbz/klipper-gcode-loader.git
primary_branch: master
is_system_service: False
```

### Klipper Configuration

To have `gcode_loader` working you need to define it **before** `virtual_sdcard`. It is important to load `gcode_loader`
so it can take `virtual_sdcard`s place, and to keep `virtual_sdcard` to satisfy moonraker.

```
[gcode_loader]

[virtual_sdcard]
path: /home/printer/gcode
```

### Additional configuration options

```
[gcode_loader]
# A comma separated list of macros to be executed without interruption
uninterrupted: T0, T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11
```

## G-Code commands

### `MACRO_RELOAD`

G-Code command `MACRO_RELOAD [VARIABLES=1] [NAME=<macro name>]` re-reads configuration files again and reloads
macros. By default, it also adds new variables, to disable this behavior add `VARIABLES=0` parameter, or to replace
current macro variables with those from file use `VARIABLES=2`. You can also restrict reload by macro/template name
using `NAME=...` parameter.

### `PRINT_FROM_MACRO`

With `PRINT_FROM_MACRO MACRO=NAME PARAMS...` you can run your custom macro as print, pause and cancel it.

```
[gcode_macro MAX_FLOW_CALIB]
gcode:
    {% if printer.gcode_loader is defined and not printer.gcode_loader.is_virtual %}
        PRINT_FROM_MACRO MACRO=MAX_FLOW_CALIB {rawparams}
    {% else %}
        PRINT_START ...
        G-CODE...
        PRINT_END
    {% endif %}
```

