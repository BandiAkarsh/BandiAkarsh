#!/usr/bin/env python3
"""
Generate languages.svg showing top languages by lines of code across all repos.
Uses GitHub API to get repos, clones them, and counts with cloc.
"""

import subprocess
import urllib.request
import urllib.error
import json
import os
from collections import defaultdict
import time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USER = os.environ.get("GITHUB_USER", "BandiAkarsh")
OUTPUT_FILE = "profile/languages.svg"

# Color palette for language bars (synthwave/cyberpunk theme)
COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Purple
    "#85C1E9",  # Sky
]


def api_request(url, retries=3):
    """Make API request with retry logic for rate limits."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "GitHub-Languages-Stats"
    }
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    return json.loads(response.read().decode())
                elif response.status == 403:
                    print(f"Rate limited, waiting 60s... (attempt {attempt+1}/{retries})")
                    time.sleep(60)
                else:
                    print(f"API returned status {response.status}")
                    return None
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"HTTP 403: Rate limit or permission issue. Waiting 60s...")
                time.sleep(60)
            else:
                print(f"HTTP Error: {e}")
                return None
        except Exception as e:
            print(f"Request error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None


def get_repos():
    """Fetch all repos for the user via GitHub API."""
    repos = []
    page = 1
    per_page = 100
    
    print(f"Fetching repos for {GITHUB_USER}...")
    
    while True:
        # Use /users/{username}/repos endpoint (works with PAT)
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page={per_page}&page={page}&type=all&sort=pushed"
        data = api_request(url)
        
        if data is None:
            print("Failed to fetch repos, trying alternative endpoint...")
            # Fallback to /user/repos
            url = f"https://api.github.com/user/repos?per_page={per_page}&page={page}&sort=pushed"
            data = api_request(url)
            if data is None:
                break
        
        if not data:
            break
            
        for repo in data:
            if repo.get("fork", False):
                continue
            repos.append({
                "name": repo["name"],
                "clone_url": repo["clone_url"]
            })
        
        print(f"  Page {page}: found {len(data)} repos")
        
        if len(data) < per_page:
            break
        page += 1
        
        # Safety limit
        if page > 10:
            break
    
    print(f"Total repos to analyze: {len(repos)}")
    return repos


def count_languages():
    """Clone repos and count lines per language using cloc."""
    language_counts = defaultdict(int)
    repos = get_repos()
    
    if not repos:
        print("No repos found!")
        return language_counts
    
    for i, repo in enumerate(repos):
        repo_name = repo["name"]
        clone_url = repo["clone_url"]
        print(f"[{i+1}/{len(repos)}] Processing {repo_name}...")
        
        # Use token for cloning
        auth_url = clone_url.replace("https://", f"https://{GITHUB_TOKEN}@")
        clone_dir = f"/tmp/repo_{i}"
        
        try:
            # Clone repo
            result = subprocess.run(
                ["git", "clone", "--depth", "1", auth_url, clone_dir],
                capture_output=True, text=True, timeout=120, check=False
            )
            
            if result.returncode != 0:
                print(f"  Clone failed: {result.stderr[:100] if result.stderr else 'unknown'}")
                continue
            
            # Count with cloc
            result = subprocess.run(
                ["cloc", "--json", clone_dir],
                capture_output=True, text=True, timeout=180
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for lang, info in data.items():
                        if isinstance(info, dict) and "code" in info:
                            language_counts[lang] += info["code"]
                except json.JSONDecodeError:
                    pass
                    
        except subprocess.TimeoutExpired:
            print(f"  Timeout processing {repo_name}")
        except Exception as e:
            print(f"  Error: {e}")
        finally:
            subprocess.run(["rm", "-rf", clone_dir], check=False)
    
    return language_counts


def generate_svg(language_counts):
    """Generate SVG bar chart for top languages."""
    if not language_counts:
        print("No language data found!")
        return False
    
    sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    total = sum(count for _, count in sorted_langs)
    
    if total == 0:
        print("Total lines is 0!")
        return False
    
    # SVG dimensions
    width = 600
    height = 350
    bar_height = 24
    bar_gap = 6
    label_width = 120
    bar_max_width = width - label_width - 90
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<defs>',
        '  <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        '    <stop offset="0%" style="stop-color:#1a1a2e"/>',
        '    <stop offset="100%" style="stop-color:#16213e"/>',
        '  </linearGradient>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="url(#bg)" rx="10"/>',
        '<text x="20" y="35" font-family="Arial,sans-serif" font-size="18" font-weight="bold" fill="#e0e0e0">Top Languages</text>',
        '<text x="20" y="55" font-family="Arial,sans-serif" font-size="11" fill="#888">by lines of code</text>',
    ]
    
    y = 80
    for idx, (lang, count) in enumerate(sorted_langs):
        bar_width = (count / sorted_langs[0][1]) * bar_max_width
        color = COLORS[idx % len(COLORS)]
        
        if count >= 1000000:
            count_str = f"{count/1000000:.1f}M"
        elif count >= 1000:
            count_str = f"{count/1000:.1f}K"
        else:
            count_str = str(count)
        
        svg_lines.extend([
            f'  <text x="20" y="{y+17}" font-family="Arial,sans-serif" font-size="12" fill="#e0e0e0">{lang}</text>',
            f'  <rect x="{label_width}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="4"/>',
            f'  <text x="{label_width + bar_width + 8}" y="{y+17}" font-family="Arial,sans-serif" font-size="11" fill="#888">{count_str}</text>',
        ])
        y += bar_height + bar_gap
    
    svg_lines.append(f'  <text x="20" y="{y+20}" font-family="Arial,sans-serif" font-size="10" fill="#666">Total: {total:,} lines</text>')
    svg_lines.append("</svg>")
    
    os.makedirs("profile", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(svg_lines))
    
    print(f"\n✅ Generated {OUTPUT_FILE}")
    print(f"Top languages: {', '.join(l for l, _ in sorted_langs[:5])}")
    return True


def commit_changes():
    """Commit and push changes if file exists."""
    if not os.path.exists(OUTPUT_FILE):
        print("No file to commit")
        return
    
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True, capture_output=True)
            subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"], check=True, capture_output=True)
            subprocess.run(["git", "add", OUTPUT_FILE], check=True, capture_output=True)
            result = subprocess.run(["git", "commit", "-m", "📊 Update language stats"], capture_output=True, text=True)
            if result.returncode == 0:
                subprocess.run(["git", "push"], check=False, capture_output=True)
                print("✅ Pushed changes to GitHub")
            else:
                print(f"Commit note: {result.stderr}")
        except Exception as e:
            print(f"Git error (non-critical): {e}")


def main():
    print(f"🚀 Generating language stats for {GITHUB_USER}...")
    
    language_counts = count_languages()
    success = generate_svg(language_counts)
    
    if success:
        commit_changes()
    else:
        print("⚠️  Could not generate language stats")


if __name__ == "__main__":
    main()
