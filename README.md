# HackDeck
### Portable Security Research Platform

> ⚠️ **Work in Progress** — This project is actively under development. Hardware design, software modules, and documentation are all subject to change.

HackDeck is a custom-built portable security research and RF analysis platform inspired by the Flipper Zero, but built around a full x86 architecture running Kali Linux. The goal is a self-contained handheld device capable of SDR analysis, RFID research, signal capture, hardware debugging, and network analysis — all accessible through a unified custom UI.

---

## Software

The HackDeck UI is built with **Python 3 and PySide6 (Qt6)**, running as a fullscreen kiosk-style application on top of Kali Linux. The architecture uses a central shell with a modular system where each hardware tool is exposed as a self-contained module with its own UI panel.

### Stack
- **OS:** Kali Linux (x86)
- **UI Framework:** PySide6 / Qt6
- **Language:** Python 3 / C++
- **Development Platform:** macOS (migrating to Kali for final build)

### Modules Planned
| Module | Description | Status |
|--------|-------------|--------|
| RF / SDR | HackRF spectrum analysis, signal capture & replay | 🔲 Planned |
| RFID / NFC | Read, write, emulate & crack RFID/NFC tags | 🔲 Planned |
| Scope / Logic | Oscilloscope & logic analyzer interface | 🔲 Planned |
| Network | Scan, sniff & analyze network traffic | 🔲 Planned |
| System | Power management, device info & settings | 🔲 Planned |
| Logs | Captured data & session log viewer | 🔲 Planned |

---

## Hardware

### Main Compute
| Component | Details |
|-----------|---------|
| **SBC** | LattePanda MU (x86 Intel, Kali Linux) |
| **Coprocessor** | RP2040 or STM32 — physical controls & housekeeping |

### RF & Radio
| Component | Details |
|-----------|---------|
| **SDR** | HackRF One — housed in dedicated shielded/grounded RF bay |
| **RFID/NFC** | ChameleonUltra — dual frequency LF (125 kHz) & HF (13.56 MHz), read/write/emulate/crack |

### Test & Measurement
| Component | Details |
|-----------|---------|
| **Scope / Logic / AWG** | BitScope Micro (current) → Digilent Analog Discovery 3 (planned upgrade) |

### Power & Connectivity
| Component | Details |
|-----------|---------|
| **USB Hub** | TUSB8041 4-port USB 2.0 hub (custom PCB, in design) |
| **Power Management** | Custom PCB with internal battery management |

### Enclosure
- Custom designed enclosure — uConsole-inspired form factor
- Separate digital and RF compartments with shielding between bays
- Dual antenna ports on rear panel for ChameleonUltra LF and HF antennas
- Physical button controls routed through RP2040 coprocessor

---

## Project Status

| Area | Status |
|------|--------|
| UI Shell | ✅ Basic shell working — home dashboard, module launcher, screen navigation |
| Hardware Selection | ✅ Core components selected |
| Enclosure Design | 🔄 In progress (CAD) |
| USB Hub PCB | 🔄 In design |
| Power Management PCB | 🔲 Planned |
| RF Module | 🔲 Planned |
| RFID Module | 🔲 Planned |
| Scope Module | 🔲 Planned |
| Network Module | 🔲 Planned |
| Kali Integration | 🔲 Planned |

---

## Development Setup

### Requirements
- Python 3.11+
- PySide6


## Roadmap

- [ ] Finalize enclosure dimensions and component layout
- [ ] Complete USB hub PCB design
- [ ] Design power management PCB
- [ ] RP2040 coprocessor firmware for physical button input
- [ ] Hardware Abstraction Layer (HAL) for each device
- [ ] RF / SDR module (GNU Radio + HackRF)
- [ ] RFID module (ChameleonUltra Python API)
- [ ] Scope module (BitScope → AD3)
- [ ] Network module (Kali tool wrappers)
- [ ] Boot-to-kiosk configuration on Kali
- [ ] Migrate development to Kali for final integration

---

## Disclaimer

This project is intended for **authorized security research, education, and personal hardware development only**. Always ensure you have explicit permission before testing any systems or devices. The author is not responsible for misuse of this software or hardware.

---

*HackDeck is a personal hardware project — not affiliated with Flipper Zero, LattePanda, HackRF, or any other mentioned brand.*
