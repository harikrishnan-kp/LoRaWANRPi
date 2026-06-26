# LoRaWAN Raspberry Pi

A Python library for LoRaWAN communication on Raspberry Pi. Based on and adapted from [lmic-rpi-fox](https://github.com/fox-iot/lmic-rpi-fox). Supports OTAA and ABP activation methods and provides a simple Python API for sending uplinks and receiving downlinks.

# Supported transceivers
- [RFM95](http://www.hoperf.com/upload/rf/RFM95_96_97_98W.pdf)

## Setup 
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

## Build the Native Library

```bash
# Clone the repository 
$ git clone https://github.com/harikrishnan-kp/LoRaWANPi.git  

# Make the project 
$ make 
```
The native library is built as `lorawanpi/liblorawanpi.so`.

## Usage
### ABP
```python
from lorawanpi import LoRaWAN, RadioConfig

lora = LoRaWAN(radio=RadioConfig(use_leds=True))

lora.configure_abp(
    devaddr="AB0096CD",
    nwkskey="1A2B80150C4ED6DADA2B2CFD822C6378",
    appskey="12345678972908DA7A6C09771181A21C",
)

result = lora.send(b"\x01\x38", port=1)

print(result.ok)
```
### OTA
```python
from lorawanpi import LoRaWAN, RadioConfig

lora = LoRaWAN(radio=RadioConfig(use_leds=True))

lora.configure_otaa(
    deveui="0000000000000000",
    appeui="0000000000000000",
    appkey="00000000000000000000000000000000",
)

result = lora.send(b"temperature=25", port=1)

print(result.ack)
```

## Examples

C++ and Python examples are available at : [examples](examples)

## License

Content is licensed under the MIT License. See [License File](LICENSE) for more information.
