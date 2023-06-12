# Clay Utilities

## Introduction

The `clayutil` package which contains a series of simple utilities is required by the `scripts` and my many other
projects. I hope this project will make your work a little bit easier or inspire you to come up with a few on your own.

## Usage

1. Clone the repository and make sure the `clayutil` package is included in the `PYTHONPATH`.

   ```shell
   $ git clone https://github.com/bobbycyl/ClayUtilities.git
   $ cd ClayUtilities/
   $ export PYTHONPATH=$PYTHONPATH:.
   ```

2. Install the requirements.

   ```shell
   $ python3 -m pip install -r requirements.txt
   ```

3. Now you can execute the scripts by running `python3 scripts/<filename>.py`.

## Scripts

### daxuexi_end.py

Get the `end.jpg` of a specific episode of 青年大学习, and saved it to `$HOME/Downloads/daxuexi/`。

### fcitx5_dict_updater.py

Update Fcitx5 dictionaries at one click.

### gen_rsakey.py

Generate a pair of RSA keys.

### lottery.py

a simple lottery emulator

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
