#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <wiringPi.h>
#include <lmic.h>
#include <hal.h>
#include <local_hal.h>

#define DEFAULT_DATA_RATE 2
#define DEFAULT_TX_POWER 20
#define DEFAULT_NET_ID 1

#define RFM95_PIN_NSS 6
#define RFM95_PIN_RST 0
#define RFM95_PIN_D0 4
#define RFM95_PIN_D1 5
#define STATUS_PIN_LED 2
#define DATA_SENT_LED 3

extern "C" {

struct lmic_rpi_result {
    int status;
    int event;
    int txrx_flags;
    int ack;
    int nack;
    int rssi_dbm;
    float snr_db;
    int downlink_port;
    uint8_t downlink_len;
    uint8_t downlink[64];
};

}

lmic_pinmap pins = {
    RFM95_PIN_NSS,
    UNUSED_PIN,
    RFM95_PIN_RST,
    {RFM95_PIN_D0, RFM95_PIN_D1, UNUSED_PIN},
};

static volatile int send_complete = 0;
static volatile int join_complete = 0;
static volatile int join_failed = 0;
static int ota_joined = 0;
static int use_leds = 1;
static lmic_rpi_result current_result;
static uint8_t g_devEui[8];
static uint8_t g_appEui[8];
static uint8_t g_appKey[16];

void os_getArtEui(u1_t *buf) { memcpy(buf, g_appEui, sizeof(g_appEui)); }
void os_getDevEui(u1_t *buf) { memcpy(buf, g_devEui, sizeof(g_devEui)); }
void os_getDevKey(u1_t *buf) { memcpy(buf, g_appKey, sizeof(g_appKey)); }

static int hex_value(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int parse_hex(const char *hex, uint8_t *out, size_t out_len)
{
    if (hex == NULL || strlen(hex) != out_len * 2) return -1;

    for (size_t i = 0; i < out_len; ++i) {
        int high = hex_value(hex[i * 2]);
        int low = hex_value(hex[i * 2 + 1]);
        if (high < 0 || low < 0) return -1;
        out[i] = (uint8_t)((high << 4) | low);
    }
    return 0;
}

static u4_t msbf4_read(const uint8_t *data)
{
    return ((u4_t)data[0] << 24) | ((u4_t)data[1] << 16) | ((u4_t)data[2] << 8) | data[3];
}

static int elapsed_ms(const struct timespec *start)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (int)((now.tv_sec - start->tv_sec) * 1000 +
                 (now.tv_nsec - start->tv_nsec) / 1000000);
}

void onEvent(ev_t ev)
{
    current_result.event = ev;

    if (ev == EV_JOINED) {
        join_complete = 1;
    }
    if (ev == EV_JOIN_FAILED || ev == EV_REJOIN_FAILED) {
        join_failed = 1;
    }

    if (ev != EV_TXCOMPLETE) {
        return;
    }

    current_result.status = 0;
    current_result.txrx_flags = LMIC.txrxFlags;
    current_result.ack = (LMIC.txrxFlags & TXRX_ACK) ? 1 : 0;
    current_result.nack = (LMIC.txrxFlags & TXRX_NACK) ? 1 : 0;
    current_result.rssi_dbm = LMIC.rssi - 96;
    current_result.snr_db = LMIC.snr * 0.25f;
    current_result.downlink_port = LMIC.dataLen > 0 ? LMIC.frame[LMIC.dataBeg - 1] : 0;
    current_result.downlink_len = LMIC.dataLen;

    if (current_result.downlink_len > sizeof(current_result.downlink)) {
        current_result.downlink_len = sizeof(current_result.downlink);
    }
    for (uint8_t i = 0; i < current_result.downlink_len; ++i) {
        current_result.downlink[i] = LMIC.frame[LMIC.dataBeg + i];
    }

    if (use_leds) {
        digitalWrite(DATA_SENT_LED, LOW);
    }
    send_complete = 1;
}

static int wait_for_join(int timeout_ms)
{
    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);
    while (!join_complete && !join_failed) {
        if (timeout_ms > 0 && elapsed_ms(&start) >= timeout_ms) {
            return -1;
        }
        if (!os_runloop_once()) {
            usleep(1000);
        }
    }
    return join_complete ? 0 : -2;
}

static int wait_for_send(int timeout_ms)
{
    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);
    while (!send_complete) {
        if (timeout_ms > 0 && elapsed_ms(&start) >= timeout_ms) {
            return -1;
        }
        if (!os_runloop_once()) {
            usleep(1000);
        }
    }
    return 0;
}

extern "C" int lmic_rpi_send_abp(
    const char *devaddr_hex,
    const char *nwkskey_hex,
    const char *appskey_hex,
    const uint8_t *payload,
    uint8_t payload_len,
    uint8_t port,
    int confirmed,
    int leds_enabled,
    int timeout_ms,
    lmic_rpi_result *result)
{
    uint8_t devaddr[4];
    uint8_t nwkskey[16];
    uint8_t appskey[16];

    if (result == NULL) return -1;
    memset(&current_result, 0, sizeof(current_result));
    current_result.status = -1;
    *result = current_result;

    if (parse_hex(devaddr_hex, devaddr, sizeof(devaddr)) < 0 ||
        parse_hex(nwkskey_hex, nwkskey, sizeof(nwkskey)) < 0 ||
        parse_hex(appskey_hex, appskey, sizeof(appskey)) < 0) {
        current_result.status = -2;
        *result = current_result;
        return -2;
    }

    if (payload_len > 0 && payload == NULL) {
        current_result.status = -3;
        *result = current_result;
        return -3;
    }

    use_leds = leds_enabled ? 1 : 0;
    send_complete = 0;

    wiringPiSetup();
    os_init();
    LMIC_reset();
    LMIC_setSession(DEFAULT_NET_ID, msbf4_read(devaddr), nwkskey, appskey);

    for (int channel = 8; channel < 72; ++channel) {
        LMIC_disableChannel(channel);
    }

    LMIC_setAdrMode(0);
    LMIC_setLinkCheckMode(0);
    LMIC_disableTracking();
    LMIC_stopPingable();
    LMIC.dn2Dr = 8;
    LMIC_setDrTxpow(DEFAULT_DATA_RATE, DEFAULT_TX_POWER);

    if (use_leds) {
        pinMode(STATUS_PIN_LED, OUTPUT);
        pinMode(DATA_SENT_LED, OUTPUT);
        digitalWrite(STATUS_PIN_LED, HIGH);
        delay(100);
        digitalWrite(STATUS_PIN_LED, LOW);
    }

    int rc = LMIC_setTxData2(port, (xref2u1_t)payload, payload_len, confirmed ? 1 : 0);
    if (rc != 0) {
        current_result.status = rc;
        *result = current_result;
        return rc;
    }

    if (use_leds) {
        digitalWrite(DATA_SENT_LED, HIGH);
    }

    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);
    while (!send_complete) {
        if (timeout_ms > 0 && elapsed_ms(&start) >= timeout_ms) {
            current_result.status = -4;
            *result = current_result;
            return -4;
        }
        if (!os_runloop_once()) {
            usleep(1000);
        }
    }

    *result = current_result;
    return current_result.status;
}

extern "C" int lmic_rpi_send_otaa(
    const char *deveui_hex,
    const char *appeui_hex,
    const char *appkey_hex,
    const uint8_t *payload,
    uint8_t payload_len,
    uint8_t port,
    int confirmed,
    int leds_enabled,
    int timeout_ms,
    lmic_rpi_result *result)
{
    if (result == NULL) return -1;
    memset(&current_result, 0, sizeof(current_result));
    current_result.status = -1;
    *result = current_result;

    if (parse_hex(deveui_hex, g_devEui, sizeof(g_devEui)) < 0 ||
        parse_hex(appeui_hex, g_appEui, sizeof(g_appEui)) < 0 ||
        parse_hex(appkey_hex, g_appKey, sizeof(g_appKey)) < 0) {
        current_result.status = -2;
        *result = current_result;
        return -2;
    }

    if (payload_len > 0 && payload == NULL) {
        current_result.status = -3;
        *result = current_result;
        return -3;
    }

    use_leds = leds_enabled ? 1 : 0;
    join_complete = 0;
    join_failed = 0;
    send_complete = 0;

    wiringPiSetup();
    os_init();
    LMIC_reset();

    for (int channel = 8; channel < 72; ++channel) {
        LMIC_disableChannel(channel);
    }

    LMIC_setAdrMode(0);
    LMIC_setLinkCheckMode(0);
    LMIC_disableTracking();
    LMIC_stopPingable();
    LMIC.dn2Dr = 8;
    LMIC_setDrTxpow(DEFAULT_DATA_RATE, DEFAULT_TX_POWER);

    if (use_leds) {
        pinMode(STATUS_PIN_LED, OUTPUT);
        pinMode(DATA_SENT_LED, OUTPUT);
        digitalWrite(STATUS_PIN_LED, HIGH);
        delay(100);
        digitalWrite(STATUS_PIN_LED, LOW);
    }

    if (!LMIC_startJoining()) {
        // no-op: already joined or joining state is active
    }

    if (wait_for_join(timeout_ms) != 0) {
        current_result.status = -4;
        *result = current_result;
        return -4;
    }

    int rc = LMIC_setTxData2(port, (xref2u1_t)payload, payload_len, confirmed ? 1 : 0);
    if (rc != 0) {
        current_result.status = rc;
        *result = current_result;
        return rc;
    }

    if (use_leds) {
        digitalWrite(DATA_SENT_LED, HIGH);
    }

    if (wait_for_send(timeout_ms) != 0) {
        current_result.status = -5;
        *result = current_result;
        return -5;
    }

    ota_joined = 1;
    *result = current_result;
    return current_result.status;
}

extern "C" int lmic_rpi_join_otaa(
    const char *deveui_hex,
    const char *appeui_hex,
    const char *appkey_hex,
    int leds_enabled,
    int timeout_ms,
    lmic_rpi_result *result)
{
    if (result == NULL) return -1;
    memset(&current_result, 0, sizeof(current_result));
    current_result.status = -1;
    *result = current_result;

    if (parse_hex(deveui_hex, g_devEui, sizeof(g_devEui)) < 0 ||
        parse_hex(appeui_hex, g_appEui, sizeof(g_appEui)) < 0 ||
        parse_hex(appkey_hex, g_appKey, sizeof(g_appKey)) < 0) {
        current_result.status = -2;
        *result = current_result;
        return -2;
    }

    use_leds = leds_enabled ? 1 : 0;
    join_complete = 0;
    join_failed = 0;
    send_complete = 0;
    ota_joined = 0;

    wiringPiSetup();
    os_init();
    LMIC_reset();

    for (int channel = 8; channel < 72; ++channel) {
        LMIC_disableChannel(channel);
    }

    LMIC_setAdrMode(0);
    LMIC_setLinkCheckMode(0);
    LMIC_disableTracking();
    LMIC_stopPingable();
    LMIC.dn2Dr = 8;
    LMIC_setDrTxpow(DEFAULT_DATA_RATE, DEFAULT_TX_POWER);

    if (use_leds) {
        pinMode(STATUS_PIN_LED, OUTPUT);
        pinMode(DATA_SENT_LED, OUTPUT);
        digitalWrite(STATUS_PIN_LED, HIGH);
        delay(100);
        digitalWrite(STATUS_PIN_LED, LOW);
    }

    if (!LMIC_startJoining()) {
        // no-op: already joined or joining state is active
    }

    int rc = wait_for_join(timeout_ms);
    if (rc != 0) {
        if (rc == -1) {
            current_result.status = -4;
        } else {
            current_result.status = -2;
        }
        *result = current_result;
        return current_result.status;
    }

    ota_joined = 1;
    current_result.status = 0;
    *result = current_result;
    return 0;
}

extern "C" int lmic_rpi_send_otaa_after_join(
    const uint8_t *payload,
    uint8_t payload_len,
    uint8_t port,
    int confirmed,
    int leds_enabled,
    int timeout_ms,
    lmic_rpi_result *result)
{
    if (result == NULL) return -1;
    memset(&current_result, 0, sizeof(current_result));
    current_result.status = -1;
    *result = current_result;

    if (!ota_joined) {
        current_result.status = -6;
        *result = current_result;
        return -6;
    }

    if (payload_len > 0 && payload == NULL) {
        current_result.status = -3;
        *result = current_result;
        return -3;
    }

    use_leds = leds_enabled ? 1 : 0;
    send_complete = 0;

    LMIC_setAdrMode(0);
    LMIC_setLinkCheckMode(0);
    LMIC_disableTracking();
    LMIC_stopPingable();
    LMIC.dn2Dr = 8;
    LMIC_setDrTxpow(DEFAULT_DATA_RATE, DEFAULT_TX_POWER);

    if (use_leds) {
        pinMode(STATUS_PIN_LED, OUTPUT);
        pinMode(DATA_SENT_LED, OUTPUT);
        digitalWrite(STATUS_PIN_LED, HIGH);
    }

    int rc = LMIC_setTxData2(port, (xref2u1_t)payload, payload_len, confirmed ? 1 : 0);
    if (rc != 0) {
        current_result.status = rc;
        *result = current_result;
        return rc;
    }

    if (use_leds) {
        digitalWrite(DATA_SENT_LED, HIGH);
    }

    if (wait_for_send(timeout_ms) != 0) {
        current_result.status = -4;
        *result = current_result;
        return -4;
    }

    *result = current_result;
    return current_result.status;
}
