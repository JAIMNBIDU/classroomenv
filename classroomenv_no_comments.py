"""
classroomenv.py — Reproducible Kali Linux Training Environment
Version: 2.0.0
License: MIT

Usage:
  sudo python3 classroomenv.py          # interactive menu
  sudo python3 classroomenv.py install web
  sudo python3 classroomenv.py verify web
  sudo python3 classroomenv.py doctor
"""

import sys
import os
import subprocess
import shutil
import re
import json
import argparse
import logging
import time
from datetime import datetime
from typing import Optional

if os.geteuid() != 0:
    print("\033[91m[!] classroomenv requires root. Run with sudo.\033[0m")
    sys.exit(1)

class C:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"
    BG_RED  = "\033[41m"

def ok(msg):   print(f"{C.GREEN}  \u2713 {msg}{C.RESET}")
def fail(msg): print(f"{C.RED}  \u2717 {msg}{C.RESET}")
def warn(msg): print(f"{C.YELLOW}  \u26a0 {msg}{C.RESET}")
def info(msg): print(f"{C.CYAN}  \u2192 {msg}{C.RESET}")
def step(msg): print(f"{C.MAGENTA}  \u25cf {msg}{C.RESET}")

def head(msg):
    w = 56
    print(f"\n{C.BOLD}{C.BLUE}\u2554{'='*w}\u2557")
    print(f"\u2551  {msg:<{w-2}}\u2551")
    print(f"\u255a{'='*w}\u255d{C.RESET}")

def subhead(msg):
    print(f"\n{C.BOLD}{C.CYAN}  +-- {msg} {C.RESET}")

def divider():
    print(f"{C.DIM}  {'-'*54}{C.RESET}")

LOG_FILE   = "/var/log/classroomenv.log"
STATE_FILE = "/var/lib/classroomenv/state.json"
LOCK_FILE  = "/var/run/classroomenv.lock"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("classroomenv")

try:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "a").close()
    os.chmod(LOG_FILE, 0o600)
except Exception:
    pass

import fcntl

_lock_fh = None

def _acquire_lock():
    global _lock_fh
    try:
        _lock_fh = open(LOCK_FILE, "w")
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fh.write(str(os.getpid()))
        _lock_fh.flush()
    except BlockingIOError:
        print(f"\033[91m[!] Another instance of classroomenv is already running.\033[0m")
        print(f"\033[93m    If this is wrong, delete {LOCK_FILE} and try again.\033[0m")
        sys.exit(1)
    except Exception:
        pass  # lock unavailable but non-blocking — continue

def _release_lock():
    global _lock_fh
    try:
        if _lock_fh:
            fcntl.flock(_lock_fh, fcntl.LOCK_UN)
            _lock_fh.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

import atexit
atexit.register(_release_lock)

REGISTRY = {

    "nmap": {
        "installer": "apt", "package": "nmap", "bin": "nmap",
        "version_cmd": ["nmap", "--version"],
        "version_re": r"Nmap version (\d+\.\d+[\w.]*)", "pinned": "7.94",
        "desc": "Network scanner and port mapper",
    },
    "git": {
        "installer": "apt", "package": "git", "bin": "git",
        "version_cmd": ["git", "--version"],
        "version_re": r"git version (\d+\.\d+\.\d+)", "pinned": "2.39",
        "desc": "Version control system",
    },
    "curl": {
        "installer": "apt", "package": "curl", "bin": "curl",
        "version_cmd": ["curl", "--version"],
        "version_re": r"curl (\d+\.\d+\.\d+)", "pinned": "7.88",
        "desc": "HTTP client and data transfer",
    },
    "wget": {
        "installer": "apt", "package": "wget", "bin": "wget",
        "version_cmd": ["wget", "--version"],
        "version_re": r"GNU Wget (\d+\.\d+[\.\d]*)", "pinned": "1.21",
        "desc": "File downloader",
    },
    "tmux": {
        "installer": "apt", "package": "tmux", "bin": "tmux",
        "version_cmd": ["tmux", "-V"],
        "version_re": r"tmux (\d+\.\d+)", "pinned": "3.3",
        "desc": "Terminal multiplexer",
    },
    "jq": {
        "installer": "apt", "package": "jq", "bin": "jq",
        "version_cmd": ["jq", "--version"],
        "version_re": r"jq-(\d+\.\d+[\.\d]*)", "pinned": "1.6",
        "desc": "JSON processor",
    },
    "netcat": {
        "installer": "apt", "package": "netcat-traditional", "bin": "nc",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "TCP/UDP Swiss army knife",
    },
    "vim": {
        "installer": "apt", "package": "vim", "bin": "vim",
        "version_cmd": ["vim", "--version"],
        "version_re": r"VIM - Vi IMproved (\d+\.\d+)", "pinned": "9.0",
        "desc": "Terminal text editor",
    },
    "python3": {
        "installer": "apt", "package": "python3", "bin": "python3",
        "version_cmd": ["python3", "--version"],
        "version_re": r"Python (\d+\.\d+\.\d+)", "pinned": "3.11",
        "desc": "Python 3 interpreter",
    },
    "pip": {
        "installer": "apt", "package": "python3-pip", "bin": "pip3",
        "version_cmd": ["pip3", "--version"],
        "version_re": r"pip (\d+\.\d+[\.\d]*)", "pinned": "23.0",
        "desc": "Python package manager",
    },
    "net-tools": {
        "installer": "apt", "package": "net-tools", "bin": "ifconfig",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "ifconfig, netstat, route",
    },
    "iputils-ping": {
        "installer": "apt", "package": "iputils-ping", "bin": "ping",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "ping utility",
    },
    "whois": {
        "installer": "apt", "package": "whois", "bin": "whois",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Domain/IP WHOIS lookup",
    },
    "dnsutils": {
        "installer": "apt", "package": "dnsutils", "bin": "dig",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "dig, nslookup, nsupdate",
    },
    "traceroute": {
        "installer": "apt", "package": "traceroute", "bin": "traceroute",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Network path tracer",
    },
    "golang": {
        "installer": "apt", "package": "golang-go", "bin": "go",
        "version_cmd": ["go", "version"],
        "version_re": r"go(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Go language (required for go-based tools)",
    },

    "ffuf": {
        "installer": "apt", "package": "ffuf", "bin": "ffuf",
        "version_cmd": ["ffuf", "-V"],
        "version_re": r"ffuf v?(\d+\.\d+[\.\d]*)", "pinned": "2.1.0",
        "desc": "Fast web fuzzer",
    },
    "gobuster": {
        "installer": "apt", "package": "gobuster", "bin": "gobuster",
        "version_cmd": ["gobuster", "version"],
        "version_re": r"(\d+\.\d+\.\d+)", "pinned": "3.6.0",
        "desc": "Directory/DNS/vhost brute-forcer",
    },
    "feroxbuster": {
        "installer": "apt", "package": "feroxbuster", "bin": "feroxbuster",
        "version_cmd": ["feroxbuster", "--version"],
        "version_re": r"(\d+\.\d+\.\d+)", "pinned": "2.10.0",
        "desc": "Recursive content discovery",
    },
    "burpsuite": {
        "installer": "apt", "package": "burpsuite", "bin": "burpsuite",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Web proxy and scanner (GUI)",
    },
    "seclists": {
        "installer": "apt", "package": "seclists", "bin": None,
        "version_cmd": None, "version_re": None, "pinned": None,
        "verify_path": "/usr/share/seclists",
        "desc": "Wordlists collection for security testing",
    },
    "httpx": {
        "installer": "go",
        "package": "github.com/projectdiscovery/httpx/cmd/httpx@v1.6.5",
        "bin": "httpx",
        "version_cmd": ["httpx", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)", "pinned": "1.6.5",
        "desc": "Fast HTTP probing tool",
    },
    "nikto": {
        "installer": "apt", "package": "nikto", "bin": "nikto",
        "version_cmd": ["nikto", "-Version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Web server vulnerability scanner",
    },
    "sqlmap": {
        "installer": "apt", "package": "sqlmap", "bin": "sqlmap",
        "version_cmd": ["sqlmap", "--version"],
        "version_re": r"(\d+\.\d+[\.\d#]*)", "pinned": None,
        "desc": "Automatic SQL injection tool",
    },
    "wpscan": {
        "installer": "apt", "package": "wpscan", "bin": "wpscan",
        "version_cmd": ["wpscan", "--version"],
        "version_re": r"(\d+\.\d+\.\d+)", "pinned": None,
        "desc": "WordPress vulnerability scanner",
    },
    "whatweb": {
        "installer": "apt", "package": "whatweb", "bin": "whatweb",
        "version_cmd": ["whatweb", "--version"],
        "version_re": r"WhatWeb version (\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Web technology fingerprinter",
    },
    "nuclei": {
        "installer": "go",
        "package": "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.2.0",
        "bin": "nuclei",
        "version_cmd": ["nuclei", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)", "pinned": "3.2.0",
        "desc": "Template-based vulnerability scanner",
    },
    "dirsearch": {
        "installer": "apt", "package": "dirsearch", "bin": "dirsearch",
        "version_cmd": ["dirsearch", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Web path scanner",
    },
    "zaproxy": {
        "installer": "apt", "package": "zaproxy", "bin": "zaproxy",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "OWASP ZAP web app scanner (GUI)",
    },

    "amass": {
        "installer": "apt", "package": "amass", "bin": "amass",
        "version_cmd": ["amass", "version"],
        "version_re": r"v?(\d+\.\d+[\.\d]*)", "pinned": "3.23.3",
        "desc": "Attack surface mapping",
    },
    "subfinder": {
        "installer": "go",
        "package": "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.6.6",
        "bin": "subfinder",
        "version_cmd": ["subfinder", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)", "pinned": "2.6.6",
        "desc": "Subdomain discovery",
    },
    "theHarvester": {
        "installer": "apt", "package": "theharvester", "bin": "theHarvester",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Email, subdomain, and name harvester",
    },
    "dnsx": {
        "installer": "go",
        "package": "github.com/projectdiscovery/dnsx/cmd/dnsx@v1.2.0",
        "bin": "dnsx",
        "version_cmd": ["dnsx", "-version"],
        "version_re": r"v?(\d+\.\d+\.\d+)", "pinned": "1.2.0",
        "desc": "Fast DNS toolkit",
    },
    "maltego": {
        "installer": "apt", "package": "maltego", "bin": "maltego",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Visual link analysis (GUI)",
    },
    "recon-ng": {
        "installer": "apt", "package": "recon-ng", "bin": "recon-ng",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Web reconnaissance framework",
    },
    "shodan": {
        "installer": "pip", "package": "shodan", "bin": None,
        "version_cmd": ["python3", "-c", "import shodan; print(shodan.__version__)"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Shodan Python API client",
    },
    "exiftool": {
        "installer": "apt", "package": "libimage-exiftool-perl", "bin": "exiftool",
        "version_cmd": ["exiftool", "-ver"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "File metadata extractor",
    },
    "spiderfoot": {
        "installer": "apt", "package": "spiderfoot", "bin": "spiderfoot",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Automated OSINT reconnaissance",
    },

    "impacket": {
        "installer": "apt", "package": "python3-impacket", "bin": None,
        "version_cmd": ["python3", "-c", "import impacket; print(impacket.__version__)"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": "0.11.0",
        "desc": "Python AD/SMB attack toolkit",
    },
    "netexec": {
        "installer": "apt", "package": "netexec", "bin": "netexec",
        "version_cmd": ["netexec", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Network exploitation framework",
    },
    "bloodhound": {
        "installer": "apt", "package": "bloodhound", "bin": "bloodhound",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "AD attack path mapping (GUI)",
    },
    "kerbrute": {
        "installer": "go",
        "package": "github.com/ropnop/kerbrute@v1.0.3",
        "bin": "kerbrute",
        "version_cmd": ["kerbrute", "version"],
        "version_re": r"v?(\d+\.\d+\.\d+)", "pinned": "1.0.3",
        "desc": "Kerberos brute-force and enumeration",
    },
    "enum4linux-ng": {
        "installer": "apt", "package": "enum4linux-ng", "bin": "enum4linux-ng",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "SMB/Samba enumeration",
    },
    "ldapdomaindump": {
        "installer": "pip", "package": "ldapdomaindump", "bin": "ldapdomaindump",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "LDAP domain info dumper",
    },
    "responder": {
        "installer": "apt", "package": "responder", "bin": "responder",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "LLMNR/NBT-NS/mDNS poisoner",
    },
    "evil-winrm": {
        "installer": "apt", "package": "evil-winrm", "bin": "evil-winrm",
        "version_cmd": ["evil-winrm", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "WinRM shell for pentesting",
    },

    "aircrack-ng": {
        "installer": "apt", "package": "aircrack-ng", "bin": "aircrack-ng",
        "version_cmd": ["aircrack-ng", "--version"],
        "version_re": r"Aircrack-ng (\d+\.\d+[\.\d]*)", "pinned": "1.7",
        "desc": "WEP/WPA/WPA2 cracking suite",
    },
    "hcxdumptool": {
        "installer": "apt", "package": "hcxdumptool", "bin": "hcxdumptool",
        "version_cmd": ["hcxdumptool", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Capture WiFi handshakes",
    },
    "hashcat": {
        "installer": "apt", "package": "hashcat", "bin": "hashcat",
        "version_cmd": ["hashcat", "--version"],
        "version_re": r"v?(\d+\.\d+[\.\d]*)", "pinned": "6.2.6",
        "desc": "GPU-accelerated password cracker",
    },
    "hcxtools": {
        "installer": "apt", "package": "hcxtools", "bin": "hcxpcapngtool",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Convert WiFi captures for hashcat",
    },
    "wifite": {
        "installer": "apt", "package": "wifite", "bin": "wifite",
        "version_cmd": ["wifite", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Automated wireless auditor",
    },
    "reaver": {
        "installer": "apt", "package": "reaver", "bin": "reaver",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "WPS PIN brute-force",
    },
    "bettercap": {
        "installer": "apt", "package": "bettercap", "bin": "bettercap",
        "version_cmd": ["bettercap", "-version"],
        "version_re": r"v?(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Network attacks and MitM framework",
    },

    "metasploit-framework": {
        "installer": "apt", "package": "metasploit-framework", "bin": "msfconsole",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "The Metasploit Framework",
    },
    "exploitdb": {
        "installer": "apt", "package": "exploitdb", "bin": "searchsploit",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Offline Exploit-DB + searchsploit",
    },
    "pwncat-cs": {
        "installer": "pip", "package": "pwncat-cs", "bin": "pwncat-cs",
        "version_cmd": ["pwncat-cs", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Post-exploitation platform",
    },
    "john": {
        "installer": "apt", "package": "john", "bin": "john",
        "version_cmd": ["john", "--version"],
        "version_re": r"John the Ripper[\w\s]*?(\d+\.\d+[\.\d\w]*)", "pinned": None,
        "desc": "John the Ripper password cracker",
    },
    "hydra": {
        "installer": "apt", "package": "hydra", "bin": "hydra",
        "version_cmd": ["hydra", "-h"],
        "version_re": r"Hydra v(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Online password brute-forcer",
    },
    "crackmapexec": {
        "installer": "apt", "package": "crackmapexec", "bin": "crackmapexec",
        "version_cmd": ["crackmapexec", "--version"],
        "version_re": r"(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "Network pentesting Swiss army knife",
    },

    "ghidra": {
        "installer": "apt", "package": "ghidra", "bin": "ghidra",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "NSA reverse engineering suite (GUI)",
    },
    "radare2": {
        "installer": "apt", "package": "radare2", "bin": "radare2",
        "version_cmd": ["radare2", "-version"],
        "version_re": r"radare2 (\d+\.\d+[\.\d]*)", "pinned": "5.8.8",
        "desc": "Reverse engineering framework",
    },
    "binwalk": {
        "installer": "apt", "package": "binwalk", "bin": "binwalk",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Firmware analysis and extraction",
    },
    "volatility3": {
        "installer": "pip", "package": "volatility3", "bin": "vol",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Memory forensics framework",
    },
    "gdb": {
        "installer": "apt", "package": "gdb", "bin": "gdb",
        "version_cmd": ["gdb", "--version"],
        "version_re": r"GNU gdb[^\d]*(\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "GNU debugger",
    },
    "strace": {
        "installer": "apt", "package": "strace", "bin": "strace",
        "version_cmd": ["strace", "--version"],
        "version_re": r"strace -- version (\d+\.\d+[\.\d]*)", "pinned": None,
        "desc": "System call tracer",
    },
    "ltrace": {
        "installer": "apt", "package": "ltrace", "bin": "ltrace",
        "version_cmd": None, "version_re": None, "pinned": None,
        "desc": "Library call tracer",
    },
}

PROFILES = {
    "core": {
        "display": "Core Essentials",
        "color": C.CYAN,
        "icon": "[*]",
        "description": "Essential tools every environment needs",
        "depends_on": [],
        "tools": [
            "nmap", "git", "curl", "wget", "python3", "pip",
            "tmux", "jq", "netcat", "vim", "net-tools",
            "iputils-ping", "whois", "dnsutils", "traceroute", "golang",
        ],
    },
    "web": {
        "display": "Web Pentesting",
        "color": C.GREEN,
        "icon": "[W]",
        "description": "Web app enumeration, fuzzing, scanning, exploitation",
        "depends_on": ["core"],
        "tools": [
            "ffuf", "gobuster", "feroxbuster", "burpsuite",
            "seclists", "httpx", "nikto", "sqlmap", "wpscan",
            "whatweb", "nuclei", "dirsearch", "zaproxy",
        ],
    },
    "osint": {
        "display": "OSINT",
        "color": C.YELLOW,
        "icon": "[O]",
        "description": "Open-source intelligence and reconnaissance",
        "depends_on": ["core"],
        "tools": [
            "amass", "subfinder", "theHarvester", "dnsx",
            "maltego", "recon-ng", "shodan", "exiftool", "spiderfoot",
        ],
    },
    "ad": {
        "display": "Active Directory",
        "color": C.MAGENTA,
        "icon": "[A]",
        "description": "AD attacks, enumeration, lateral movement",
        "depends_on": ["core"],
        "tools": [
            "impacket", "netexec", "bloodhound", "kerbrute",
            "enum4linux-ng", "ldapdomaindump", "responder", "evil-winrm",
        ],
    },
    "wireless": {
        "display": "Wireless",
        "color": C.BLUE,
        "icon": "[~]",
        "description": "WiFi auditing, WPA cracking, MitM attacks",
        "depends_on": ["core"],
        "tools": [
            "aircrack-ng", "hcxdumptool", "hashcat", "hcxtools",
            "wifite", "reaver", "bettercap",
        ],
    },
    "exploitation": {
        "display": "Exploitation",
        "color": C.RED,
        "icon": "[!]",
        "description": "Exploitation frameworks, password cracking, post-exploitation",
        "depends_on": ["core"],
        "tools": [
            "metasploit-framework", "exploitdb", "pwncat-cs",
            "john", "hydra", "crackmapexec",
        ],
    },
    "extras": {
        "display": "Reverse Engineering & Forensics",
        "color": C.WHITE,
        "icon": "[R]",
        "description": "Binary analysis, debugging, memory forensics",
        "depends_on": ["core"],
        "tools": [
            "ghidra", "radare2", "binwalk", "volatility3",
            "gdb", "strace", "ltrace",
        ],
    },
    "full": {
        "display": "Full Arsenal",
        "color": C.RED,
        "icon": "[X]",
        "description": "Every profile — installs everything",
        "depends_on": ["core", "web", "osint", "ad", "wireless", "exploitation", "extras"],
        "tools": [],
    },
}

def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"installed": {}, "profiles": []}

def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    os.chmod(STATE_FILE, 0o600)

def _record_install(tool, version):
    state = _load_state()
    state["installed"][tool] = {
        "version": version,
        "installed_at": datetime.now().isoformat(),
    }
    _save_state(state)

def _record_profile(profile):
    state = _load_state()
    if profile not in state["profiles"]:
        state["profiles"].append(profile)
    _save_state(state)

def _run(cmd, capture=True, timeout=300):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            timeout=timeout, text=True,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout after {timeout}s"
    except FileNotFoundError:
        return 1, "", f"Not found: {cmd[0]}"
    except Exception as e:
        return 1, "", str(e)

def _apt_install(package):
    rc, _, _ = _run(
        ["apt-get", "install", "-y", "--no-install-recommends", package],
        capture=False
    )
    return rc == 0

def _pip_install(package):
    rc, _, _ = _run(["pip3", "install", "--quiet", package], capture=False)
    return rc == 0

def _go_install(package):
    if not shutil.which("go"):
        fail("Go not installed. Run: apt-get install golang-go")
        return False
    env = os.environ.copy()
    env.setdefault("GOPATH", "/root/go")
    env["GOBIN"] = "/usr/local/bin"
    result = subprocess.run(["go", "install", package], env=env, timeout=300)
    return result.returncode == 0

def _get_version(tool):
    meta = REGISTRY.get(tool)
    if not meta:
        return None
    if meta.get("verify_path"):
        return "present" if os.path.exists(meta["verify_path"]) else None
    if not meta.get("version_cmd"):
        b = meta.get("bin")
        return "present" if (b and shutil.which(b)) else None
    rc, stdout, stderr = _run(meta["version_cmd"])
    combined = stdout + stderr
    if not meta.get("version_re"):
        return "present" if (rc == 0 or combined.strip()) else None
    m = re.search(meta["version_re"], combined)
    return m.group(1) if m else None

def _version_matches(found, pinned):
    return found.startswith(pinned)

def _resolve_profiles(name):
    if name not in PROFILES:
        fail(f"Unknown profile: {name}")
        sys.exit(1)
    seen = []
    def _walk(n):
        for dep in PROFILES[n].get("depends_on", []):
            _walk(dep)
        if n not in seen:
            seen.append(n)
    _walk(name)
    return seen

def _tools_for_profile(name):
    tools = []
    for p in _resolve_profiles(name):
        for t in PROFILES[p]["tools"]:
            if t not in tools:
                tools.append(t)
    return tools

def _do_install(profile_name):
    pmeta = PROFILES[profile_name]
    head(f"{pmeta['icon']}  Installing: {pmeta['display']}")
    tools = _tools_for_profile(profile_name)
    chain = _resolve_profiles(profile_name)
    info(f"Profile chain : {' -> '.join(chain)}")
    info(f"Tools to process: {len(tools)}")
    print()
    info("Running apt-get update...")
    _run(["apt-get", "update", "-qq"], capture=False)

    success, skipped, failed_tools = [], [], []
    total = len(tools)

    for i, tool in enumerate(tools, 1):
        meta = REGISTRY.get(tool)
        if not meta:
            warn(f"[{i}/{total}] {tool} -- not in registry, skipping")
            skipped.append(tool)
            continue

        existing = _get_version(tool)
        if existing:
            ok(f"[{i}/{total}] {tool:<24} already installed ({existing})")
            skipped.append(tool)
            continue

        step(f"[{i}/{total}] {tool:<24} {meta.get('desc','')}")
        installer = meta["installer"]

        if installer == "apt":
            result = _apt_install(meta["package"])
        elif installer == "pip":
            result = _pip_install(meta["package"])
        elif installer == "go":
            result = _go_install(meta["package"])
        else:
            warn(f"Unknown installer type: {installer}")
            skipped.append(tool)
            continue

        if result:
            v = _get_version(tool)
            ok(f"  +-- installed ({v or 'ok'})")
            _record_install(tool, v)
            success.append(tool)
            log.info(f"Installed {tool} v{v}")
        else:
            fail(f"  +-- FAILED")
            failed_tools.append(tool)
            log.error(f"Failed: {tool}")

    _record_profile(profile_name)
    print()
    head("Install Summary")
    ok(f"Installed : {len(success)}")
    info(f"Skipped   : {len(skipped)}  (already present)")
    if failed_tools:
        fail(f"Failed    : {len(failed_tools)}  ->  {', '.join(failed_tools)}")
    else:
        ok("No failures")

def _do_verify(profile_name):
    pmeta = PROFILES[profile_name]
    head(f"Verifying: {pmeta['display']}")
    tools = _tools_for_profile(profile_name)
    passed, warned, missing = [], [], []

    for tool in tools:
        meta = REGISTRY.get(tool)
        if not meta:
            warn(f"{tool:<26} not in registry")
            continue
        found  = _get_version(tool)
        pinned = meta.get("pinned")

        if found is None:
            fail(f"{tool:<26} NOT FOUND")
            missing.append(tool)
        elif pinned is None:
            ok(f"{tool:<26} {str(found):<14} (unpinned)")
            passed.append(tool)
        elif _version_matches(found, pinned):
            ok(f"{tool:<26} {str(found):<14} matches pin {pinned}")
            passed.append(tool)
        else:
            fail(f"{tool:<26} MISMATCH  expected={pinned}  found={found}")
            warned.append(tool)

    print()
    head("Verify Summary")
    ok(f"Passed  : {len(passed)}")
    if warned:
        warn(f"Mismatch: {len(warned)}  ->  {', '.join(warned)}")
    if missing:
        fail(f"Missing : {len(missing)}  ->  {', '.join(missing)}")

def _do_doctor():
    head("System Health Check")
    issues = 0

    try:
        content = open("/etc/os-release").read()
        if "kali" in content.lower():
            vm = re.search(r'VERSION_ID="?(\S+?)"?\s', content)
            ok(f"Kali Linux {vm.group(1) if vm else 'detected'}")
        else:
            warn("Not Kali Linux -- some packages may be unavailable")
    except Exception:
        warn("Could not read /etc/os-release")

    rc, _, _ = _run(["curl", "-s", "--max-time", "5", "https://kali.org"])
    if rc == 0: ok("Internet connectivity")
    else:       fail("No internet connection"); issues += 1

    rc, _, _ = _run(["apt-get", "check"])
    if rc == 0: ok("apt functional")
    else:       fail("apt broken or locked"); issues += 1

    rc, out, _ = _run(["python3", "--version"])
    if rc == 0: ok(out.strip())
    else:       fail("python3 missing"); issues += 1

    if shutil.which("pip3"): ok("pip3 available")
    else: warn("pip3 not found -- pip-based tools will fail")

    if shutil.which("go"):
        _, out, _ = _run(["go", "version"])
        ok(out.strip())
    else:
        warn("Go not installed -- go-based tools will fail")
        warn("Fix: apt-get install golang-go")

    if shutil.which("git"): ok("git available")
    else: fail("git missing"); issues += 1

    stat = os.statvfs("/")
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    if free_gb >= 10:  ok(f"Disk: {free_gb:.1f} GB free")
    elif free_gb >= 5: warn(f"Disk: {free_gb:.1f} GB free (low for full install)")
    else:              fail(f"Disk: {free_gb:.1f} GB -- critically low"); issues += 1

    paths = os.environ.get("PATH", "").split(":")
    for p in ["/usr/bin", "/usr/local/bin", "/usr/sbin"]:
        if p in paths: ok(f"PATH contains {p}")
        else:          warn(f"PATH missing {p}")

    rc1, _, _ = _run(["systemctl", "is-active", "open-vm-tools"])
    rc2, _, _ = _run(["systemctl", "is-active", "virtualbox-guest-utils"])
    if rc1 == 0:   ok("VMware open-vm-tools active")
    elif rc2 == 0: ok("VirtualBox guest utils active")
    else:          info("No VM guest tools detected (normal on bare metal)")

    ok(f"Log file: {LOG_FILE}")

    print()
    if issues == 0: ok("System is ready for classroomenv")
    else:           fail(f"{issues} critical issue(s) -- fix before installing")
    return issues

def _do_inventory():
    head("Installed Tool Inventory")
    state = _load_state()
    profiles = state.get("profiles", [])

    if not profiles:
        info("No profiles installed yet.")
        return

    info(f"Installed profiles: {', '.join(profiles)}")
    print()
    fmt = f"  {'Tool':<24} {'Type':<5} {'Pinned':<10} {'Found':<16} Status"
    print(f"{C.BOLD}{fmt}{C.RESET}")
    divider()

    shown = set()
    for p in profiles:
        for t in _tools_for_profile(p):
            if t in shown:
                continue
            shown.add(t)
            meta   = REGISTRY.get(t, {})
            pinned = meta.get("pinned") or "---"
            found  = _get_version(t) or "not found"
            inst   = meta.get("installer", "?")

            if found == "not found":
                status = f"{C.RED}MISSING{C.RESET}"
            elif pinned == "---":
                status = f"{C.GREEN}OK{C.RESET}"
            elif _version_matches(found, pinned):
                status = f"{C.GREEN}OK{C.RESET}"
            else:
                status = f"{C.YELLOW}MISMATCH{C.RESET}"

            print(f"  {t:<24} {inst:<5} {pinned:<10} {found:<16} {status}")

def _fix_apt_sources():
    sources = "/etc/apt/sources.list"
    kali_repo = "deb https://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware\n"
    try:
        content = open(sources).read()
        if "http://http.kali.org" in content:
            content = content.replace(
                "deb http://http.kali.org/kali",
                "deb https://http.kali.org/kali"
            )
            with open(sources, "w") as f:
                f.write(content)
            ok("Upgraded existing kali repo entry to HTTPS")
        elif "kali-rolling" not in content:
            with open(sources, "a") as f:
                f.write("\n" + kali_repo)
            ok("Added kali-rolling repo (HTTPS) to sources.list")
        else:
            ok("kali-rolling repo already present")
    except Exception as e:
        warn(f"Could not update sources.list: {e}")

def _install_vm_tools():
    _, dmi_out, _ = _run(["dmidecode", "-s", "system-manufacturer"])
    manufacturer = dmi_out.lower().strip()
    if "vmware" in manufacturer:
        info("VMware detected -- installing open-vm-tools")
        _run(["apt-get", "install", "-y", "open-vm-tools", "open-vm-tools-desktop"], capture=False)
        _run(["systemctl", "enable", "--now", "open-vm-tools"], capture=False)
        ok("VMware guest tools installed and enabled")
    elif "virtualbox" in manufacturer or "innotek" in manufacturer:
        info("VirtualBox detected -- installing guest additions")
        _run(["apt-get", "install", "-y", "virtualbox-guest-x11", "virtualbox-guest-utils"], capture=False)
        ok("VirtualBox guest additions installed")
    else:
        info("Hypervisor not detected -- skipping VM guest tools")

def _do_fresh_setup():
    os.system("clear")
    head("Fresh Kali Linux Setup")
    print(f"""
  {C.YELLOW}This will run the following steps:{C.RESET}

  [1] Fix apt sources (ensure kali-rolling is on HTTPS)
  [2] apt-get update
  [3] apt-get upgrade  (safe upgrade -- skips kernel/driver replacements)
  [4] Install VMware / VirtualBox guest tools (auto-detected)
  [5] Install kali-linux-headless meta-package
  [6] Install Go (required for httpx, nuclei, subfinder, etc.)
  [7] Install core profile (16 essential tools)
  [8] apt autoremove + autoclean

  {C.RED}This will take 10-30 minutes depending on internet speed.{C.RESET}
  {C.RED}Do not close the terminal.{C.RESET}
""")

    confirm = input(f"  {C.BOLD}Proceed with fresh setup? [y/N]: {C.RESET}").strip().lower()
    if confirm != "y":
        info("Aborted -- returning to menu")
        return

    steps = [
        ("Fixing apt sources",              _fix_apt_sources),
        ("Running apt update",              lambda: _run(["apt-get", "update"], capture=False)),
        ("System upgrade",                  lambda: _run(["apt-get", "upgrade", "-y"], capture=False)),
        ("Installing VM guest tools",       _install_vm_tools),
        ("Installing kali-linux-headless",  lambda: _run(["apt-get", "install", "-y", "kali-linux-headless"], capture=False)),
        ("Installing Go",                   lambda: _run(["apt-get", "install", "-y", "golang-go"], capture=False)),
        ("Installing core profile",         lambda: _do_install("core")),
        ("Cleaning up",                     lambda: (_run(["apt-get", "autoremove", "-y"], capture=False),
                                                     _run(["apt-get", "autoclean"], capture=False))),
    ]

    for label, fn in steps:
        print()
        step(label)
        try:
            fn()
            ok(f"Done: {label}")
        except Exception as e:
            warn(f"Warning during '{label}': {e}")

    print()
    head("Fresh Setup Complete")
    ok("System upgraded, VM tools installed, core profile ready")
    info("Run doctor from the menu to verify your environment")
    info("Then pick whichever profiles you need")

def _do_update():
    head("System Update")
    for cmd, label in [
        (["apt-get", "update"],         "Updating package lists"),
        (["apt-get", "upgrade", "-y"],  "Upgrading installed packages"),
        (["apt-get", "autoremove", "-y"], "Removing unused packages"),
        (["apt-get", "autoclean"],      "Cleaning apt cache"),
    ]:
        step(label)
        _run(cmd, capture=False)
        ok("Done")

    state = _load_state()
    if state.get("profiles"):
        print()
        info("Re-verifying installed profiles...")
        for p in state["profiles"]:
            if p in PROFILES:
                _do_verify(p)

def _banner():
    os.system("clear")
    art = r"""

░█████╗░██╗░░░░░░█████╗░░██████╗░██████╗██████╗░░█████╗░░█████╗░███╗░░░███╗███████╗███╗░░██╗██╗░░░██╗
██╔══██╗██║░░░░░██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗████╗░████║██╔════╝████╗░██║██║░░░██║
██║░░╚═╝██║░░░░░███████║╚█████╗░╚█████╗░██████╔╝██║░░██║██║░░██║██╔████╔██║█████╗░░██╔██╗██║╚██╗░██╔╝
██║░░██╗██║░░░░░██╔══██║░╚═══██╗░╚═══██╗██╔══██╗██║░░██║██║░░██║██║╚██╔╝██║██╔══╝░░██║╚████║░╚████╔╝░
╚█████╔╝███████╗██║░░██║██████╔╝██████╔╝██║░░██║╚█████╔╝╚█████╔╝██║░╚═╝░██║███████╗██║░╚███║░░╚██╔╝░░
░╚════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚═════╝░╚═╝░░╚═╝░╚════╝░░╚════╝░╚═╝░░░░░╚═╝╚══════╝╚═╝░░╚══╝░░░╚═╝░░░

    print(f"{C.CYAN}{C.BOLD}{art}{C.RESET}")
    print(f"  {C.YELLOW}Reproducible Kali Linux Training Environment{C.RESET}  "
          f"{C.DIM}v2.0.0  |  Log: {LOG_FILE}{C.RESET}\n")

def _show_profile_and_confirm(profile_name):
    _banner()
    meta  = PROFILES[profile_name]
    color = meta["color"]
    head(f"{meta['icon']}  {meta['display']}")
    print(f"  {meta['description']}\n")

    deps = meta.get("depends_on", [])
    if deps:
        info(f"Also installs dependencies: {', '.join(deps)}")
        print()

    all_tools  = _tools_for_profile(profile_name)
    own_tools  = meta["tools"]
    inherited  = [t for t in all_tools if t not in own_tools]

    subhead(f"Tools in this profile ({len(own_tools)})")
    for t in own_tools:
        m     = REGISTRY.get(t, {})
        inst  = m.get("installer", "?")
        pin   = m.get("pinned") or "latest"
        desc  = m.get("desc", "")
        found = _get_version(t)
        tick  = f"{C.GREEN}[installed]{C.RESET}" if found else f"{C.DIM}[not installed]{C.RESET}"
        print(f"  {color}{t:<24}{C.RESET} [{inst:<3}] pin:{pin:<10} {C.DIM}{desc}{C.RESET}  {tick}")

    if inherited:
        print()
        subhead(f"Inherited from dependencies ({len(inherited)})")
        for t in inherited:
            found = _get_version(t)
            tick  = f"{C.GREEN}[installed]{C.RESET}" if found else f"{C.DIM}[not installed]{C.RESET}"
            print(f"  {C.DIM}{t:<24}{C.RESET}  {tick}")

    print()
    divider()
    already   = sum(1 for t in all_tools if _get_version(t))
    remaining = len(all_tools) - already
    info(f"{already}/{len(all_tools)} tools already installed -- {remaining} will be installed")

    needs_go = [t for t in all_tools if REGISTRY.get(t, {}).get("installer") == "go"]
    if needs_go and not shutil.which("go"):
        print()
        print(f"  {C.YELLOW}{C.BOLD}  !! WARNING: Go is not installed !!{C.RESET}")
        print(f"  {C.YELLOW}  These tools in this profile will FAIL without it:{C.RESET}")
        for t in needs_go:
            print(f"  {C.RED}    - {t}{C.RESET}")
        print(f"\n  {C.BOLD}  Install Go first:{C.RESET}")
        print(f"  {C.GREEN}    sudo apt-get install golang-go{C.RESET}")
        print(f"\n  {C.YELLOW}  You can still continue -- apt tools will install fine.")
        print(f"  Go tools will be skipped and can be installed after.{C.RESET}")
    print()

    choice = input(f"  {C.BOLD}Install '{profile_name}' profile? [y/N]: {C.RESET}").strip().lower()
    if choice == "y":
        print()
        _do_install(profile_name)
    else:
        info("Installation cancelled -- returning to menu")
    input(f"\n  {C.DIM}Press Enter to return to menu...{C.RESET}")

def _menu_verify():
    _banner()
    head("Verify Installed Profiles")
    state    = _load_state()
    profiles = state.get("profiles", [])

    if not profiles:
        warn("No profiles installed yet.")
        input(f"\n  {C.DIM}Press Enter to return...{C.RESET}")
        return

    print(f"  {C.BOLD}Select profile to verify:{C.RESET}\n")
    for i, p in enumerate(profiles, 1):
        pmeta = PROFILES.get(p, {})
        print(f"  {C.CYAN}[{i}]{C.RESET} {pmeta.get('display', p)}")
    print(f"  {C.CYAN}[a]{C.RESET} Verify all profiles")
    print(f"  {C.RED}[0]{C.RESET} Back to menu")
    print()

    choice = input(f"  {C.BOLD}Select: {C.RESET}").strip().lower()
    if choice == "0":
        return
    elif choice == "a":
        for p in profiles:
            if p in PROFILES:
                _do_verify(p)
    elif choice.isdigit() and 1 <= int(choice) <= len(profiles):
        _do_verify(profiles[int(choice) - 1])
    else:
        warn("Invalid selection")

    input(f"\n  {C.DIM}Press Enter to return...{C.RESET}")


GO_TOOLS = [t for t, m in REGISTRY.items() if m.get("installer") == "go"]

def _check_requirements(auto=False):
    """
    Check all runtime requirements.
    auto=True  -> called silently at startup; only blocks if critical issues found.
    auto=False -> called from menu; always shows full output and waits for input.
    """
    _banner()
    head("Requirements Check")

    if auto:
        print(f"  {C.DIM}Running startup requirements check...{C.RESET}\n")
    else:
        print(f"  Checking everything classroomenv needs before you install anything.\n")

    issues   = []   # critical — must fix
    warnings = []   # non-critical — will limit some tools

    pv = sys.version_info
    if pv.major == 3 and pv.minor >= 10:
        ok(f"Python {pv.major}.{pv.minor}.{pv.micro}  (required: 3.10+)")
    else:
        fail(f"Python {pv.major}.{pv.minor} is too old  (required: 3.10+)")
        issues.append("python3 >= 3.10")

    if shutil.which("pip3"):
        rc, out, _ = _run(["pip3", "--version"])
        ver = re.search(r"pip (\S+)", out)
        ok(f"pip3 {ver.group(1) if ver else 'found'}")
    else:
        fail("pip3 not found")
        issues.append("pip3  ->  fix: apt-get install python3-pip")

    if shutil.which("go"):
        rc, out, _ = _run(["go", "version"])
        ver = re.search(r"go(\d+\.\d+[\.\d]*)", out)
        ok(f"Go {ver.group(1) if ver else 'found'}")
    else:
        fail("Go is NOT installed")
        print()
        print(f"  {C.YELLOW}{C.BOLD}  !! IMPORTANT !!")
        print(f"  {C.RESET}{C.YELLOW}  The following tools WILL FAIL to install without Go:{C.RESET}")
        for t in GO_TOOLS:
            desc = REGISTRY[t].get("desc", "")
            print(f"  {C.RED}    - {t:<20}{C.RESET} {C.DIM}{desc}{C.RESET}")
        print()
        print(f"  {C.BOLD}  Fix this now by running:{C.RESET}")
        print(f"  {C.GREEN}    sudo apt-get install golang-go{C.RESET}")
        print()
        warnings.append("golang-go")

    rc, _, _ = _run(["curl", "-s", "--max-time", "5", "https://kali.org"])
    if rc == 0:
        ok("Internet connectivity")
    else:
        fail("No internet connection detected")
        issues.append("internet  ->  required for all installations")

    rc, _, err = _run(["apt-get", "check"])
    if rc == 0:
        ok("apt is functional")
    else:
        fail(f"apt is broken or locked: {err.strip()[:60]}")
        issues.append("apt  ->  fix: sudo dpkg --configure -a")

    stat    = os.statvfs("/")
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    if free_gb >= 10:
        ok(f"Disk space: {free_gb:.1f} GB free")
    elif free_gb >= 5:
        warn(f"Disk space: {free_gb:.1f} GB free  (10 GB+ recommended for full install)")
        warnings.append(f"low disk: {free_gb:.1f} GB")
    else:
        fail(f"Disk space critical: {free_gb:.1f} GB free")
        issues.append(f"disk space  ->  only {free_gb:.1f} GB free, need at least 5 GB")

    try:
        content = open("/etc/os-release").read()
        if "kali" in content.lower():
            vm = re.search(r'VERSION_ID="?(\S+?)"?\s', content)
            ok(f"Kali Linux {vm.group(1) if vm else 'detected'}")
        else:
            warn("Not running Kali Linux -- apt packages may not exist")
            warnings.append("non-Kali OS")
    except Exception:
        warn("Could not detect OS")

    print()
    divider()

    if not issues and not warnings:
        ok("All requirements satisfied. You are good to go.")
        print()
        if not auto:
            input(f"  {C.DIM}Press Enter to return to menu...{C.RESET}")
        return True

    if warnings and not issues:
        print(f"\n  {C.YELLOW}{C.BOLD}Warnings ({len(warnings)}):{C.RESET}")
        for w in warnings:
            warn(w)
        print(f"\n  {C.YELLOW}These are not blockers but some tools will fail.")
        print(f"  Strongly recommended: install Go before proceeding.{C.RESET}")
        print()
        if not auto:
            input(f"  {C.DIM}Press Enter to return to menu...{C.RESET}")
        return True  # warnings don't block

    if issues:
        print(f"\n  {C.RED}{C.BOLD}Critical issues found ({len(issues)}) -- fix before installing:{C.RESET}")
        for i in issues:
            fail(i)
        print()
        if auto:
            print(f"  {C.RED}Cannot continue. Fix the above issues and re-run.{C.RESET}\n")
            input(f"  {C.DIM}Press Enter to exit...{C.RESET}")
            sys.exit(1)
        else:
            input(f"  {C.DIM}Press Enter to return to menu...{C.RESET}")
        return False

    return True

PROFILE_KEYS = ["core", "web", "osint", "ad", "wireless", "exploitation", "extras", "full"]

def _interactive_menu():
    _check_requirements(auto=True)

    while True:
        _banner()
        state    = _load_state()
        inst_prf = state.get("profiles", [])

        if inst_prf:
            print(f"  {C.DIM}Active profiles: {', '.join(inst_prf)}{C.RESET}\n")
        else:
            print(f"  {C.DIM}No profiles installed yet{C.RESET}\n")

        print(f"  {C.BOLD}{C.BG_RED}[0]{C.RESET} {C.RED} FRESH KALI SETUP{C.RESET}  "
              f"{C.DIM}<-- New VM? Start here. Upgrades system + installs core + VM tools{C.RESET}")
        print()
        divider()
        print(f"  {C.BOLD}  INSTALL PROFILES{C.RESET}")
        divider()

        for i, key in enumerate(PROFILE_KEYS, 1):
            pmeta     = PROFILES[key]
            color     = pmeta["color"]
            installed = (key in inst_prf)
            tag       = f"  {C.GREEN}[installed]{C.RESET}" if installed else ""
            tool_count = len(pmeta["tools"]) if pmeta["tools"] else "all"
            print(f"  {C.CYAN}[{i}]{C.RESET} {color}{pmeta['icon']} {pmeta['display']:<30}{C.RESET}"
                  f" {C.DIM}({tool_count} tools){C.RESET}{tag}")

        print()
        divider()
        print(f"  {C.CYAN}[r]{C.RESET}  {C.YELLOW}Requirements check{C.RESET}  {C.DIM}<-- run this first if you haven't{C.RESET}")
        print(f"  {C.CYAN}[u]{C.RESET}  Update system (apt upgrade + verify)")
        print(f"  {C.CYAN}[v]{C.RESET}  Verify installed profiles")
        print(f"  {C.CYAN}[i]{C.RESET}  Inventory (all installed tools + versions)")
        print(f"  {C.CYAN}[d]{C.RESET}  Doctor (system health check)")
        print(f"  {C.RED}[q]{C.RESET}  Quit")
        divider()

        choice = input(f"\n  {C.BOLD}Select: {C.RESET}").strip().lower()

        if choice == "q":
            print(f"\n  {C.CYAN}Goodbye.{C.RESET}\n")
            sys.exit(0)
        elif choice == "0":
            _do_fresh_setup()
            input(f"\n  {C.DIM}Press Enter to return to menu...{C.RESET}")
        elif choice == "r":
            _check_requirements(auto=False)
        elif choice == "u":
            _banner()
            _do_update()
            input(f"\n  {C.DIM}Press Enter to return to menu...{C.RESET}")
        elif choice == "v":
            _menu_verify()
        elif choice == "i":
            _banner()
            _do_inventory()
            input(f"\n  {C.DIM}Press Enter to return to menu...{C.RESET}")
        elif choice == "d":
            _banner()
            _do_doctor()
            input(f"\n  {C.DIM}Press Enter to return to menu...{C.RESET}")
        elif choice.isdigit() and 1 <= int(choice) <= len(PROFILE_KEYS):
            _show_profile_and_confirm(PROFILE_KEYS[int(choice) - 1])
        else:
            warn("Invalid selection")
            time.sleep(1)

def main():
    _acquire_lock()

    if len(sys.argv) == 1:
        _interactive_menu()
        return

    parser = argparse.ArgumentParser(
        prog="classroomenv",
        description="Reproducible Kali Linux training environment"
    )
    parser.add_argument("command", help="install|verify|doctor|inventory|list|update|fresh|profile-info")
    parser.add_argument("target", nargs="?", help="Profile name")
    args = parser.parse_args()

    _banner()
    cmd = args.command.lower()

    if cmd == "install":
        if not args.target:
            fail("Usage: classroomenv install <profile>")
            sys.exit(1)
        _do_install(args.target)
    elif cmd == "verify":
        if not args.target:
            fail("Usage: classroomenv verify <profile>")
            sys.exit(1)
        _do_verify(args.target)
    elif cmd == "doctor":
        _do_doctor()
    elif cmd == "inventory":
        _do_inventory()
    elif cmd == "update":
        _do_update()
    elif cmd == "fresh":
        _do_fresh_setup()
    elif cmd == "list":
        for name, pmeta in PROFILES.items():
            c = pmeta["color"]
            print(f"\n  {c}{C.BOLD}{pmeta['icon']} {name}{C.RESET}")
            print(f"  {pmeta['description']}")
            print(f"  Tools: {len(pmeta['tools'])}")
    elif cmd in ("profile-info", "profile_info"):
        if not args.target:
            fail("Usage: classroomenv profile-info <name>")
            sys.exit(1)
        _show_profile_and_confirm(args.target)
    else:
        fail(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()