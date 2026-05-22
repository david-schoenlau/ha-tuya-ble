# Tuya BLE SDK User Guide

Source: https://developer.tuya.com/en/docs/iot-device-dev/tuya-ble-sdk-user-guide?id=K9h5zc4e5djd9

# BLE SDK Guide - TuyaOS

## Overview

This guide covers the Tuya BLE SDK, which encapsulates communication protocols with Tuya Smart mobile apps and implements event scheduling. Developers can interconnect devices with the Tuya app by calling provided APIs without managing protocol implementation details directly.

## Framework Architecture

The application framework consists of several layers:

- **Platform**: Chip platform and protocol stack maintained by manufacturers
- **Port**: Abstract interfaces implemented according to chip specifications
- **Tuya BLE SDK**: Core communication protocol and service interfaces
- **Application**: Custom device implementation using the SDK
- **SDK API**: BLE management, communication, and asynchronous message handling
- **SDK Config**: Macro-based configuration for different operational modes
- **Main Process**: Event engine requiring periodic calls or OS-based task execution
- **Message/Callback**: Status and data delivery through callbacks or messages

## OS Compatibility

The SDK supports both OS-based and non-OS platforms:

- **With OS**: SDK automatically creates tasks and message queues; applications register callbacks via `tuya_ble_callback_queue_register()`
- **Without OS**: Applications must call `tuya_ble_main_tasks_exec()` in main loop

## BLE Service Configuration

**Service UUID**: 0x1910
**Characteristics**:
- 0x2b10 (Notify)
- 0x2b11 (Write/Write without response)

**MTU Settings**: ATT MTU = 23, GATT MTU = 20

### Broadcast Data Format

Broadcast packets contain:
- **Physical connection identifier** (Type 0x01): Length 0x02, Data 0x16
- **Service UUID** (Type 0x02): Length 0x03, Data 0xA201
- **Service Data** (Type 0x16): Length 0x0C or 0x14, contains product identifier (PID or key, 8 or 16 bytes)

Scan response includes:
- **Complete Local Name** (Type 0x09): Length 0x03
- **Manufacturer Data** (Type 0xFF): Company ID 0x07D0, includes protocol version and encryption method

## Porting Interfaces

### Logging Functions

**TUYA_BLE_LOG**: Formatted output for debugging

**TUYA_BLE_HEXDUMP**: Hex value printing utility

### GAP Functions

**tuya_ble_gap_advertising_adv_data_update**: Updates broadcast packets

**tuya_ble_gap_advertising_scan_rsp_data_update**: Updates scan response data

**tuya_ble_gap_disconnect**: Terminates BLE connection

**tuya_ble_gap_addr_get**: Retrieves MAC address (supports public/random types)

**tuya_ble_gap_addr_set**: Updates device MAC address

### GATT Functions

**tuya_ble_gatt_send_data**: Sends data via BLE GATT (max 20 bytes, notification method)

### Timer Management

**tuya_ble_timer_create**: Creates timer with single-shot or recurring mode

**tuya_ble_timer_delete**: Removes timer

**tuya_ble_timer_start**: Starts timer

**tuya_ble_timer_restart**: Restarts with new timeout value

**tuya_ble_timer_stop**: Stops timer

### Delay Functions

**tuya_ble_device_delay_ms**: Millisecond-level delay (non-blocking for OS platforms)

**tuya_ble_device_delay_us**: Microsecond-level delay

### Device Management

**tuya_ble_device_reset**: Restarts device

**tuya_ble_device_enter_critical**: Enters critical section

**tuya_ble_device_exit_critical**: Exits critical section

### Random and Time Functions

**tuya_ble_rand_generator**: Generates random bytes

**tuya_ble_rtc_get_timestamp**: Retrieves Unix timestamp and timezone

**tuya_ble_rtc_set_timestamp**: Updates RTC with timestamp and timezone

### Non-Volatile Memory (NV)

**tuya_ble_nv_init**: Initializes NV space

**tuya_ble_nv_erase**: Erases specified memory range

**tuya_ble_nv_write**: Writes data to NV

**tuya_ble_nv_read**: Reads data from NV

**tuya_ble_nv_erase_async**: Asynchronous erase with callback

**tuya_ble_nv_write_async**: Asynchronous write with callback

**tuya_ble_nv_read_async**: Asynchronous read with callback

### UART Functions

**tuya_ble_common_uart_init**: Initializes UART for production testing

**tuya_ble_common_uart_send_data**: Sends data via UART

### OS Task Functions (OS platforms only)

**tuya_ble_os_task_create**: Creates task with priority and stack size

**tuya_ble_os_task_delete**: Removes task

**tuya_ble_os_task_suspend**: Pauses task execution

**tuya_ble_os_task_resume**: Resumes suspended task

### Message Queue Functions (OS platforms only)

**tuya_ble_os_msg_queue_create**: Creates message queue

**tuya_ble_os_msg_queue_delete**: Removes queue

**tuya_ble_os_msg_queue_peek**: Checks pending messages

**tuya_ble_os_msg_queue_send**: Sends message with timeout options

**tuya_ble_os_msg_queue_recv**: Receives message with timeout

### Cryptography Functions

**tuya_ble_aes128_ecb_encrypt/decrypt**: AES-128 ECB mode

**tuya_ble_aes128_cbc_encrypt/decrypt**: AES-128 CBC mode

**tuya_ble_md5_crypt**: MD5 checksum calculation

**tuya_ble_hmac_sha1_crypt**: HMAC-SHA1 (currently unused)

**tuya_ble_hmac_sha256_crypt**: HMAC-SHA256 (currently unused)

### Memory Management

**tuya_ble_port_malloc**: Allocates memory (when TUYA_BLE_USE_PLATFORM_MEMORY_HEAP=1)

**tuya_ble_port_free**: Deallocates memory

## Configuration Macros

### OS and Task Configuration

- **TUYA_BLE_USE_OS**: Enable OS support (1/0)
- **TUYA_BLE_SELF_BUILT_TASK**: SDK creates own tasks (requires OS, 1/0)
- **TUYA_BLE_TASK_PRIORITY**: Task priority level
- **TUYA_BLE_TASK_STACK_SIZE**: Task stack allocation in bytes

### Device Communication

- **TUYA_BLE_DEVICE_COMMUNICATION_ABILITY**: Bitfield for BLE, Mesh, Wi-Fi 2.4G/5G, Zigbee, NB-IoT support
- **TUYA_BLE_DEVICE_SHARED**: Device sharing capability (0/1)
- **TUYA_BLE_DEVICE_UNBIND_MODE**: Unbinding requirement for shared devices (1/0)

### Security and Authentication

- **TUYA_BLE_DEVICE_AUTH_SELF_MANAGEMENT**: App manages auth (1/0, recommended 1 for BLE-only)
- **TUYA_BLE_SECURE_CONNECTION_TYPE**: Encryption method (AUTH_KEY, ECC, or PASSTHROUGH)
- **TUYA_BLE_DEVICE_MAC_UPDATE**: Use auth MAC as device MAC (1/0)
- **TUYA_BLE_DEVICE_MAC_UPDATE_RESET**: Restart after MAC update (1/0)

### Memory Configuration

- **TUYA_BLE_USE_PLATFORM_MEMORY_HEAP**: Use platform malloc (1/0)
- **TUYA_BLE_GATT_SEND_DATA_QUEUE_SIZE**: Default 20
- **TUYA_BLE_DATA_MTU_MAX**: Currently 20 bytes only

### Logging Configuration

- **TUYA_BLE_LOG_ENABLE**: Enable SDK logging (1/0)
- **TUYA_BLE_LOG_COLORS_ENABLE**: Colored output (1/0)
- **TUYA_BLE_LOG_LEVEL**: ERROR/WARNING/INFO/DEBUG levels
- **TUYA_APP_LOG_ENABLE**: Enable application logging
- **TUYA_APP_LOG_COLORS_ENABLE**: App log colors
- **TUYA_APP_LOG_LEVEL**: Application log level

### NV Storage Configuration

- **TUYA_NV_ERASE_MIN_SIZE**: Minimum erasure unit (e.g., 4096 bytes)
- **TUYA_NV_WRITE_GRAN**: Write granularity (e.g., 4 bytes)
- **TUYA_NV_START_ADDR**: Initial NV address (e.g., 0x1000)
- **TUYA_NV_AREA_SIZE**: Total NV allocation (multiple of ERASE_MIN_SIZE)

### Version and Firmware

- **TUYA_BLE_APP_VERSION_STRING**: Application version (two-digit format)
- **TUYA_BLE_APP_BUILD_FIRMNAME_STRING**: Firmware name for production testing

### Custom Configuration

- **CUSTOMIZED_TUYA_BLE_CONFIG_FILE**: Custom configuration header
- **CUSTOMIZED_TUYA_BLE_APP_PRODUCT_TEST_HEADER_FILE**: Custom test header
- **CUSTOMIZED_TUYA_BLE_APP_UART_COMMON_HEADER_FILE**: Custom UART header

## SDK Initialization

### tuya_ble_sdk_init

Synchronous initialization function. Must be called before using SDK.

```c
tuya_ble_status_t tuya_ble_sdk_init(tuya_ble_device_param_t * param_data)
```

**Parameters**:
- `device_id_len`: Length of device UUID (16 or 20, compressed to 16)
- `device_id`: Unique device identifier assigned by Tuya
- `p_type`: Product ID type (PID or product key)
- `product_id`: Product identifier from Developer Platform
- `device_vid`: Virtual ID generated after binding
- `auth_key`: Authentication key (32 bytes) for authorization
- `login_key`: Login key for authenticated sessions
- `bound_flag`: Binding status (1=bound, 0=unbound)
- `firmware_version`: Firmware version (e.g., 0x010102 = v1.1.2)
- `hardware_version`: Hardware/PCBA version

### tuya_ble_sdk_init_async

Asynchronous initialization for platforms with async flash operations.

```c
void tuya_ble_sdk_init_async(tuya_ble_device_param_t * param_data,
                              tuya_ble_nv_async_callback_t callback)
```

Callback executes automatically upon initialization completion.

## Main Event Processing

### tuya_ble_main_tasks_exec

Non-OS platforms must call in main loop:

```c
void tuya_ble_main_tasks_exec(void)
```

Executes all scheduled events since last call.

## GATT Data Handling

### tuya_ble_gatt_receive_data

Called where BLE data is received from protocol stack:

```c
tuya_ble_status_t tuya_ble_gatt_receive_data(uint8_t* p_data, uint16_t len)
```

### tuya_ble_common_uart_receive_data

```c
tuya_ble_status_t tuya_ble_common_uart_receive_data(uint8_t *p_data, uint16_t len)
```

### tuya_ble_common_uart_send_full_instruction_received

```c
tuya_ble_status_t tuya_ble_common_uart_send_full_instruction_received(uint8_t *p_data, uint16_t len)
```

## Device Configuration Updates

### tuya_ble_device_update_product_id

```c
tuya_ble_status_t tuya_ble_device_update_product_id(tuya_ble_product_id_type_t type,
                                                     uint8_t len, uint8_t* p_buf)
```

### tuya_ble_device_update_login_key

```c
tuya_ble_status_t tuya_ble_device_update_login_key(uint8_t* p_buf, uint8_t len)
```

### tuya_ble_device_update_bound_state

```c
tuya_ble_status_t tuya_ble_device_update_bound_state(uint8_t state)
```

### tuya_ble_device_update_mcu_version

```c
tuya_ble_status_t tuya_ble_device_update_mcu_version(uint32_t mcu_firmware_version,
                                                      uint32_t mcu_hardware_version)
```

## Data Reporting

### tuya_ble_dp_data_report

```c
tuya_ble_status_t tuya_ble_dp_data_report(uint8_t *p_data, uint32_t len)
```

**DP Format**: Each point contains:
- Dp_id (1 byte): Point serial number
- Dp_type (1 byte): RAW(0), BOOL(1), VALUE(2), STRING(3), ENUM(4), BITMAP(5)
- Dp_len (1 byte): Data length (max 255)
- Dp_data (variable): Actual data

**Max data length**: TUYA_BLE_REPORT_MAX_DP_DATA_LEN (255+3 bytes)

### tuya_ble_dp_data_with_time_report

```c
tuya_ble_status_t tuya_ble_dp_data_with_time_report(uint32_t timestamp,
                                                     uint8_t *p_data, uint32_t len)
```

### tuya_ble_dp_data_with_time_ms_string_report

```c
tuya_ble_status_t tuya_ble_dp_data_with_time_ms_string_report(uint8_t *time_string,
                                                                uint8_t *p_data, uint32_t len)
```

13-byte millisecond-precision string time (e.g., "0000000123456").

### tuya_ble_dp_data_with_flag_report

```c
tuya_ble_status_t tuya_ble_dp_data_with_flag_report(uint16_t sn, tuya_ble_report_mode_t mode,
                                                     uint8_t *p_data, uint32_t len)
```

**Mode options**:
- REPORT_FOR_CLOUD_PANEL: Both panel and cloud
- REPORT_FOR_CLOUD: Cloud only
- REPORT_FOR_PANEL: Panel only
- REPORT_FOR_NONE: Neither

## Connection Status Management

### tuya_ble_connect_status_get

```c
tuya_ble_connect_status_t tuya_ble_connect_status_get(void)
```

**States**:
- UNBONDING_UNCONN (0): Unbound, disconnected
- UNBONDING_CONN: Unbound, connected
- BONDING_UNCONN: Bound, disconnected
- BONDING_CONN: Bound, connected
- BONDING_UNAUTH_CONN: Bound, connected, unauthed
- UNBONDING_UNAUTH_CONN: Unbound, connected, unauthed
- UNKNOW_STATUS: Unknown state

### tuya_ble_adv_data_connecting_request_set

```c
tuya_ble_status_t tuya_ble_adv_data_connecting_request_set(uint8_t on_off)
```

## Data Transmission

### tuya_ble_data_passthrough

```c
tuya_ble_status_t tuya_ble_data_passthrough(uint8_t *p_data, uint32_t len)
```

## DP Point Queries

### Event: TUYA_BLE_CB_EVT_DP_QUERY

```c
typedef struct {
    uint8_t *p_data;
    uint16_t data_len;
} tuya_ble_dp_query_data_t;
```

- `data_len=0`: Query all DP points
- `data_len>0`: Query specific DP IDs listed in p_data

## SDK Callback Events

### TUYA_BLE_CB_EVT_CONNECTE_STATUS
### TUYA_BLE_CB_EVT_DP_WRITE — App sends DP point control data
### TUYA_BLE_CB_EVT_DP_QUERY — App requests DP point values
### TUYA_BLE_CB_EVT_DP_DATA_REPORT_RESPONSE
### TUYA_BLE_CB_EVT_DP_DATA_WITH_TIME_REPORT_RESPONSE
### TUYA_BLE_CB_EVT_UNBOUND
### TUYA_BLE_CB_EVT_ANOMALY_UNBOUND
### TUYA_BLE_CB_EVT_DEVICE_RESET
### TUYA_BLE_CB_EVT_OTA_DATA
### TUYA_BLE_CB_EVT_NETWORK_INFO
### TUYA_BLE_CB_EVT_WIFI_SSID
### TUYA_BLE_CB_EVT_TIME_STAMP — Unix timestamp response (4-byte)
### TUYA_BLE_CB_EVT_TIME_NORMAL — Structured time
### TUYA_BLE_CB_EVT_DATA_PASSTHROUGH

## Directory Structure

- **app**: Tuya-managed applications (test, production, general modules)
- **doc**: Help documentation
- **extern_components**: Security algorithm extensions
- **port**: Platform-specific interface implementations
- **sdk**: Core SDK source code
- **tuya_ble_config.h**: Primary SDK configuration file
- **tuya_ble_sdk_version.h**: Version information

---
*Last updated August 24, 2021.*
