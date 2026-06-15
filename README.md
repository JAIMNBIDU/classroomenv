# ClassroomEnv

A reproducible Kali Linux training environment for workshops, study groups, security clubs, and bootcamps. Run the script to set up tools on an existing Kali machine, or use the Docker images for a frozen, identical environment with no VM required.

Two ways to use it:

> **Script (`classroomenv.py`)** — run it on a Kali VM and install only the tools a session needs, grouped into domain profiles. Standardizes the toolset across a room of machines.
> **Docker images** — prebuilt, CLI-only images per profile. An image built on a given day is frozen forever, so everyone who pulls it gets byte-for-byte identical tools. This is the reproducible part.

---

## Why this exists

I was running an informal cybersecurity session over Discord. Before any teaching could happen, I asked everyone to set up a Kali VM — and the setup ate the session alive.

People were on different hypervisors (VMware and VirtualBox), different Kali releases, and some already had Kali installed with their own mix of tool versions. Tools were missing on some machines, present-but-different on others. Instead of teaching, I was debugging seven people's operating systems in parallel.

I reached for [PimpMyKali by Dewalt](https://github.com/Dewalt-arch/pimpmykali), which I'd used before and which is excellent at fixing a broken Kali. But for a *beginner session* it was the wrong fit: it took a long time, and it pulled in a lot of tooling the tutorial didn't call for — things like Ghidra and CrackMapExec, which are great tools but well past where a first session should start. New people don't need a reverse-engineering suite on day one; they need the handful of tools the lesson actually uses, installed the same way on every machine.

So I built ClassroomEnv. You run it after a Kali install (fresh or existing), and you install **only the profile the session needs** — `web`, `osint`, `ad`, and so on. A beginner web session gets web tools and nothing else. The advanced material stays in its own profile, opt-in, for when the group is ready for it.

The standardization philosophy is borrowed from PimpMyKali; the scope is deliberately narrower and session-oriented.

---

## What it does

- Installs predefined, domain-specific tool profiles — you pick what you need
- Verifies installed tools against a minimum-version floor
- Runs a system health check before installing anything
- Bootstraps a fresh Kali VM (system upgrade, VM guest tools, core tooling)
- Auto-detects and installs VMware / VirtualBox guest utilities
- Keeps an inventory of what's installed
- Ships [Docker images](#docker-images) per profile for a frozen, reproducible environment with no VM needed

## Requirements (script)

- **Kali Linux** (2025 or 2026 tested). Built specifically for Kali; other Debian-based distros are untested and some packages won't resolve.
- **Root** (the script drives `apt`).
- **Internet access** (everything is installed from repositories).
- **Go** — only needed for `kerbrute` in the `ad` profile. The script installs it during fresh setup, or warns if it's missing. Everything else installs via apt or pipx.

For Docker, you only need **Docker** — no Kali VM, no Go, nothing else.

---

## Installation (script)

```bash
git clone https://github.com/JAIMNBIDU/classroomenv.git
cd classroomenv
sudo python3 classroomenv.py
```

`sudo python3 classroomenv.py` launches the interactive menu and works regardless of how the file was cloned. The included `.gitattributes` guarantees Unix line endings on checkout, so the shebang works even if you cloned on Windows.

---

## Usage (script)

### Interactive menu (recommended)

```bash
sudo python3 classroomenv.py
```

Fresh-VM setup, profile installation, requirement validation, verification, inventory, and system updates.

### Command line

| Command | What it does |
|---|---|
| `sudo python3 classroomenv.py install <profile>` | Install a profile |
| `sudo python3 classroomenv.py install <profile> --no-gui` | Install a profile, skipping GUI tools |
| `sudo python3 classroomenv.py verify <profile>` | Verify a profile against version floors |
| `sudo python3 classroomenv.py doctor` | System health check |
| `sudo python3 classroomenv.py inventory` | List installed tools and versions |
| `sudo python3 classroomenv.py update` | `apt upgrade` + re-verify installed profiles |
| `sudo python3 classroomenv.py fresh` | Full new-VM bootstrap |
| `sudo python3 classroomenv.py list` | List all available profiles |

---

## Profiles

Each profile installs the `core` profile first as a dependency, so the essentials are always present.

| Profile | Focus | Tools |
|---|---|---|
| `core` | Essentials | nmap, git, curl, wget, python3, pip, tmux, jq, netcat, vim, net-tools, iputils-ping, whois, dnsutils, traceroute, golang |
| `web` | Web app testing | ffuf, gobuster, feroxbuster, burpsuite, seclists, httpx, nikto, sqlmap, wpscan, whatweb, nuclei, dirsearch, zaproxy |
| `osint` | Recon & OSINT | amass, subfinder, theHarvester, dnsx, maltego, recon-ng, shodan, exiftool, spiderfoot |
| `ad` | Active Directory | impacket, netexec, bloodhound, kerbrute, enum4linux-ng, ldapdomaindump, responder, evil-winrm |
| `wireless` | WiFi auditing | aircrack-ng, hcxdumptool, hashcat, hcxtools, wifite, reaver, bettercap |
| `exploitation` | Exploitation & cracking | metasploit-framework, exploitdb, john, hydra, crackmapexec |
| `extras` | Reverse engineering & forensics | ghidra, radare2, binwalk, volatility3, gdb, strace, ltrace |
| `full` | Everything | all of the above |

The split is the point: a beginner web session installs `web` and gets web tools, not a reverse-engineering suite. The advanced material lives in `extras` and `exploitation`, opt-in.

---

## How tools are installed

The script routes each tool to the most reliable installer, so you don't get fragile source builds where a prebuilt package exists:

- **apt** — the default and preferred path. Prebuilt Kali packages, installed in seconds.
- **pipx** — for Python application tools (shodan, volatility3, ldapdomaindump). Each is installed into an isolated virtualenv with its binary on `PATH`. This avoids the `externally-managed-environment` (PEP 668) errors that `pip install` throws on modern Kali. The script also pins `setuptools<81` into each venv, because newer setuptools removed `pkg_resources`, which several of these tools still import.
- **go** — `kerbrute` only, built from source because it isn't reliably packaged. Pinned via Go modules.

### Tool naming notes

- **httpx** is invoked as `httpx-toolkit` on Kali. The bare name `httpx` belongs to an unrelated Python library, so Kali renames ProjectDiscovery's tool to avoid the clash.
- **shodan**, **volatility3** (`vol`), and **ldapdomaindump** are pipx-isolated: their command-line tools work, but their Python libraries are not importable system-wide (`import shodan` in your own script won't find them).

---

## Docker images

The script standardizes the *toolset* but pulls whatever versions Kali currently ships, so two machines set up weeks apart can differ. The Docker images solve that: an image built on a given day is frozen — base OS, libraries, every tool — and `docker pull` gives everyone the identical environment, on any host OS, with no Kali VM at all. The image itself is the reproducible artifact.

All images are **CLI-only**. The five GUI tools (burpsuite, zaproxy, maltego, bloodhound, ghidra) are excluded via the script's `--no-gui` flag, since a container has no display. X11-forwarded GUI support may come later.

### Image layout

| Image | Built from | Contents |
|---|---|---|
| `classroomenv:core` | `kalilinux/kali-rolling` | The 16 core tools. Base layer for every other image. |
| `classroomenv:web` | `classroomenv:core` | + web tools (minus burpsuite, zaproxy) |
| `classroomenv:osint` | `classroomenv:core` | + OSINT tools (minus maltego) |
| `classroomenv:ad` | `classroomenv:core` | + AD tools (minus bloodhound) |
| `classroomenv:wireless` | `classroomenv:core` | + wireless tools |
| `classroomenv:exploitation` | `classroomenv:core` | + exploitation tools |
| `classroomenv:extras` | `classroomenv:core` | + RE/forensics tools (minus ghidra) |
| `classroomenv:full` | `classroomenv:core` | every profile, GUI tools excluded |

Each profile image adds only its own tools on top of the shared `core` layer.

### Building

`classroomenv:core` must be built first — every other image is `FROM classroomenv:core`. From the **repo root**:

```bash
./docker/build-all.sh
```

Builds `core` first, then every profile, tagging each `classroomenv:<profile>`. To build only specific profiles (core is always built first):

```bash
./docker/build-all.sh web ad
```

Or build manually (on Windows PowerShell, run these individually since `build-all.sh` is bash):

```bash
docker build -f docker/Dockerfile.core -t classroomenv:core .
docker build -f docker/Dockerfile.web  -t classroomenv:web  .
```

> **Rebuilding after a change:** the script is copied into `classroomenv:core`, so any edit to `classroomenv.py` requires rebuilding `core` with `--no-cache` before the change reaches profile images:
> `docker build --no-cache -f docker/Dockerfile.core -t classroomenv:core .`

### Running

```bash
docker run -it --rm classroomenv:web
```

Drops you into a bash shell with the profile's tools on `PATH`. `--rm` deletes the container on exit; nothing persists unless you mount a volume.

---

## Typical workshop workflow

**For instructors**

1. Share the repository link before the session.
2. Have participants clone it (or pull the matching Docker image).
3. On fresh VMs, run **Fresh Kali Setup** from the menu.
4. Install the one profile the session needs (e.g. `web`).
5. Run `verify` to confirm everyone's on the same baseline before teaching.

**For participants (script)**

```bash
git clone https://github.com/JAIMNBIDU/classroomenv.git
cd classroomenv
sudo python3 classroomenv.py
```

**For participants (Docker, no VM)**

```bash
docker run -it --rm classroomenv:web
```

---

## Troubleshooting

**`'python3\r': No such file or directory`**

The script has Windows (CRLF) line endings, usually from being edited on Windows. Fix once: `sed -i 's/\r$//' classroomenv.py`, or just run it as `sudo python3 classroomenv.py` (which bypasses the shebang). The included `.gitattributes` prevents this for fresh clones.

**A tool is "command not found" after install**

Some Kali packages install under a different command name than expected — notably `httpx` runs as `httpx-toolkit`. Check the [tool naming notes](#tool-naming-notes).

**Docker build seems to skip everything (`CACHED`, finishes in seconds)**

Docker reused cached layers. After editing `classroomenv.py`, rebuild `core` with `--no-cache` so the change actually propagates.

**Wireless tools don't do anything**

`aircrack-ng`, `wifite`, `reaver`, `hcxdumptool` need real wireless hardware in monitor mode, which a container (and often a VM) can't provide. They install fine; they just can't capture without compatible hardware passed through.

---

## Contributing

Issues, pull requests, bug reports, and profile suggestions are welcome. The goal is to make training environments faster to deploy and easier to keep consistent across a room.

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and distribute.
