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
import base64
from collections import defaultdict

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


def get_repos():
    """Fetch all repos for the user via GitHub API."""
    repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/user/repos?per_page={per_page}&page={page}&sort=pushed"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_TOKEN}"
        }
        
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                repos.extend([r["clone_url"] for r in data if not r.get("fork", False)])
                if len(data) < per_page:
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching repos: {e}")
            break
    
    return repos


def count_languages():
    """Clone repos and count lines per language using cloc."""
    language_counts = defaultdict(int)
    repos = get_repos()
    
    print(f"Found {len(repos)} repos to analyze")
    
    for i, repo_url in enumerate(repos):
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        print(f"[{i+1}/{len(repos)}] Processing {repo_name}...")
        
        # Use token for private repos
        auth_url = repo_url.replace(
            "https://", f"https://{GITHUB_TOKEN}@"
        )
        
        clone_dir = f"/tmp/repo_{i}"
        
        try:
            # Clone repo
            subprocess.run(
                ["git", "clone", "--depth", "1", auth_url, clone_dir],
                capture_output=True, timeout=60, check=False
            )
            
            # Count with cloc
            result = subprocess.run(
                ["cloc", "--json", clone_dir],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for lang, info in data.items():
                        if isinstance(info, dict) and "code" in info:
                            language_counts[lang] += info["code"]
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"  Error: {e}")
        finally:
            # Cleanup
            subprocess.run(["rm", "-rf", clone_dir], check=False)
    
    return language_counts


def generate_svg(language_counts):
    """Generate SVG bar chart for top languages."""
    if not language_counts:
        print("No language data found!")
        return
    
    # Sort by lines, take top 10
    sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    total = sum(count for _, count in sorted_langs)
    
    # SVG dimensions
    width = 600
    height = 300
    bar_height = 24
    bar_gap = 6
    label_width = 120
    bar_max_width = width - label_width - 80
    
    # Build SVG
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
    for i, (lang, count) in enumerate(sorted_langs):
        percentage = (count / total) * 100
        bar_width = (count / sorted_langs[0][1]) * bar_max_width
        color = COLORS[i % len(COLORS)]
        
        # Format count
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
    
    svg_lines.append("</svg>")
    
    # Write to file
    os.makedirs("profile", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(svg_lines))
    
    print(f"\nGenerated {OUTPUT_FILE}")
    print(f"Top languages: {', '.join(l for l, _ in sorted_langs[:5])}")


def main():
    print(f"Generating language stats for {GITHUB_USER}...")
    
    language_counts = count_languages()
    generate_svg(language_counts)
    
    # Commit if in CI
    if os.environ.get("GITHUB_ACTIONS") == "true":
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"], check=True)
        subprocess.run(["git", "add", OUTPUT_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "📊 Update language stats"], check=False)
        subprocess.run(["git", "push"], check=False)


if __name__ == "__main__":
    main()
