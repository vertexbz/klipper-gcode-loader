# klipper-gcode-loader

`virtual_sdcard` alternative providing ability to pause and cancel print
during macro execution (you still have to wait for blocking commands though)
and adds error stack trace

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

To have `gcode_loader` working you need to replace `virtual_sdcard` configuration with `gcode_loader`, like on example
below

<table><tr>
<th>From</th><th>To</th>
</tr><tr>
<td valign="top">

```
[virtual_sdcard]
path: /home/printer/gcode
```

</td>
<td valign="top">

```
[gcode_loader]
path: /home/printer/gcode
```

</td>
</tr></table>

### Additional configuration options

```
[gcode_loader]
path: /home/printer/gcode
# Forces uninterrupted (shallow) execution of provided macros 
shallow: ['T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11']
```

## TODO

- [ ] recursive call protection

