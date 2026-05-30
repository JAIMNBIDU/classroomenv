#!/usr/bin/env python3
"""
classroomenv.py — Reproducible Kali Linux Training Environment
Version: 1.0.0
Author: You
License: MIT

Usage:
  sudo python3 classroomenv.py install core
  sudo python3 classroomenv.py install web
  sudo python3 classroomenv.py verify web
  sudo python3 classroomenv.py doctor
  sudo python3 classroomenv.py inventory
  sudo python3 classroomenv.py list
  sudo python3 classroomenv.py profile-info web
"""

import sys
import os
import subprocess
import shutil
import re
import json
import argparse
import logging
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
#  REQUIRES ROOT
# ─────────────────────────────────────────────

if os.geteuid() != 0:
    print("\033[91m[!] classroomenv requires root. Run with sudo.\033[0m")
    sys.exit(1)

# ─────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────

class C:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def ok(msg):    print(f"{C.GREEN}  ✓ {msg}{C.RESET}")
def fail(msg):  print(f"{C.RED}  ✗ {msg}{C.RESET}")
def warn(msg):  print(f"{C.YELLOW}  ⚠ {msg}{C.RESET}")
def info(msg):  print(f"{C.CYAN}  → {msg}{C.RESET}")
def head(msg):  print(f"\n{C.BOLD}{C.BLUE}{'─'*50}\n  {msg}\n{'─'*50}{C.RESET}")

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

LOG_FILE = "/var/log/classroomenv.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("classroomenv")


# ─────────────────────────────────────────────
#  TOOL REGISTRY
#  Each tool defines:
#    installer   : apt | pip | go | git
#    package     : what to install
#    bin         : binary name on PATH
#    version_cmd : command to get version string
#    version_re  : regex to extract semver-ish version
#    pinned      : expected version string
# ─────────────────────────────────────────────

REGISTRY = {
    # ── CORE ─────────────────────────────────
    "nmap": {
        "installer": "apt",
        "package": "nmap",
        "bin": "nmap",
        "version_cmd": ["nmap", "--version"],
        "version_re": r"Nmap version (\d+\.\d+[\w.]*)",
        "pinned": "7.94",
    },
    "git": {
        "installer": "apt",
        "package": "git",
        "bin": "git",
        "version_cmd": ["git", "--version"],
        "version_re": r"git version (\d+\.\d+\.\d+)",
        "pinned": "2.39",
    },
    "curl": {
        "installer": "apt",
        "package": "curl",
        "bin": "curl",
        "version_cmd": ["curl", "--version"],
        "version_re": r"curl (\d+\.\d+\.\d+)",
        "pinned": "7.88",
    },
    "wget": {
        "installer": "apt",
        "package": "wget",
        "bin": "wget",
        "version_cmd": ["wget", "--version"],
        "version_re": r"GNU Wget (\d+\.\d+[\.\d]*)",
        "pinned": "1.21",
    },
    "tmux": {
        "installer": "apt",
        "package": "tmux",
        "bin": "tmux",
        "version_cmd": ["tmux", "-V"],
        "version_re": r"tmux (\d+\.\d+)",
        "pinned": "3.3",
    },
    "jq": {
        "installer": "apt",
        "package": "jq",
        "bin": "jq",
        "version_cmd": ["jq", "--version"],
        "version_re": r"jq-(\d+\.\d+[\.\d]*)",
        "pinned": "1.6",
    },
    "netcat": {
        "installer": "apt",
        "package": "netcat-traditional",
        "bin": "nc",
        "version_cmd": ["nc", "-h"],
        "version_re": r"v(\d+\.\d+[\.\d]*)",
        "pinned": None,   # version string unreliable across variants
    },
    "vim": {
        "installer": "apt",
        "package": "vim",
        "bin": "vim",
        "version_cmd": ["vim", "--version"],
        "version_re": r"VIM - Vi IMproved (\d+\.\d+)",
        "pinned": "9.0",
    },
    "python3": {
        "installer": "apt",
        "package": "python3",
        "bin": "python3",
        "version_cmd": ["python3", "--version"],
        "version_re": r"Python (\d+\.\d+\.\d+)",
        "pinned": "3.11",
    },
    "pip": {
        "installer": "apt",
        "package": "python3-pip",
        "bin": "pip3",
        "version_cmd": ["pip3", "--version"],
        "version_re": r"pip (\d+\.\d+[\.\d]*)",
        "pinned": "23.0",
    },

    # ── WEB ──────────────────────────────────
    "ffuf": {
        "installer": "apt",
        "package": "ffuf",
        "bin": "ffuf",
        "version_cmd": ["ffuf", "-V"],
        "version_re": r"ffuf v?(\d+\.\d+[\.\d]*)",
        "pinned": "2.1.0",
    },
    "gobuster": {
        "installer": "apt",
        "package": "gobuster",
        "bin": "gobuster",
        "version_cmd": ["gobuster", "version"],
        "version_re": r"(\d+\.\d+\.\d+)",
        "pinned": "3.6.0",
    },
    "feroxbuster": {
        "installer": "apt",
        "package": "feroxbuster",
        "bin": "feroxbuster",
        "version_cmd": ["feroxbuster", "--version"],
        "version_re": r"(\d+\.\d+\.\d+)",
        "pinned": "2.10.0",
    },
    "burpsuite": {
        "installer": "apt",
        "package": "burpsuite",
        "bin": "burpsuite",
        "version_cmd": None,   # GUI tool — binary presence check only
        "version_re": None,
        "pinned": None,
    },
    "seclists": {
        "installer": "apt",
        "package": "seclists",
        "bin": None,           # not a binary — wordlist package
        "version_cmd": None,
        "version_re": None,
        "pinned": None,
        "verify_path": "/usr/share/seclists",
    },
    "httpx": {
        "installer": "go",
        "package": "github.com/projectdiscovery/httpx/cmd/httpx@v1.6.5",
        "bin": "httpx",
        "version_cmd": ["httpx", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)",
        "pinned": "1.6.5",
    },

    # ── OSINT ─────────────────────────────────
    "amass": {
        "installer": "apt",
        "package": "amass",
        "bin": "amass",
        "version_cmd": ["amass", "version"],
        "version_re": r"v?(\d+\.\d+[\.\d]*)",
        "pinned": "3.23.3",
    },
    "subfinder": {
        "installer": "go",
        "package": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.6.6",
        "bin": "subfinder",
        "version_cmd": ["subfinder", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)",
        "pinned": "2.6.6",
    },
    "theHarvester": {
        "installer": "apt",
        "package": "theharvester",
        "bin": "theHarvester",
        "version_cmd": ["theHarvester", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)",
        "pinned": None,
    },
    "dnsx": {
        "installer": "go",
        "package": "github.com/projectdiscovery/dnsx/cmd/dnsx@v1.2.0",
        "bin": "dnsx",
        "version_cmd": ["dnsx", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)",
        "pinned": "1.2.0",
    },

    # ── ACTIVE DIRECTORY ─────────────────────
    "impacket": {
        "installer": "apt",
        "package": "python3-impacket",
        "bin": None,
        "version_cmd": ["python3", "-c", "import impacket; print(impacket.__version__)"],
        "version_re": r"(\d+\.\d+[\.\d]*)",
        "pinned": "0.11.0",
    },
    "netexec": {
        "installer": "apt",
        "package": "netexec",
        "bin": "netexec",
        "version_cmd": ["netexec", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)",
        "pinned": None,
    },
    "bloodhound": {
        "installer": "apt",
        "package": "bloodhound",
        "bin": "bloodhound",
        "version_cmd": None,
        "version_re": None,
        "pinned": None,
    },
    "kerbrute": {
        "installer": "go",
        "package": "github.com/ropnop/kerbrute@v1.0.3",
        "bin": "kerbrute",
        "version_cmd": ["kerbrute", "version"],
        "version_re": r"v?(\d+\.\d+\.\d+)",
        "pinned": "1.0.3",
    },

    # ── WIRELESS ─────────────────────────────
    "aircrack-ng": {
        "installer": "apt",
        "package": "aircrack-ng",
        "bin": "aircrack-ng",
        "version_cmd": ["aircrack-ng", "--version"],
        "version_re": r"Aircrack-ng (\d+\.\d+[\.\d]*)",
        "pinned": "1.7",
    },
    "hcxdumptool": {
        "installer": "apt",
        "package": "hcxdumptool",
        "bin": "hcxdumptool",
        "version_cmd": ["hcxdumptool", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)",
        "pinned": None,
    },
    "hashcat": {
        "installer": "apt",
        "package": "hashcat",
        "bin": "hashcat",
        "version_cmd": ["hashcat", "--version"],
        "version_re": r"v?(\d+\.\d+[\.\d]*)",
        "pinned": "6.2.6",
    },

    # ── EXTRAS ───────────────────────────────
    "ghidra": {
        "installer": "apt",
        "package": "ghidra",
        "bin": "ghidra",
        "version_cmd": None,
        "version_re": None,
        "pinned": None,
    },
    "radare2": {
        "installer": "apt",
        "package": "radare2",
        "bin": "radare2",
        "version_cmd": ["radare2", "-version"],
        "version_re": r"radare2 (\d+\.\d+[\.\d]*)",
        "pinned": "5.8.8",
    },
    "binwalk": {
        "installer": "apt",
        "package": "binwalk",
        "bin": "binwalk",
        "version_cmd": ["binwalk", "--help"],
        "version_re": r"Binwalk v?(\d+\.\d+[\.\d]*)",
        "pinned": None,
    },
    "volatility3": {
        "installer": "pip",
        "package": "volatility3",
        "bin": "vol",
        "version_cmd": ["vol", "-h"],
        "version_re": r"Volatility (\d+\.\d+[\.\d]*)",
        "pinned": None,
    },
}


# ─────────────────────────────────────────────
#  PROFILES
#  depends_on is resolved before install
# ─────────────────────────────────────────────

PROFILES = {
    "core": {
        "description": "Essential tools every environment needs",
        "depends_on": [],
        "tools": [
            "nmap", "git", "curl", "wget", "python3",
            "pip", "tmux", "jq", "netcat", "vim",
        ],
    },
    "web": {
        "description": "Web application penetration testing",
        "depends_on": ["core"],
        "tools": [
            "ffuf", "gobuster", "feroxbuster",
            "burpsuite", "seclists", "httpx",
        ],
    },
    "osint": {
        "description": "Open-source intelligence gathering",
        "depends_on": ["core"],
        "tools": ["amass", "subfinder", "theHarvester", "dnsx"],
    },
    "ad": {
        "description": "Active Directory attacks and enumeration",
        "depends_on": ["core"],
        "tools": ["impacket", "netexec", "bloodhound", "kerbrute"],
    },
    "wireless": {
        "description": "Wireless network auditing",
        "depends_on": ["core"],
        "tools": ["aircrack-ng", "hcxdumptool", "hashcat"],
    },
    "extras": {
        "description": "Advanced tools — reverse engineering, forensics",
        "depends_on": ["core"],
        "tools": ["ghidra", "radare2", "binwalk", "volatility3"],
    },
    "full": {
        "description": "Everything — all profiles combined",
        "depends_on": ["core", "web", "osint", "ad", "wireless", "extras"],
        "tools": [],
    },
}


# ─────────────────────────────────────────────
#  STATE FILE
#  Tracks what classroomenv has installed
# ─────────────────────────────────────────────

STATE_FILE = "/var/lib/classroomenv/state.json"

def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return {"installed": {}, "profiles": []}
    return {"installed": {}, "profiles": []}

def _save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def _record_install(tool: str, version: Optional[str]):
    state = _load_state()
    state["installed"][tool] = {
        "version": version,
        "installed_at": datetime.now().isoformat(),
    }
    _save_state(state)

def _record_profile(profile: str):
    state = _load_state()
    if profile not in state["profiles"]:
        state["profiles"].append(profile)
    _save_state(state)


# ─────────────────────────────────────────────
#  SUBPROCESS HELPERS
# ─────────────────────────────────────────────

def _run(cmd: list, capture=True, timeout=300) -> tuple[int, str, str]:
    """Run a command. Returns (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            timeout=timeout,
            text=True,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout after {timeout}s"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)

def _apt_install(package: str) -> bool:
    info(f"apt install {package}")
    rc, _, err = _run(
        ["apt-get", "install", "-y", "--no-install-recommends", package],
        capture=False
    )
    if rc != 0:
        log.error(f"apt install failed: {package} — {err}")
        return False
    return True

def _pip_install(package: str) -> bool:
    info(f"pip install {package}")
    rc, _, err = _run(
        ["pip3", "install", "--quiet", package],
        capture=False
    )
    if rc != 0:
        log.error(f"pip install failed: {package} — {err}")
        return False
    return True

def _go_install(package: str) -> bool:
    if not shutil.which("go"):
        fail("Go is not installed. Cannot install Go-based tools.")
        return False
    info(f"go install {package}")
    env = os.environ.copy()
    if "GOPATH" not in env:
        env["GOPATH"] = "/root/go"
    env["GOBIN"] = "/usr/local/bin"
    try:
        result = subprocess.run(
            ["go", "install", package],
            env=env,
            timeout=300,
        )
        if result.returncode != 0:
            log.error(f"go install failed: {package}")
            return False
        return True
    except Exception as e:
        log.error(f"go install exception: {e}")
        return False


# ─────────────────────────────────────────────
#  VERSION EXTRACTION
# ─────────────────────────────────────────────

def _get_version(tool: str) -> Optional[str]:
    meta = REGISTRY.get(tool)
    if not meta:
        return None

    # wordlist/path-based tools
    if meta.get("verify_path"):
        return "present" if os.path.exists(meta["verify_path"]) else None

    # no version command defined
    if not meta.get("version_cmd"):
        bin_name = meta.get("bin")
        if bin_name:
            return "present" if shutil.which(bin_name) else None
        return None

    rc, stdout, stderr = _run(meta["version_cmd"])
    combined = stdout + stderr  # some tools write version to stderr

    if not meta.get("version_re"):
        return "present" if (rc == 0 or combined.strip()) else None

    match = re.search(meta["version_re"], combined)
    if match:
        return match.group(1)
    return None


def _version_matches(found: str, pinned: str) -> bool:
    """
    Loose prefix match.
    pinned=7.94 matches found=7.94.1 or 7.94SVN
    pinned=3.11 matches found=3.11.6
    """
    return found.startswith(pinned)


# ─────────────────────────────────────────────
#  PROFILE RESOLVER
# ─────────────────────────────────────────────

def _resolve_profiles(profile_name: str) -> list[str]:
    """Returns ordered list of profiles to process, dependencies first."""
    if profile_name not in PROFILES:
        fail(f"Unknown profile: {profile_name}")
        sys.exit(1)

    seen = []
    def _walk(name):
        for dep in PROFILES[name].get("depends_on", []):
            _walk(dep)
        if name not in seen:
            seen.append(name)
    _walk(profile_name)
    return seen

def _tools_for_profile(profile_name: str) -> list[str]:
    """All tools for a profile including dependency tools, deduplicated."""
    profiles = _resolve_profiles(profile_name)
    tools = []
    for p in profiles:
        for t in PROFILES[p]["tools"]:
            if t not in tools:
                tools.append(t)
    return tools


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────

def cmd_install(profile_name: str, verbose: bool = False):
    head(f"Installing profile: {profile_name}")
    tools = _tools_for_profile(profile_name)
    info(f"Resolving {len(tools)} tools from profile chain: {' → '.join(_resolve_profiles(profile_name))}")

    # apt update once before installing
    info("Running apt-get update...")
    _run(["apt-get", "update", "-qq"], capture=False)

    success, skipped, failed_tools = [], [], []

    for tool in tools:
        meta = REGISTRY.get(tool)
        if not meta:
            warn(f"{tool} — not in registry, skipping")
            skipped.append(tool)
            continue

        # already installed?
        existing = _get_version(tool)
        if existing:
            ok(f"{tool} already installed ({existing})")
            skipped.append(tool)
            continue

        installer = meta["installer"]
        pkg = meta["package"]

        if installer == "apt":
            result = _apt_install(pkg)
        elif installer == "pip":
            result = _pip_install(pkg)
        elif installer == "go":
            result = _go_install(pkg)
        else:
            warn(f"{tool} — unknown installer type '{installer}', skipping")
            skipped.append(tool)
            continue

        if result:
            version = _get_version(tool)
            ok(f"{tool} installed ({version or 'unknown version'})")
            _record_install(tool, version)
            success.append(tool)
            log.info(f"Installed {tool} v{version}")
        else:
            fail(f"{tool} — installation failed")
            failed_tools.append(tool)
            log.error(f"Failed to install {tool}")

    _record_profile(profile_name)

    print()
    head("Install Summary")
    ok(f"Installed:  {len(success)}")
    info(f"Skipped:    {len(skipped)}")
    if failed_tools:
        fail(f"Failed:     {len(failed_tools)} → {', '.join(failed_tools)}")
    else:
        ok("No failures")


def cmd_verify(profile_name: str):
    head(f"Verifying profile: {profile_name}")
    tools = _tools_for_profile(profile_name)

    passed, warned, failed_tools = [], [], []

    for tool in tools:
        meta = REGISTRY.get(tool)
        if not meta:
            warn(f"{tool:<20} not in registry")
            warned.append(tool)
            continue

        found = _get_version(tool)

        if found is None:
            fail(f"{tool:<20} NOT FOUND")
            failed_tools.append(tool)
            log.warning(f"Verify failed: {tool} not found")
            continue

        pinned = meta.get("pinned")

        if pinned is None:
            ok(f"{tool:<20} {found} (no pin defined)")
            passed.append(tool)
        elif _version_matches(found, pinned):
            ok(f"{tool:<20} {found}")
            passed.append(tool)
        else:
            fail(f"{tool:<20} VERSION MISMATCH")
            print(f"             Expected: {pinned}")
            print(f"             Found:    {found}")
            warned.append(tool)
            log.warning(f"Version mismatch: {tool} expected={pinned} found={found}")

    print()
    head("Verify Summary")
    ok(f"Passed:    {len(passed)}")
    if warned:
        warn(f"Warnings:  {len(warned)} → {', '.join(warned)}")
    if failed_tools:
        fail(f"Missing:   {len(failed_tools)} → {', '.join(failed_tools)}")


def cmd_doctor():
    head("System Health Check")
    issues = 0

    # OS check
    try:
        with open("/etc/os-release") as f:
            content = f.read()
        if "kali" in content.lower():
            version_match = re.search(r'VERSION_ID="?(\d{4}\.\d+)"?', content)
            ver = version_match.group(1) if version_match else "unknown"
            ok(f"Kali Linux detected (version {ver})")
        else:
            warn("Not running Kali Linux — some packages may be unavailable")
    except Exception:
        warn("Could not read /etc/os-release")

    # Internet
    rc, _, _ = _run(["curl", "-s", "--max-time", "5", "https://kali.org"], capture=True)
    if rc == 0:
        ok("Internet connectivity")
    else:
        fail("No internet connectivity")
        issues += 1

    # apt
    rc, _, err = _run(["apt-get", "check"])
    if rc == 0:
        ok("apt is functional")
    else:
        fail(f"apt check failed: {err.strip()}")
        issues += 1

    # Python3
    rc, out, _ = _run(["python3", "--version"])
    if rc == 0:
        ok(f"Python3: {out.strip()}")
    else:
        fail("python3 not found")
        issues += 1

    # pip3
    if shutil.which("pip3"):
        ok("pip3 available")
    else:
        warn("pip3 not found — pip-based tools will fail")

    # Go
    if shutil.which("go"):
        _, out, _ = _run(["go", "version"])
        ok(f"Go: {out.strip()}")
    else:
        warn("Go not installed — go-based tools will not install")
        warn("Install Go: apt-get install golang-go")

    # Git
    if shutil.which("git"):
        ok("git available")
    else:
        fail("git not found")
        issues += 1

    # Disk space
    stat = os.statvfs("/")
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    if free_gb >= 5:
        ok(f"Disk space: {free_gb:.1f} GB free")
    elif free_gb >= 2:
        warn(f"Disk space low: {free_gb:.1f} GB free (recommend 5GB+)")
    else:
        fail(f"Disk space critical: {free_gb:.1f} GB free")
        issues += 1

    # PATH
    path_dirs = os.environ.get("PATH", "").split(":")
    required_paths = ["/usr/bin", "/usr/local/bin", "/usr/sbin"]
    for p in required_paths:
        if p in path_dirs:
            ok(f"PATH contains {p}")
        else:
            warn(f"PATH missing {p}")

    # Log file
    ok(f"Log file: {LOG_FILE}")

    # State file
    if os.path.exists(STATE_FILE):
        ok(f"State file: {STATE_FILE}")
    else:
        info(f"No state file yet (created on first install)")

    print()
    if issues == 0:
        ok("System is ready for classroomenv")
    else:
        fail(f"{issues} critical issue(s) found — fix before installing profiles")


def cmd_inventory():
    head("Installed Tool Inventory")
    state = _load_state()

    installed_profiles = state.get("profiles", [])
    installed_tools = state.get("installed", {})

    if installed_profiles:
        info(f"Installed profiles: {', '.join(installed_profiles)}")
    else:
        info("No profiles installed yet")

    print()
    fmt = f"  {'Tool':<22} {'Pinned':<12} {'Found':<16} {'Status':<10} {'Profile'}"
    print(f"{C.BOLD}{fmt}{C.RESET}")
    print("  " + "─" * 80)

    # Show all tools across all installed profiles
    shown = set()
    all_tools = []
    for p in installed_profiles:
        for t in _tools_for_profile(p):
            if t not in shown:
                all_tools.append((t, p))
                shown.add(t)

    if not all_tools:
        info("No tools tracked. Run: classroomenv install <profile>")
        return

    for tool, profile in all_tools:
        meta = REGISTRY.get(tool, {})
        pinned = meta.get("pinned") or "—"
        found = _get_version(tool) or "not found"
        rec = installed_tools.get(tool, {})

        if found == "not found":
            status = f"{C.RED}MISSING{C.RESET}"
        elif pinned == "—":
            status = f"{C.GREEN}OK{C.RESET}"
        elif _version_matches(found, pinned):
            status = f"{C.GREEN}OK{C.RESET}"
        else:
            status = f"{C.YELLOW}MISMATCH{C.RESET}"

        print(f"  {tool:<22} {pinned:<12} {found:<16} {status:<20} {profile}")


def cmd_list():
    head("Available Profiles")
    for name, meta in PROFILES.items():
        deps = meta.get("depends_on", [])
        dep_str = f" (needs: {', '.join(deps)})" if deps else ""
        tool_count = len(meta["tools"]) if meta["tools"] else "inherits all"
        print(f"\n  {C.BOLD}{C.CYAN}{name}{C.RESET}")
        print(f"    {meta['description']}{dep_str}")
        print(f"    Tools: {tool_count}")


def cmd_profile_info(profile_name: str):
    if profile_name not in PROFILES:
        fail(f"Unknown profile: {profile_name}")
        sys.exit(1)

    meta = PROFILES[profile_name]
    head(f"Profile: {profile_name}")
    info(f"Description: {meta['description']}")

    deps = meta.get("depends_on", [])
    if deps:
        info(f"Depends on:  {', '.join(deps)}")

    resolved = _resolve_profiles(profile_name)
    if len(resolved) > 1:
        info(f"Install order: {' → '.join(resolved)}")

    all_tools = _tools_for_profile(profile_name)
    own_tools = meta["tools"]

    print(f"\n  {C.BOLD}Tools in this profile:{C.RESET}")
    for t in own_tools:
        m = REGISTRY.get(t, {})
        pin = m.get("pinned") or "unpinned"
        inst = m.get("installer", "?")
        print(f"    {t:<22} [{inst}]  pin: {pin}")

    inherited = [t for t in all_tools if t not in own_tools]
    if inherited:
        print(f"\n  {C.BOLD}Inherited from dependencies:{C.RESET}")
        for t in inherited:
            m = REGISTRY.get(t, {})
            pin = m.get("pinned") or "unpinned"
            print(f"    {t:<22} pin: {pin}")


# ─────────────────────────────────────────────
#  BANNER
# ─────────────────────────────────────────────

def _banner():
    print(f"""
{C.CYAN}{C.BOLD}
  ██████╗██╗      █████╗ ███████╗███████╗██████╗  ██████╗  ██████╗ ███╗   ███╗███████╗███╗   ██╗██╗   ██╗
 ██╔════╝██║     ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔═══██╗██╔═══██╗████╗ ████║██╔════╝████╗  ██║██║   ██║
 ██║     ██║     ███████║███████╗███████╗██████╔╝██║   ██║██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║██║   ██║
 ██║     ██║     ██╔══██║╚════██║╚════██║██╔══██╗██║   ██║██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║╚██╗ ██╔╝
 ╚██████╗███████╗██║  ██║███████║███████║██║  ██║╚██████╔╝╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║ ╚████╔╝
  ╚═════╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝  ╚═══╝
{C.RESET}
  {C.YELLOW}Reproducible Kali Linux Training Environment{C.RESET}  v1.0.0
  {C.BLUE}Log: {LOG_FILE}  |  State: {STATE_FILE}{C.RESET}
""")


# ─────────────────────────────────────────────
#  CLI ENTRY
# ─────────────────────────────────────────────

def main():
    _banner()

    parser = argparse.ArgumentParser(
        prog="classroomenv",
        description="Reproducible Kali Linux training environment manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  install <profile>     Install all tools in a profile
  verify <profile>      Verify installed versions against pins
  doctor                System health check
  inventory             Show all installed tools and versions
  list                  List available profiles
  profile-info <name>   Show profile details

Profiles:
  core     wireless     osint
  web      ad           extras     full

Examples:
  sudo python3 classroomenv.py install web
  sudo python3 classroomenv.py verify web
  sudo python3 classroomenv.py doctor
        """,
    )

    parser.add_argument("command", help="Command to run")
    parser.add_argument("target", nargs="?", help="Profile name (for install/verify/profile-info)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    cmd = args.command.lower()

    if cmd == "install":
        if not args.target:
            fail("install requires a profile name")
            info("Usage: classroomenv install <profile>")
            info("Run 'classroomenv list' to see available profiles")
            sys.exit(1)
        cmd_install(args.target, args.verbose)

    elif cmd == "verify":
        if not args.target:
            fail("verify requires a profile name")
            sys.exit(1)
        cmd_verify(args.target)

    elif cmd == "doctor":
        cmd_doctor()

    elif cmd == "inventory":
        cmd_inventory()

    elif cmd == "list":
        cmd_list()

    elif cmd in ("profile-info", "profileinfo", "profile_info"):
        if not args.target:
            fail("profile-info requires a profile name")
            sys.exit(1)
        cmd_profile_info(args.target)

    else:
        fail(f"Unknown command: {cmd}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
