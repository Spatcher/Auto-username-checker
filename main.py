"""
Username Availability Checker — v2
Checks usernames across major social media platforms.
Supports per-platform character sets (letters, numbers, underscores, dots).
Results saved to found_usernames.txt
"""

import asyncio
import aiohttp
import itertools
import string
import random
from datetime import datetime

# ─────────────────────────────────────────────
#  MULTI-INSTANCE CONFIG
#  When running on multiple machines, set a different
#  INSTANCE_ID (0-based) and TOTAL_INSTANCES on each one.
#  Example: 5 machines → TOTAL_INSTANCES=5, INSTANCE_ID=0..4
# ─────────────────────────────────────────────

INSTANCE_ID      = 0   # This machine's ID (0, 1, 2, 3, 4 ...)
TOTAL_INSTANCES  = 1   # Total number of machines running in parallel

# ─────────────────────────────────────────────
#  GENERAL CONFIG
# ─────────────────────────────────────────────

LENGTHS      = [3, 4, 5]   # Username lengths to check
RANDOMIZE    = True         # Shuffle order to avoid sequential hammering
DELAY        = 0.3          # Seconds between each username batch
CONCURRENT   = 10           # Max concurrent requests
OUTPUT_FILE  = f"found_usernames_instance{INSTANCE_ID}.txt"

# ─────────────────────────────────────────────
#  CHARACTER SETS
# ─────────────────────────────────────────────

L   = string.ascii_lowercase
U   = string.ascii_uppercase
D   = string.digits
UND = "_"
DOT = "."
DAS = "-"

# ─────────────────────────────────────────────
#  PER-PLATFORM DEFINITIONS
# ─────────────────────────────────────────────

PLATFORMS = {
    "YouTube": {
        "url":       "https://www.youtube.com/@{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND + DOT + DAS,
        "min_len":   3,
        "max_len":   30,
        "no_leading_hyphen":  True,
        "no_trailing_hyphen": True,
        "no_leading_dot":     True,
        "no_trailing_dot":    True,
    },
    "TikTok": {
        "url":       "https://www.tiktok.com/@{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND + DOT,
        "min_len":   2,
        "max_len":   24,
        "no_leading_dot":     True,
        "no_trailing_dot":    True,
        "no_leading_underscore":  True,
        "no_trailing_underscore": True,
    },
    "Twitch": {
        "url":       "https://www.twitch.tv/{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   4,
        "max_len":   25,
    },
    "GitHub": {
        "url":       "https://github.com/{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + DAS,
        "min_len":   1,
        "max_len":   39,
        "no_leading_hyphen":  True,
        "no_trailing_hyphen": True,
        "no_double_hyphen":   True,
    },
    "Instagram": {
        "url":       "https://www.instagram.com/{}/",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND + DOT,
        "min_len":   1,
        "max_len":   30,
        "no_leading_dot":     True,
        "no_trailing_dot":    True,
        "no_double_dot":      True,
    },
    "Twitter/X": {
        "url":       "https://x.com/{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   1,
        "max_len":   15,
    },
    "Pinterest": {
        "url":       "https://www.pinterest.com/{}/",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   3,
        "max_len":   30,
    },
    "Roblox": {
        "url":       "https://www.roblox.com/user.aspx?username={}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   3,
        "max_len":   20,
        "no_leading_underscore":  True,
        "no_trailing_underscore": True,
        "no_double_underscore":   True,
    },
}

# Optional Discord bot token — uncomment to enable Discord checks:
# DISCORD_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ─────────────────────────────────────────────
#  USERNAME GENERATOR
# ─────────────────────────────────────────────

def all_platform_chars():
    chars = set()
    for p in PLATFORMS.values():
        chars.update(p["chars"])
    # Put letters first so combos start with real words, not symbols
    letters = [c for c in chars if c.isalpha()]
    digits  = [c for c in chars if c.isdigit()]
    special = [c for c in chars if not c.isalnum()]
    return "".join(sorted(letters) + sorted(digits) + sorted(special))

def generate_usernames(lengths):
    """
    Lazy generator — yields one username at a time, no RAM blowup.
    RANDOMIZE is disabled when using a generator (can't shuffle infinite streams).
    If you want random order, set LENGTHS = [3] or [3, 4] only and it'll
    collect those into memory safely (much smaller sets).
    """
    chars = all_platform_chars()
    index = 0
    for length in lengths:
        for combo in itertools.product(chars, repeat=length):
            if index % TOTAL_INSTANCES == INSTANCE_ID:
                yield "".join(combo)
            index += 1

def is_valid_for_platform(username, cfg):
    length = len(username)
    if length < cfg["min_len"]:
        return False
    if cfg["max_len"] and length > cfg["max_len"]:
        return False
    allowed = set(cfg["chars"])
    if not all(c in allowed for c in username):
        return False
    # Underscore rules
    if cfg.get("no_leading_underscore")  and username.startswith("_"): return False
    if cfg.get("no_trailing_underscore") and username.endswith("_"):   return False
    if cfg.get("no_double_underscore")   and "__" in username:         return False
    # Hyphen rules
    if cfg.get("no_leading_hyphen")      and username.startswith("-"): return False
    if cfg.get("no_trailing_hyphen")     and username.endswith("-"):   return False
    if cfg.get("no_double_hyphen")       and "--" in username:         return False
    # Dot rules
    if cfg.get("no_leading_dot")         and username.startswith("."): return False
    if cfg.get("no_trailing_dot")        and username.endswith("."):   return False
    if cfg.get("no_double_dot")          and ".." in username:         return False
    return True

# ─────────────────────────────────────────────
#  HTTP CHECKER
# ─────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

async def check_platform(session, semaphore, platform_name, cfg, username, results):
    if not is_valid_for_platform(username, cfg):
        return None

    url = cfg["url"].format(username)
    async with semaphore:
        try:
            async with session.get(
                url, headers=HEADERS,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                status = resp.status
                if status in cfg["available"]:
                    results.append((platform_name, username, "✅ AVAILABLE"))
                    return True
                elif status in cfg["taken"]:
                    results.append((platform_name, username, "❌ taken"))
                    return False
                else:
                    results.append((platform_name, username, f"⚠️  unknown ({status})"))
                    return None
        except asyncio.TimeoutError:
            results.append((platform_name, username, "⏱️  timeout"))
        except Exception as e:
            results.append((platform_name, username, f"💥 error: {e}"))
    return None

# ─────────────────────────────────────────────
#  DISCORD  (optional)
# ─────────────────────────────────────────────

async def check_discord(session, semaphore, username, results):
    try:
        token = DISCORD_TOKEN  # noqa
    except NameError:
        return

    discord_chars = set(L + U + D + UND + DOT)
    if not (2 <= len(username) <= 32):
        return
    if not all(c in discord_chars for c in username):
        return

    url = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
    headers = {**HEADERS, "Content-Type": "application/json",
               "Authorization": f"Bot {token}"}
    async with semaphore:
        try:
            async with session.post(
                url, json={"username": username}, headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                taken = data.get("taken", None)
                if taken is False:
                    results.append(("Discord", username, "✅ AVAILABLE"))
                elif taken is True:
                    results.append(("Discord", username, "❌ taken"))
                else:
                    results.append(("Discord", username, f"⚠️  {data}"))
        except Exception as e:
            results.append(("Discord", username, f"💥 error: {e}"))

# ─────────────────────────────────────────────
#  OUTPUT + STATS
# ─────────────────────────────────────────────

def print_result(platform, username, status):
    ts = datetime.now().strftime("%H:%M:%S")
    if "taken" not in status:  # suppress taken — too noisy
        print(f"[{ts}] {platform:<12} @{username:<10}  {status}")

def save_available(found):
    if not found:
        return
    with open(OUTPUT_FILE, "a") as f:
        for platform, username, _ in found:
            f.write(f"{platform}: @{username}\n")
    print(f"💾 Saved {len(found)} hits to {OUTPUT_FILE}")

class Stats:
    def __init__(self, total):
        self.total     = total
        self.checked   = 0
        self.available = 0
        self.start     = datetime.now()

    def update(self, results):
        self.checked   += 1
        self.available += sum(1 for _, _, s in results if "AVAILABLE" in s)

    def print_progress(self):
        elapsed   = (datetime.now() - self.start).total_seconds()
        rate      = self.checked / elapsed if elapsed > 0 else 0
        remaining = (self.total - self.checked) / rate if rate > 0 else 0
        pct       = self.checked / self.total * 100
        print(
            f"\n📊 {self.checked:,}/{self.total:,} ({pct:.1f}%) | "
            f"{rate:.1f} usernames/s | "
            f"Found: {self.available} | "
            f"ETA: {remaining/3600:.1f}h\n"
        )

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print(f"  🔍  Username Checker v2  —  Instance {INSTANCE_ID+1}/{TOTAL_INSTANCES}")
    print(f"  Lengths: {LENGTHS}  |  Platforms: {len(PLATFORMS)}")
    print()
    print(f"  {'Platform':<12}  {'Chars':<6}  {'Allowed characters'}")
    print(f"  {'-'*12}  {'-'*6}  {'-'*30}")
    for name, cfg in PLATFORMS.items():
        char_desc = ""
        chars = cfg["chars"]
        if any(c in chars for c in string.ascii_lowercase): char_desc += "a-z "
        if any(c in chars for c in string.ascii_uppercase): char_desc += "A-Z "
        if any(c in chars for c in string.digits):          char_desc += "0-9 "
        if "_" in chars: char_desc += "_ "
        if "." in chars: char_desc += ". "
        if "-" in chars: char_desc += "- "
        print(f"  {name:<12}  {len(chars):<6}  {char_desc.strip()}")
    print("=" * 60)

    usernames = generate_usernames(LENGTHS)
    chars_count = len(all_platform_chars())
    total_est = sum(chars_count ** l for l in LENGTHS) // TOTAL_INSTANCES
    stats = Stats(total_est)
    print(f"\n  Estimated usernames for this instance: ~{total_est:,}\n")
    print("  Checks are running — only non-taken results shown below.\n")

    semaphore = asyncio.Semaphore(CONCURRENT)
    available_buffer = []

    connector = aiohttp.TCPConnector(ssl=False, limit=CONCURRENT)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i, username in enumerate(usernames, 1):
            results = []
            tasks = [
                check_platform(session, semaphore, name, cfg, username, results)
                for name, cfg in PLATFORMS.items()
            ]
            tasks.append(check_discord(session, semaphore, username, results))
            await asyncio.gather(*tasks)

            stats.update(results)
            for platform, uname, status in results:
                print_result(platform, uname, status)
                if "AVAILABLE" in status:
                    available_buffer.append((platform, uname, status))

            if i % 50 == 0:
                save_available(available_buffer)
                available_buffer.clear()
                stats.print_progress()

            await asyncio.sleep(DELAY)

    save_available(available_buffer)
    print(f"\n✅ Done! Total available usernames found: {stats.available}")

if __name__ == "__main__":
    asyncio.run(main())
