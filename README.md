# LoRaWAN Raspberry Pi
A Python wrapper for utilizing the LMIC library to transmit data from a Raspberry Pi 4 using the RFM95 module.

This code is adapted and modified from [lmic-rpi-fox](https://github.com/fox-iot/lmic-rpi-fox). This library provides an interface between hardware and software, consisting of a LoRa chip [RFM95](http://www.hoperf.com/upload/rf/RFM95_96_97_98W.pdf) modified to operate at a frequency of 865 MHz and two indicator LEDs, one for indicating power on and the other for indicating data sending activity. 


## Setup 

- Format the SD card with [SD Memory Card Formatter](https://www.sdcard.org/downloads/formatter_4/) 
- Install the Raspbian operating system on the Raspberry Pi, which can be installed via Imager/Baleno Etcher
- Enable the SPI interface in preferences => Raspberrry pi configuration => interfaces 

## Hardware mapping 

The complete WiringPi pin mapping can be seen [here](assets/pin_map.png) 
| WiringPi Pin | Function        |
|--------------|-----------------|
| 0            | Reset           |
| 4            | DIO0            |
| 5            | DIO1            |
| 1            | DIO2 (Not used) |
| 12           | MOSI            |
| 13           | MISO            |
| 14           | SCK             |
| 6            | SS              |
| 2            | STATUS LED      |
| 3            | DATE SENT LED   |
| GND          | GND             |
| 3.3V         | +3.3V           |

## Install the WiringPi library 

The [WiringPi](https://github.com/WiringPi/WiringPi) library provides the Raspberry Pi GPIO interface. Follow the instructions in that repository or do the following.

```bash
# Clone the repository 
$ git clone https://github.com/WiringPi/WiringPi.git 

# Access the wiringPi folder 
$ cd wiringPi 

# Build the library
$ ./build 
```

## Compile [LoraWANPi](https://github.com/lucasmaziero/lmic-rpi-fox.git) 

```bash
# Clone the repository 
$ git clone https://github.com/harikrishnan-kp/LoRaWANPi.git 

# Access the C++ example folder
$ cd examples/cpp/ttn-abp-send 

# Make the project 
$ make 

# Running the program 
$ ./ttn-abp-send 
```

## How to run
```bash
# LED flag (0/1) can be used as an indication for device activity and data sending
./ttn-abp-send <DevAddr> <Nwkskey> <Appskey> <Rain_mm> <LED_FLAG>

# Example
./ttn-abp-send AB0096CD 1A2B80150C4ED6DADA2B2CFD822C6378 12345678972908DA7A6C09771181A21C 3.12 1
```

## Python wrapper

The repository also contains a Python wrapper that loads the LMIC code through a native shared library. Build it on the Raspberry Pi after WiringPi is installed:

```bash
cd python
make
```

Then run Python from the repository root with `PYTHONPATH=python`, or run from the `python` folder:

```python
from lorawanpi import send_rain_abp

result = send_rain_abp(
    devaddr="AB0096CD",
    nwkskey="1A2B80150C4ED6DADA2B2CFD822C6378",
    appskey="12345678972908DA7A6C09771181A21C",
    rain_mm=3.12,
    use_leds=True,
)

print(result)
```

For arbitrary payloads:

```python
from lorawanpi import send_abp

send_abp(
    devaddr="AB0096CD",
    nwkskey="1A2B80150C4ED6DADA2B2CFD822C6378",
    appskey="12345678972908DA7A6C09771181A21C",
    payload=b"\x01\x38",
    port=1,
)
```

The native library is built as `python/lorawanpi/liblorawanpi.so`.

## Examples

C++ and Python examples are available at : `examples/`

## License

Content is licensed under the MIT License. See [License File](LICENSE) for more information.
