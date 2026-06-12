# ClassroomEnv

A reproducible Kali Linux training environment for workshops, study groups, university security clubs, bootcamps, and cybersecurity training sessions.

ClassroomEnv was built after repeatedly running into the same problem during initial training sessions.

A significant amount of time was being lost before any actual learning started. Students arrived with different Kali installations, different package versions, missing dependencies, broken repositories, missing guest additions, and inconsistent toolsets. Instead of teaching cybersecurity, time was spent troubleshooting operating systems.

The goal of this project is simple:

Standardize the environment so instructors can focus on teaching and students can focus on learning.
The project was also influenced by the standardization philosophy behind PimpMyKali and the work of DeWalt and TCM Security. While using PimpMyKali during PNPT preparation, it became clear how valuable environment consistency is. ClassroomEnv applies a similar idea specifically to training environments and classroom use cases.

---

## What it does

* Standardizes Kali Linux environments across multiple systems
* Installs predefined cybersecurity tool profiles
* Verifies installed tools and versions
* Performs environment health checks
* Automates fresh Kali VM setup tasks
* Installs VM guest utilities automatically
* Maintains installation inventory
* Reduces setup time before workshops and training sessions

---

## Supported Systems

* Kali Linux 2025
* Kali Linux 2026

Designed specifically for Kali Linux.

---

## Profiles

### Core

### Web

### OSINT

### Active Directory

### Wireless

### Exploitation

### Extras

### Full

---

## Installation

### Clone the repository

```bash
git clone <repository-url>
cd classroomenv
```

### Make the script executable

```bash
chmod +x classroomenv.py
```

### Launch ClassroomEnv

```bash
sudo ./classroomenv.py
```

or

```bash
sudo python3 classroomenv.py
```

---

## Recommended Usage

The interactive menu is the preferred way to use ClassroomEnv.

It provides:

* Requirement validation
* Profile selection
* Environment verification
* Inventory management
* Fresh system setup
* Update management

Launch the menu using:

```bash
sudo python3 classroomenv.py
```

For most users, trainers, clubs, and workshop participants, this is the recommended workflow.

---

## Command Line Usage

Install a profile:

```bash
sudo python3 classroomenv.py install web
```

Verify a profile:

```bash
sudo python3 classroomenv.py verify web
```

Run environment checks:

```bash
sudo python3 classroomenv.py doctor
```

Display installed tools and versions:

```bash
sudo python3 classroomenv.py inventory
```

Update the system and re-verify installed profiles:

```bash
sudo python3 classroomenv.py update
```

Prepare a fresh Kali installation:

```bash
sudo python3 classroomenv.py fresh
```

---

## Typical Workshop Workflow

### For Students

```bash
git clone <repository-url>
cd classroomenv
chmod +x classroomenv.py
sudo python3 classroomenv.py
```

Run the interactive setup and install the profile required for the session.

### For Instructors

1. Share the repository before the event
2. Have participants clone the repository
3. Run Fresh Kali Setup on newly installed VMs
4. Install the required profile
5. Verify the environment before beginning the session

---

## Why ClassroomEnv Exists

One of the largest sources of friction in beginner cybersecurity training is environment drift.

Students arrive with:

* Different Kali versions
* Different package states
* Missing tools
* Missing dependencies
* Different tool versions
* Broken repositories
* Missing VM integrations

The result is lost time and fragmented instruction.

ClassroomEnv attempts to reduce that overhead by providing a reproducible baseline environment that can be deployed consistently across multiple systems.

---

## Contributing

Issues, pull requests, bug reports, and profile suggestions are welcome.
The objective is to make cybersecurity training environments easier to deploy, easier to maintain, and easier to reproduce.

---

## License

MIT License

Free to use the way you like. 
