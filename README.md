# Clay Utilities

## Introduction

The `clayutil` package which contains a series of simple utilities is required by the `scripts` and my many other projects. I hope this project will make your work a little bit easier.

## Usage

1. Make sure the `clayutil` package is included in the `PYTHONPATH` (can be ignored if you open this project with an IDE)

2. Now you can write your scripts based on the `clayutil` package or execute the scripts directly in the `scripts` folder.

## Scripts

### daxuexi_end.py

Get the `end.jpg` of a specific episode of 青年大学习, and saved it to `$HOME/Downloads/daxuexi/`。

### fcitx5_dict_updater.py

Update Fcitx5 dictionaries at one click.

### gen_rsakey.py

Generate a pair of RSA keys.

### lottery.py

A simple lottery emulator.

Here is an example properties file for this script.

```properties
# Prize=Probability
SSR=0.05
SR=0.1
R=0.25
N=0.6
max=60
paid=0
```

#### Rules

1. The cumulative probability of all prizes must be 1.0.

2. For each draw, `paid` increases 1.

3. When `paid` hits `max`, `paid` returns to 0, and the first prize must be drawn.


