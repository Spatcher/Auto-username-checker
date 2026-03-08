"""
Username Availability Checker — v3
Checks usernames across major social media platforms.
Sends available usernames to Discord channels via embeds.
"""

import asyncio
import aiohttp
import itertools
import string
from datetime import datetime

# ─────────────────────────────────────────────
#  DISCORD CONFIG
# ─────────────────────────────────────────────

DISCORD_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

CHANNEL_IDS = {
    "GitHub":    000000000000000000,
    "TikTok":    000000000000000000,
    "YouTube":   000000000000000000,
    "Instagram": 000000000000000000,
    "Twitch":    000000000000000000,
    "Pinterest": 000000000000000000,
}

# ─────────────────────────────────────────────
#  MULTI-INSTANCE CONFIG
# ─────────────────────────────────────────────

INSTANCE_ID     = 0  # This machine's ID (0, 1, 2, 3 ...)
TOTAL_INSTANCES = 1  # Total machines running in parallel

# ─────────────────────────────────────────────
#  GENERAL CONFIG
# ─────────────────────────────────────────────

LENGTHS    = [4, 5]
DELAY      = 0.3
CONCURRENT = 10

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
#  PLATFORM COLORS FOR EMBEDS
# ─────────────────────────────────────────────

PLATFORM_META = {
    "GitHub":    {"color": 0x333333, "url": "https://github.com/{}",               "emoji": "🐙"},
    "TikTok":    {"color": 0x010101, "url": "https://www.tiktok.com/@{}",           "emoji": "🎵"},
    "YouTube":   {"color": 0xFF0000, "url": "https://www.youtube.com/@{}",          "emoji": "▶️"},
    "Instagram": {"color": 0xE1306C, "url": "https://www.instagram.com/{}/",        "emoji": "📸"},
    "Twitch":    {"color": 0x9146FF, "url": "https://www.twitch.tv/{}",             "emoji": "🎮"},
    "Pinterest": {"color": 0xE60023, "url": "https://www.pinterest.com/{}/",        "emoji": "📌"},
}

# ─────────────────────────────────────────────
#  PLATFORMS
# ─────────────────────────────────────────────

PLATFORMS = {
    "GitHub": {
        "url":       "https://api.github.com/users/{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + DAS,
        "min_len":   1,
        "max_len":   39,
        "no_leading_hyphen":  True,
        "no_trailing_hyphen": True,
        "no_double_hyphen":   True,
    },
    "TikTok": {
        "url":       "https://www.tiktok.com/@{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND + DOT,
        "min_len":   2,
        "max_len":   24,
        "no_leading_dot":         True,
        "no_trailing_dot":        True,
        "no_leading_underscore":  True,
        "no_trailing_underscore": True,
    },
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
    "Instagram": {
        "url":       "https://www.instagram.com/{}/",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND + DOT,
        "min_len":   1,
        "max_len":   30,
        "no_leading_dot":  True,
        "no_trailing_dot": True,
        "no_double_dot":   True,
    },
    "Twitch": {
        "url":       "https://www.twitch.tv/{}",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   4,
        "max_len":   25,
    },
    "Pinterest": {
        "url":       "https://www.pinterest.com/{}/",
        "available": [404],
        "taken":     [200],
        "chars":     L + U + D + UND,
        "min_len":   3,
        "max_len":   30,
    },
}

# ─────────────────────────────────────────────
#  USERNAME GENERATOR
# ─────────────────────────────────────────────

def all_platform_chars():
    chars = set()
    for p in PLATFORMS.values():
        chars.update(p["chars"])
    letters = [c for c in chars if c.isalpha()]
    digits  = [c for c in chars if c.isdigit()]
    special = [c for c in chars if not c.isalnum()]
    return "".join(sorted(letters) + sorted(digits) + sorted(special))

def generate_usernames(lengths):
    chars = all_platform_chars()
    index = 0
    for length in lengths:
        for combo in itertools.product(chars, repeat=length):
            if index % TOTAL_INSTANCES == INSTANCE_ID:
                yield "".join(combo)
            index += 1

def is_valid_for_platform(username, cfg):
    if len(username) < cfg["min_len"]:
        return False
    if cfg["max_len"] and len(username) > cfg["max_len"]:
        return False
    if not all(c in set(cfg["chars"]) for c in username):
        return False
    if cfg.get("no_leading_underscore")  and username.startswith("_"): return False
    if cfg.get("no_trailing_underscore") and username.endswith("_"):   return False
    if cfg.get("no_double_underscore")   and "__" in username:         return False
    if cfg.get("no_leading_hyphen")      and username.startswith("-"): return False
    if cfg.get("no_trailing_hyphen")     and username.endswith("-"):   return False
    if cfg.get("no_double_hyphen")       and "--" in username:         return False
    if cfg.get("no_leading_dot")         and username.startswith("."): return False
    if cfg.get("no_trailing_dot")        and username.endswith("."):   return False
    if cfg.get("no_double_dot")          and ".." in username:         return False
    return True

# ─────────────────────────────────────────────
#  HEADERS
# ─────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ─────────────────────────────────────────────
#  DISCORD NOTIFIER
# ─────────────────────────────────────────────

async def send_discord_embed(session, platform, username):
    channel_id = CHANNEL_IDS.get(platform)
    if not channel_id or channel_id == 0:
        return

    meta        = PLATFORM_META[platform]
    profile_url = meta["url"].format(username)
    emoji       = meta["emoji"]
    color       = meta["color"]

    embed = {
        "title":       f"{emoji} Available Username Found!",
        "description": f"**@{username}** is available on **{platform}**",
        "color":       color,
        "fields": [
            {"name": "Platform", "value": platform,      "inline": True},
            {"name": "Username", "value": f"`@{username}`", "inline": True},
            {"name": "Link",     "value": profile_url,   "inline": False},
        ],
        "footer": {"text": f"Username Checker • Instance {INSTANCE_ID + 1}/{TOTAL_INSTANCES}"},
        "timestamp": datetime.utcnow().isoformat(),
    }

    url     = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type":  "application/json",
    }

    try:
        async with session.post(url, json={"embeds": [embed]}, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                print(f"  ⚠️  Discord send failed ({resp.status}): {text[:100]}")
    except Exception as e:
        print(f"  💥 Discord error: {e}")

# ─────────────────────────────────────────────
#  CHECKER
# ─────────────────────────────────────────────

async def check_platform(session, semaphore, platform_name, cfg, username, results):
    if not is_valid_for_platform(username, cfg):
        return None

    url = cfg["url"].format(username)
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS, allow_redirects=True,
                                   timeout=aiohttp.ClientTimeout(total=5)) as resp:
                status = resp.status
                if status in cfg["available"]:
                    results.append((platform_name, username, "✅ AVAILABLE"))
                    return True
                elif status in cfg["taken"]:
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
#  STATS
# ─────────────────────────────────────────────

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
            f"{rate:.1f}/s | "
            f"Found: {self.available} | "
            f"ETA: {remaining/3600:.1f}h\n"
        )

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

async def main():
    print("=" * 60)
    print(f"  🔍  Username Checker v3  —  Instance {INSTANCE_ID+1}/{TOTAL_INSTANCES}")
    print(f"  Lengths: {LENGTHS}  |  Platforms: {len(PLATFORMS)}")
    print()
    print(f"  {'Platform':<12}  {'Chars':<6}  {'Allowed characters'}")
    print(f"  {'-'*12}  {'-'*6}  {'-'*30}")
    for name, cfg in PLATFORMS.items():
        chars = cfg["chars"]
        char_desc = ""
        if any(c in chars for c in string.ascii_lowercase): char_desc += "a-z "
        if any(c in chars for c in string.ascii_uppercase): char_desc += "A-Z "
        if any(c in chars for c in string.digits):          char_desc += "0-9 "
        if "_" in chars: char_desc += "_ "
        if "." in chars: char_desc += ". "
        if "-" in chars: char_desc += "- "
        print(f"  {name:<12}  {len(chars):<6}  {char_desc.strip()}")
    print("=" * 60)

    chars_count = len(all_platform_chars())
    total_est   = sum(chars_count ** l for l in LENGTHS) // TOTAL_INSTANCES
    stats       = Stats(total_est)
    print(f"\n  Estimated usernames for this instance: ~{total_est:,}")
    print(f"  Results will be sent to Discord channels.\n")

    semaphore = asyncio.Semaphore(CONCURRENT)
    connector = aiohttp.TCPConnector(ssl=False, limit=CONCURRENT)

    async with aiohttp.ClientSession(connector=connector) as session:
        for i, username in enumerate(generate_usernames(LENGTHS), 1):
            results = []
            tasks   = [
                check_platform(session, semaphore, name, cfg, username, results)
                for name, cfg in PLATFORMS.items()
            ]
            await asyncio.gather(*tasks)

            stats.update(results)

            for platform, uname, status in results:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] {platform:<12} @{uname:<10}  {status}")
                if "AVAILABLE" in status:
                    await send_discord_embed(session, platform, uname)

            if i % 50 == 0:
                stats.print_progress()

            await asyncio.sleep(DELAY)

    print(f"\n✅ Done! Total available usernames found: {stats.available}")

if __name__ == "__main__":
    asyncio.run(main())
