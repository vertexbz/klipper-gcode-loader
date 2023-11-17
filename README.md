# klipper-gcode-loader

This extension serves as an alternative to `virtual_sdcard`. With it, you can:

* pause/cancel print during custom print_start and other macros
* run macros as prints ([`PRINT_FROM_MACRO`](#printfrommacro))
* reload macros without the need for a firmware restart ([`MACRO_RELOAD`](#macroreload))
* include G-code from external gcode files ([`SDCARD_PRINT_FILE INCLUDE=1`](#sdcardprintfile-include1-filename))

## Installation

```bash
cd ~
git clone https://github.com/vertexbz/klipper-gcode-loader.git
cd ~/klipper/klippy/extras/
ln -s ~/klipper-gcode-loader/src gcode_loader
```

### Moonraker Integration

To use the update manager, modify your Moonraker configuration as follows:

```ini
[update_manager klipper_gcode_loader]
type : git_repo
path : ~/klipper-gcode-loader
origin : https://github.com/vertexbz/klipper-gcode-loader.git
primary_branch : master
is_system_service : False
```

### Klipper Configuration

For proper operation of `gcode_loader`, ensure it is defined **before** `virtual_sdcard`. Loading `gcode_loader` in this sequence allows it to take
the place of `virtual_sdcard` while keeping the latter in place to satisfy Moonraker requirements.

```ini
[gcode_loader]

[virtual_sdcard]
path : /home/printer/gcode
```

### Additional Configuration Options

```ini
[gcode_loader]
# A comma-separated list of macros to be executed without interruption
uninterrupted : T0, T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11
```

## G-Code Commands

### `MACRO_RELOAD`

The G-code command `MACRO_RELOAD [VARIABLES=1] [NAME=<macro name>]` re-reads configuration files and reloads macros. By default, it adds new
variables. To disable this behavior, use the `VARIABLES=0` parameter. Alternatively, to replace current macro variables with those from the file,
use `VARIABLES=2`. You can also restrict the reload by specifying the macro/template name with the `NAME=...` parameter.

### `PRINT_FROM_MACRO`

Execute your custom macro as a print, pause it, or cancel it using the `PRINT_FROM_MACRO MACRO=NAME PARAMS...` command.

```ini
[gcode_macro MAX_FLOW_CALIB]
gcode :
    {% if printer.gcode_loader is defined and not printer.gcode_loader.is_virtual %}
    PRINT_FROM_MACRO MACRO=MAX_FLOW_CALIB {rawparams}
    {% else %}
    PRINT_START ...
    G-CODE...
    PRINT_END
    {% endif %}
```

### `SDCARD_PRINT_FILE INCLUDE=1 FILENAME=...`

Additional `INCLUDE=1` parameter in the `SDCARD_PRINT_FILE` G-code command allows the inclusion of G-code from a specified file.