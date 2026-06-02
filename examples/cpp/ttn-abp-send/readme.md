## Build
```
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