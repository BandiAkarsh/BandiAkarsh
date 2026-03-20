#!/usr/bin/env python3
"""
Generate languages.svg using GitHub's own language data via API.
"""

import subprocess
import urllib.request
import urllib.error
import json
import os
import time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = os.environ.get("GITHUB_USER", "BandiAkarsh")
OUTPUT_FILE = "profile/languages.svg"

COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
]


def api_request(url, max_retries=3):
    """Make API request with detailed error handling."""
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN is not set!")
        return None
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "GitHub-Languages-Stats"
    }
    
    print(f"   → {url[:60]}...")
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                print(f"   ✓ OK ({len(data)} items)")
                return data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()[:300]
            print(f"   ❌ HTTP {e.code}: {e.reason}")
            
            if e.code == 403:
                if "rate limit" in error_body.lower():
                    print(f"   Rate limited, waiting 60s...")
                    time.sleep(60)
                    continue
                print(f"   Permission denied: {error_body[:100]}")
                return None
            elif e.code == 401:
                print(f"   ❌ Unauthorized - check GITHUB_TOKEN")
                return None
            return None
                
        except Exception as e:
            print(f"   Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    return None


def get_repo_languages():
    """Fetch language data from GitHub's API."""
    all_languages = {}
    
    print(f"\n🚀 Fetching repos for {GITHUB_USER}...")
    
    # Verify token first
    print("   Verifying token...")
    test_data = api_request(f"https://api.github.com/users/{GITHUB_USER}")
    if test_data is None:
        print("   ❌ Cannot access GitHub API")
        print("   Make sure GITHUB_TOKEN has 'repo' scope for private repos")
        return {}
    print(f"   ✓ Authenticated as: {test_data.get('login', GITHUB_USER)}")
    
    page = 1
    per_page = 100
    total_repos = 0
    
    while True:
        print(f"\n   Page {page}:")
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page={per_page}&page={page}&type=all&sort=pushed"
        repos = api_request(url)
        
        if repos is None:
            print("   ❌ Failed to fetch repos")
            break
        
        if not repos:
            print("   No more repos found")
            break
        
        for repo in repos:
            if repo.get("fork"):
                continue
            
            total_repos += 1
            repo_name = repo["name"]
            print(f"\n   📦 {repo_name}")
            
            lang_url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/languages"
            languages = api_request(lang_url)
            
            if languages:
                for lang, bytes_count in languages.items():
                    all_languages[lang] = all_languages.get(lang, 0) + bytes_count
                print(f"      Languages: {', '.join(languages.keys())}")
            else:
                print(f"      No language data")
            
            time.sleep(0.5)
        
        if len(repos) < per_page:
            break
        page += 1
        if page > 10:
            break
    
    print(f"\n📊 Processed {total_repos} repos, {len(all_languages)} languages")
    return all_languages


def generate_svg(language_counts):
    """Generate SVG bar chart."""
    if not language_counts:
        print("❌ No language data!")
        return False
    
    sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    total = sum(c for _, c in sorted_langs)
    
    if total == 0:
        print("❌ Total is 0!")
        return False
    
    w, h = 600, 350
    bh, bg = 24, 6
    lw = 120
    bw = w - lw - 100
    
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">',
        '<defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        '<stop offset="0%" style="stop-color:#1a1a2e"/>',
        '<stop offset="100%" style="stop-color:#16213e"/></linearGradient></defs>',
        f'<rect width="{w}" height="{h}" fill="url(#bg)" rx="10"/>',
        '<text x="20" y="35" font-family="Arial,sans-serif" font-size="18" font-weight="bold" fill="#e0e0e0">Top Languages</text>',
        '<text x="20" y="55" font-family="Arial,sans-serif" font-size="11" fill="#888">by bytes (GitHub Linguist)</text>',
    ]
    
    y = 80
    for idx, (lang, bc) in enumerate(sorted_langs):
        pct = (bc / total) * 100
        bar_w = (bc / sorted_langs[0][1]) * bw
        color = COLORS[idx % len(COLORS)]
        cnt = f"{bc/1000000:.1f}M" if bc >= 1000000 else f"{bc/1000:.1f}K" if bc >= 1000 else str(bc)
        
        svg.extend([
            f'<text x="20" y="{y+17}" font-family="Arial,sans-serif" font-size="12" fill="#e0e0e0">{lang}</text>',
            f'<rect x="{lw}" y="{y}" width="{bar_w}" height="{bh}" fill="{color}" rx="4"/>',
            f'<text x="{lw+bar_w+8}" y="{y+17}" font-family="Arial,sans-serif" font-size="11" fill="#888">{cnt} ({pct:.1f}%)</text>',
        ])
        y += bh + bg
    
    svg.append(f'<text x="20" y="{y+20}" font-family="Arial,sans-serif" font-size="10" fill="#666">Total: {total:,} bytes</text>')
    svg.append("</svg>")
    
    os.makedirs("profile", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(svg))
    
    print(f"\n✅ Generated {OUTPUT_FILE}")
    for lang, bc in sorted_langs[:5]:
        print(f"   {lang}: {bc:,} bytes ({(bc/total)*100:.1f}%)")
    return True


def commit_changes():
    if not os.path.exists(OUTPUT_FILE):
        return
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"], check=True, capture_output=True)
            subprocess.run(["git", "add", OUTPUT_FILE], check=True, capture_output=True)
            r = subprocess.run(["git", "commit", "-m", "📊 Update language stats"], capture_output=True, text=True)
            if r.returncode == 0:
                subprocess.run(["git", "push"], check=False, capture_output=True)
                print("✅ Pushed to GitHub")
            else:
                print(f"Commit note: {r.stderr}")
        except Exception as e:
            print(f"Git error: {e}")


def main():
    print("=" * 50)
    print("GitHub Language Stats Generator")
    print("=" * 50)
    print(f"User: {GITHUB_USER}")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not set - must run in GitHub Actions")
        return
    
    language_counts = get_repo_languages()
    success = generate_svg(language_counts)
    if success:
        commit_changes()


if __name__ == "__main__":
    main()
