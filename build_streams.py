import os
import re
import urllib.parse
import requests

# നിങ്ങളുടെ Cloudflare Worker URL
CF_WORKER = "https://mal-ml.xxjox.workers.dev"

# സോഴ്സ് ലിങ്ക്
SOURCE_URL = "https://premiumplugx.com/htt/hot.php?playlist=1"

# ഫിൽട്ടർ ചെയ്യേണ്ട കീവേഡുകൾ
KEYWORDS = ["asianet", "bigboss", "star sports"]

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace(" ", "_").replace("-", "_")
    return name.strip("_")

def main():
    os.makedirs("streams", exist_ok=True)
    
    headers = {
        "User-Agent": "Hotstar;in.startv.hotstar/25.02.24.8.11169@Premium Plugx(Android/15)"
    }
    
    print("Downloading playlist...")
    try:
        res = requests.get(SOURCE_URL, headers=headers, timeout=25)
        res.raise_for_status()
    except Exception as e:
        raise SystemExit(f"Fetch error: {e}")
        
    content = res.text
    blocks = content.split("#EXTINF:")
    
    combined_m3u = ["#EXTM3U\n"]
    
    for block in blocks:
        if not block.strip():
            continue
            
        full_block = "#EXTINF:" + block
        
        name_match = re.search(r',([^\r\n]+)', full_block)
        channel_name = name_match.group(1).strip() if name_match else "Unknown"
        channel_lower = channel_name.lower()
        
        if not any(k in channel_lower for k in KEYWORDS):
            continue
            
        logo_match = re.search(r'tvg-logo="([^"]+)"', full_block)
        group_match = re.search(r'group-title="([^"]+)"', full_block)
        cookie_match = re.search(r'http-cookie=([^\r\n]+)', full_block)
        ua_match = re.search(r'http-user-agent=([^\r\n]+)', full_block)
        key_match = re.search(r'license_key=([^\r\n]+)', full_block)
        
        url_match = re.search(r'(https?://[^\r\n?|]+(?:\.m3u8|\.mpd))', full_block)
        if not url_match:
            continue
            
        stream_url = url_match.group(1).strip()
        cookie = cookie_match.group(1).strip() if cookie_match else ""
        ua = ua_match.group(1).strip() if ua_match else "Hotstar;in.startv.hotstar"
        logo = logo_match.group(1) if logo_match else ""
        group = group_match.group(1) if group_match else "Entertainment"
        
        file_name = sanitize_filename(channel_name)
        
        # 1. HLS (.m3u8) ചാനലുകൾ (Bigg Boss മുതലായവ)
        if stream_url.endswith(".m3u8"):
            encoded_url = urllib.parse.quote(stream_url, safe="")
            encoded_cookie = urllib.parse.quote(cookie, safe="")
            encoded_ua = urllib.parse.quote(ua, safe="")
            
            worker_stream_link = f"{CF_WORKER}/?url={encoded_url}&cookie={encoded_cookie}&ua={encoded_ua}"
            
            m3u8_payload = (
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720\n"
                f"{worker_stream_link}\n"
            )
            
            with open(f"streams/{file_name}.m3u8", "w", encoding="utf-8") as f:
                f.write(m3u8_payload)
                
            combined_m3u.append(
                f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{group}",{channel_name}\n'
                f'{worker_stream_link}\n'
            )
            print(f"[HLS Generated] streams/{file_name}.m3u8")
            
        # 2. DASH (.mpd) ചാനലുകൾ (Asianet, Star Sports മുതലായവ)
        elif stream_url.endswith(".mpd"):
            clearkey = key_match.group(1).strip() if key_match else ""
            pipe_url = f"{stream_url}|cookie={cookie}&referer=https://www.hotstar.com/&origin=https://www.hotstar.com&user-agent={ua}"
            
            combined_m3u.append(
                f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo}" group-title="{group}",{channel_name}\n'
                f'#KODIPROP:inputstream=inputstream.adaptive\n'
                f'#KODIPROP:inputstream.adaptive.manifest_type=mpd\n'
                f'#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                f'#KODIPROP:inputstream.adaptive.license_key={clearkey}\n'
                f'{pipe_url}\n'
            )
            print(f"[MPD Added] {channel_name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.writelines(combined_m3u)
    print("Completed!")

if __name__ == "__main__":
    main()
