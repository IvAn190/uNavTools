# uNavTools

## Overview

uNavTools is a comprehensive toolset designed for the analysis and processing of GNSS signals using both Real-Time Kinematic (RTK) and Precise Point Positioning (PPP) techniques. This project consists of three main modules:

1. **PPP Module**: Applies corrections using a single receiver and improves accuracy through SSR files, providing orbit, bias, and clock corrections.
2. **RTK Module**: Utilizes corrections through two receivers, including a base station and a mobile receiver (rover). SSR corrections can also be applied for enhanced signal precision.
3. **Raw Data Acquisition Module**: Designed to acquire data from U-Blox devices and parse them into RINEX 3 format for subsequent processing with RTK or PPP.

These modules can be executed from the command line, providing a flexible and integrated interface with the entire library and its functionalities.

### Example Usage

A simple command to acquire raw data from the U-Blox receiver, parse it into RINEX format, and process it with the PPP module while plotting the results:

```sh
python .\Commands.py -getdata -ppp -t 20 -f 2 -port 'COM4' -plot
```

```sh
python .\Commands.py - -rtk -folder 'path/to/folder' -t 20 -f 2 -plot
```

```sh
python .\Commands.py -ppp -model 'FP9' -folder 'path/to/folder' -f 2 -t 20 -plot
```

## Requirements

The project has the following dependencies:

- Python 3.x
- numpy
- simplekml
- cssrlib

These dependencies are listed in the `requirements.txt` file.

## Installation

To install the required dependencies and set up the project, follow these steps:

1. **Clone the repository**:

```sh
git clone https://github.com/IvAn190/uNavTools.git
```

2. **Install the dependencies**:

Make sure you have pip installed. Then run:

```sh
python setup.py
```

This script will read the requirements.txt file and install each dependency using pip. Ensure requirements.txt is in the same directory as setup.py.

All code is available on my GitHub repository, which is open source and designed for easy and straightforward use.
