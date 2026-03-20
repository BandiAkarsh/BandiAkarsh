#!/usr/bin/env python3
"""
Generate languages.svg using GitHub's own language data via API.
This matches exactly what GitHub shows on each repo's language bar.
"""

import subprocess
import urllib.request
import urllib.error
import json
import os
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USER = os.environ.get("GITHUB_USER", "BandiAkarsh")
OUTPUT_FILE = "profile/languages.svg"

# Cyberpunk color palette
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


def api_request(url):
    """Make API request to GitHub."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "GitHub-Languages-Stats"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"API Error: {e}")
        return None


def get_repo_languages():
    """
    Fetch language data from GitHub's API.
    This uses GitHub's own Linguist analysis, matching what you see on repo pages.
    """
    all_languages = defaultdict(int)
    page = 1
    per_page = 100
    
    print(f"Fetching language data from GitHub API for {GITHUB_USER}...")
    
    while True:
        # Get user's repos
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page={per_page}&page={page}&type=all&sort=pushed"
        repos = api_request(url)
        
        if repos is None:
            break
        
        if not repos:
            break
        
        for repo in repos:
            if repo.get("fork"):
                continue
            
            repo_name = repo["name"]
            print(f"  Fetching languages for {repo_name}...")
            
            # Get languages for this specific repo via GitHub API
            # This returns bytes per language, exactly like the repo language bar
            lang_url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/languages"
            languages = api_request(lang_url)
            
            if languages:
                for lang, bytes_count in languages.items():
                    all_languages[lang] += bytes_count
            else:
                print(f"    Could not fetch languages for {repo_name}")
            
            # Be nice to the API
            import time
            time.sleep(0.5)
        
        if len(repos) < per_page:
            break
        page += 1
        
        if page > 10:  # Safety limit
            break
    
    return all_languages


def generate_svg(language_counts):
    """Generate SVG bar chart for top languages."""
    if not language_counts:
        print("No language data found!")
        return False
    
    # Sort by bytes (GitHub's method), take top 10
    sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    total = sum(count for _, count in sorted_langs)
    
    if total == 0:
        print("Total bytes is 0!")
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
        '<text x="20" y="55" font-family="Arial,sans-serif" font-size="11" fill="#888">by bytes (GitHub Linguist)</text>',
    ]
    
    y = 80
    for idx, (lang, bytes_count) in enumerate(sorted_langs):
        percentage = (bytes_count / total) * 100
        bar_width = (bytes_count / sorted_langs[0][1]) * bar_max_width
        color = COLORS[idx % len(COLORS)]
        
        # Format bytes to human readable
        if bytes_count >= 1000000:
            count_str = f"{bytes_count/1000000:.1f}M"
        elif bytes_count >= 1000:
            count_str = f"{bytes_count/1000:.1f}K"
        else:
            count_str = str(bytes_count)
        
        svg_lines.extend([
            f'  <text x="20" y="{y+17}" font-family="Arial,sans-serif" font-size="12" fill="#e0e0e0">{lang}</text>',
            f'  <rect x="{label_width}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="4"/>',
            f'  <text x="{label_width + bar_width + 8}" y="{y+17}" font-family="Arial,sans-serif" font-size="11" fill="#888">{count_str} ({percentage:.1f}%)</text>',
        ])
        y += bar_height + bar_gap
    
    svg_lines.append(f'  <text x="20" y="{y+20}" font-family="Arial,sans-serif" font-size="10" fill="#666">Total: {total:,} bytes</text>')
    svg_lines.append("</svg>")
    
    os.makedirs("profile", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(svg_lines))
    
    print(f"\n✅ Generated {OUTPUT_FILE}")
    print(f"Top languages: {', '.join(l for l, _ in sorted_langs[:5])}")
    print(f"Full breakdown:")
    for lang, bytes_count in sorted_langs:
        pct = (bytes_count / total) * 100
        print(f"  {lang}: {bytes_count:,} bytes ({pct:.1f}%)")
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
    print(f"🚀 Generating language stats for {GITHUB_USER} (using GitHub API)...")
    
    language_counts = get_repo_languages()
    success = generate_svg(language_counts)
    
    if success:
        commit_changes()
    else:
        print("⚠️  Could not generate language stats")


if __name__ == "__main__":
    main()
