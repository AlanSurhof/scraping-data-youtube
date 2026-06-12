"""
KDM YouTube Channel — Analytics Scraper per Provinsi Indonesia
==============================================================
REAL-TIME menggunakan YouTube Data API v3 + YouTube Analytics API v2

Cara penggunaan:
  1. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  2. Aktifkan YouTube Data API v3 & YouTube Analytics API di Google Cloud Console
  3. Buat OAuth 2.0 credentials (Desktop App) → download sebagai client_secret.json
  4. Jalankan: python kdm_scraper.py

Output: data_provinsi_YYYY-MM.json (siap diupload ke dashboard HTML)

CATATAN:
  - API_KEY digunakan untuk data publik (channel info, video stats)
  - OAuth diperlukan untuk YouTube Analytics API (distribusi provinsi, watch time)
  - Jika OAuth tidak tersedia, distribusi provinsi dihitung dari bobot demografis Indonesia
"""

import os
import json
import datetime
import calendar
import pickle
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
#  KONFIGURASI REAL — GANTI SESUAI CHANNEL
# ══════════════════════════════════════════════════════════════════
API_KEY      = "AIzaSyCuOM3XVAkGRKA95iJEJbHruexW38IpRg8"   # ← YouTube Data API v3 Key
CHANNEL_ID   = "UCopjJE-RzBmv4MID-E1Oiyg"                  # ← KDM Channel ID
CLIENT_SECRET = "client_secret.json"   # OAuth credentials (untuk Analytics API)
TOKEN_FILE    = "token.pickle"
OUTPUT_DIR    = "output_data"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# ══════════════════════════════════════════════════════════════════
#  MAPPING PROVINSI
# ══════════════════════════════════════════════════════════════════
PROVINCE_MAP = {
    "ID-AC": "Aceh",           "ID-BA": "Bali",
    "ID-BB": "Bangka Belitung","ID-BT": "Banten",
    "ID-BE": "Bengkulu",       "ID-JT": "Jawa Tengah",
    "ID-JI": "Jawa Timur",     "ID-JK": "DKI Jakarta",
    "ID-JB": "Jawa Barat",     "ID-JA": "Jambi",
    "ID-KB": "Kalimantan Barat","ID-KS": "Kalimantan Selatan",
    "ID-KT": "Kalimantan Tengah","ID-KI": "Kalimantan Timur",
    "ID-KU": "Kalimantan Utara","ID-KR": "Kepulauan Riau",
    "ID-LA": "Lampung",        "ID-MA": "Maluku",
    "ID-MU": "Maluku Utara",   "ID-NB": "Nusa Tenggara Barat",
    "ID-NT": "Nusa Tenggara Timur","ID-PA": "Papua",
    "ID-PB": "Papua Barat",    "ID-PS": "Papua Selatan",
    "ID-PT": "Papua Tengah",   "ID-PE": "Papua Pegunungan",
    "ID-RI": "Riau",           "ID-SR": "Sulawesi Barat",
    "ID-SN": "Sulawesi Selatan","ID-ST": "Sulawesi Tengah",
    "ID-SG": "Gorontalo",      "ID-SA": "Sulawesi Utara",
    "ID-SE": "Sulawesi Tenggara","ID-SB": "Sumatera Barat",
    "ID-SS": "Sumatera Selatan","ID-SU": "Sumatera Utara",
    "ID-YO": "DI Yogyakarta",
}

ISLAND_MAP = {
    "Aceh":"Sumatera","Sumatera Utara":"Sumatera","Sumatera Barat":"Sumatera",
    "Riau":"Sumatera","Kepulauan Riau":"Sumatera","Jambi":"Sumatera",
    "Bengkulu":"Sumatera","Sumatera Selatan":"Sumatera",
    "Bangka Belitung":"Sumatera","Lampung":"Sumatera",
    "DKI Jakarta":"Jawa","Jawa Barat":"Jawa","Banten":"Jawa",
    "Jawa Tengah":"Jawa","DI Yogyakarta":"Jawa","Jawa Timur":"Jawa",
    "Kalimantan Barat":"Kalimantan","Kalimantan Tengah":"Kalimantan",
    "Kalimantan Selatan":"Kalimantan","Kalimantan Timur":"Kalimantan",
    "Kalimantan Utara":"Kalimantan",
    "Sulawesi Utara":"Sulawesi","Gorontalo":"Sulawesi","Sulawesi Tengah":"Sulawesi",
    "Sulawesi Barat":"Sulawesi","Sulawesi Selatan":"Sulawesi","Sulawesi Tenggara":"Sulawesi",
    "Bali":"Bali & NTT","Nusa Tenggara Barat":"Bali & NTT","Nusa Tenggara Timur":"Bali & NTT",
    "Maluku":"Maluku","Maluku Utara":"Maluku",
    "Papua Barat":"Papua","Papua":"Papua","Papua Selatan":"Papua",
    "Papua Tengah":"Papua","Papua Pegunungan":"Papua",
}

# Bobot distribusi internet Indonesia (BPS 2024 + Hootsuite Digital 2024)
# Disesuaikan dengan karakteristik konten channel
DEMOGRAPHIC_WEIGHTS = {
    "Jawa Barat":17.8,"Jawa Tengah":13.7,"Jawa Timur":12.6,"DKI Jakarta":11.1,
    "Banten":5.5,"DI Yogyakarta":4.6,"Sumatera Utara":5.8,"Sumatera Selatan":3.5,
    "Riau":3.2,"Sumatera Barat":2.9,"Lampung":2.7,"Aceh":1.9,
    "Kepulauan Riau":1.6,"Jambi":1.4,"Bengkulu":0.7,"Bangka Belitung":0.8,
    "Kalimantan Timur":2.5,"Kalimantan Selatan":2.0,"Kalimantan Barat":1.8,
    "Kalimantan Tengah":1.3,"Kalimantan Utara":0.6,"Sulawesi Selatan":3.8,
    "Sulawesi Tengah":1.4,"Sulawesi Utara":1.0,"Sulawesi Tenggara":1.0,
    "Gorontalo":0.6,"Sulawesi Barat":0.5,"Bali":2.2,
    "Nusa Tenggara Barat":1.5,"Nusa Tenggara Timur":0.9,
    "Papua":0.9,"Papua Barat":0.4,"Papua Selatan":0.26,
    "Papua Tengah":0.22,"Papua Pegunungan":0.20,
    "Maluku":0.75,"Maluku Utara":0.47,
}

WATCH_TIME_BASE = {
    "Jawa Barat":18.4,"Jawa Tengah":17.1,"Jawa Timur":16.8,"DKI Jakarta":19.2,
    "Banten":14.9,"DI Yogyakarta":20.1,"Sumatera Utara":15.6,"Sumatera Selatan":14.2,
    "Riau":13.8,"Sumatera Barat":14.5,"Lampung":13.1,"Aceh":12.9,
    "Kepulauan Riau":14.1,"Jambi":13.0,"Bengkulu":12.1,"Bangka Belitung":12.6,
    "Kalimantan Timur":15.3,"Kalimantan Selatan":13.7,"Kalimantan Barat":12.8,
    "Kalimantan Tengah":12.5,"Kalimantan Utara":12.0,"Sulawesi Selatan":16.1,
    "Sulawesi Tengah":12.4,"Sulawesi Utara":13.2,"Sulawesi Tenggara":12.7,
    "Gorontalo":11.9,"Sulawesi Barat":11.6,"Bali":17.8,
    "Nusa Tenggara Barat":13.5,"Nusa Tenggara Timur":12.3,"Papua":11.8,
    "Papua Barat":11.2,"Papua Selatan":10.8,"Papua Tengah":10.5,
    "Papua Pegunungan":10.3,"Maluku":11.5,"Maluku Utara":11.4,
}

# ══════════════════════════════════════════════════════════════════
#  AUTENTIKASI OAUTH (untuk YouTube Analytics API)
# ══════════════════════════════════════════════════════════════════
def get_oauth_services():
    """Autentikasi OAuth untuk akses YouTube Analytics API."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  Merefresh token OAuth...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                raise FileNotFoundError(
                    f"File '{CLIENT_SECRET}' tidak ditemukan.\n"
                    "  Download dari Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client"
                )
            print("  Membuka browser untuk otorisasi OAuth...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        print("  ✓ Token tersimpan")

    yt_data     = build("youtube",         "v3",  credentials=creds)
    yt_analytics = build("youtubeAnalytics","v2", credentials=creds)
    return yt_data, yt_analytics


def get_api_key_service():
    """Service YouTube Data API menggunakan API Key (tanpa OAuth)."""
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=API_KEY)


# ══════════════════════════════════════════════════════════════════
#  CHANNEL INFO (REAL — API KEY)
# ══════════════════════════════════════════════════════════════════
def fetch_channel_info(use_oauth: bool = False):
    """
    Ambil info channel secara real-time menggunakan YouTube Data API v3.
    Menggunakan API Key (tidak perlu OAuth) karena data channel bersifat publik.
    """
    print("  [REAL] Mengambil info channel dari YouTube Data API...")
    svc = get_api_key_service()
    resp = svc.channels().list(
        part="snippet,statistics,brandingSettings,contentDetails",
        id=CHANNEL_ID,
    ).execute()

    if not resp.get("items"):
        raise ValueError(f"Channel ID tidak ditemukan: {CHANNEL_ID}")

    item = resp["items"][0]
    stats = item.get("statistics", {})

    info = {
        "channel_id":       CHANNEL_ID,
        "channel_name":     item["snippet"]["title"],
        "description":      item["snippet"].get("description", "")[:200],
        "country":          item["snippet"].get("country", "ID"),
        "published_at":     item["snippet"].get("publishedAt", ""),
        "thumbnail":        item["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "view_count":       int(stats.get("viewCount", 0)),
        "video_count":      int(stats.get("videoCount", 0)),
        "hidden_subscriber": stats.get("hiddenSubscriberCount", False),
        "uploads_playlist": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
    }
    print(f"  ✓ Channel : {info['channel_name']}")
    print(f"  ✓ Subs    : {info['subscriber_count']:,}" if not info['hidden_subscriber'] else "  ✓ Subs    : [Tersembunyi]")
    print(f"  ✓ Views   : {info['view_count']:,}")
    print(f"  ✓ Video   : {info['video_count']:,}")
    return info


# ══════════════════════════════════════════════════════════════════
#  VIDEO STATS (REAL — API KEY)
# ══════════════════════════════════════════════════════════════════
def fetch_recent_videos(uploads_playlist_id: str, max_results: int = 50):
    """
    Ambil statistik video terbaru dari channel secara real-time.
    Menggunakan YouTube Data API v3 dengan API Key.
    """
    print(f"  [REAL] Mengambil {max_results} video terbaru...")
    svc = get_api_key_service()

    # 1. Ambil playlist items
    pl_resp = svc.playlistItems().list(
        part="contentDetails,snippet",
        playlistId=uploads_playlist_id,
        maxResults=max_results,
    ).execute()

    items = pl_resp.get("items", [])
    if not items:
        print("  [WARN] Tidak ada video ditemukan")
        return []

    video_ids = [i["contentDetails"]["videoId"] for i in items]
    print(f"  ✓ Ditemukan {len(video_ids)} video")

    # 2. Ambil statistik tiap video (batch 50 per request)
    all_videos = []
    for i in range(0, len(video_ids), 50):
        batch = ",".join(video_ids[i:i+50])
        v_resp = svc.videos().list(
            part="snippet,statistics,contentDetails",
            id=batch,
        ).execute()
        all_videos.extend(v_resp.get("items", []))

    # Format output
    result = []
    for v in all_videos:
        stats = v.get("statistics", {})
        snip  = v.get("snippet", {})
        result.append({
            "video_id":       v["id"],
            "title":          snip.get("title", ""),
            "published_at":   snip.get("publishedAt", ""),
            "thumbnail":      snip.get("thumbnails", {}).get("medium", {}).get("url", ""),
            "duration":       v.get("contentDetails", {}).get("duration", ""),
            "views":          int(stats.get("viewCount", 0)),
            "likes":          int(stats.get("likeCount", 0)),
            "comments":       int(stats.get("commentCount", 0)),
            "description":    snip.get("description", "")[:150],
        })

    result.sort(key=lambda x: x["published_at"], reverse=True)
    print(f"  ✓ Statistik video berhasil diambil")
    return result


# ══════════════════════════════════════════════════════════════════
#  PROVINCE DATA — ANALYTICS API (REAL, perlu OAuth)
# ══════════════════════════════════════════════════════════════════
def fetch_province_analytics(yt_analytics, year: int, month: int):
    """
    Ambil data distribusi views per provinsi Indonesia menggunakan
    YouTube Analytics API v2 (memerlukan OAuth dari pemilik channel).

    Mengembalikan list provinsi dengan views, watch time, dll.
    """
    start_date = f"{year}-{month:02d}-01"
    last_day   = calendar.monthrange(year, month)[1]
    end_date   = f"{year}-{month:02d}-{last_day:02d}"
    print(f"  [REAL Analytics] Mengambil data provinsi {start_date} → {end_date}...")

    try:
        resp = yt_analytics.reports().query(
            ids=f"channel=={CHANNEL_ID}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
            dimensions="province",
            filters="country==ID",
            sort="-views",
        ).execute()
    except Exception as e:
        print(f"  [WARN] YouTube Analytics API error: {e}")
        return None   # Caller akan fallback ke estimasi demografis

    rows = resp.get("rows", [])
    if not rows:
        print("  [WARN] Tidak ada data baris provinsi dari Analytics API")
        return None

    total_views = sum(int(r[1]) for r in rows)
    result = []
    for row in rows:
        code  = row[0]
        views = int(row[1])
        wm    = float(row[2]) if len(row) > 2 else 0
        avg_d = float(row[3]) if len(row) > 3 else 0
        avg_p = float(row[4]) if len(row) > 4 else 0
        name  = PROVINCE_MAP.get(code, code)
        island= ISLAND_MAP.get(name, "Lainnya")
        result.append({
            "province_code":     code,
            "name":              name,
            "island":            island,
            "views":             views,
            "pct_total":         round(views / total_views * 100, 4) if total_views else 0,
            "watch_minutes_total": round(wm, 1),
            "avg_watch_time_min":  round(avg_d / 60, 2),
            "avg_view_pct":      round(avg_p, 2),
            "unique_viewers":    int(views * 0.33),   # estimasi; uniqueViewers kadang tidak tersedia per provinsi
            "data_source":       "youtube_analytics_api",
        })

    print(f"  ✓ Data dari Analytics API: {len(result)} provinsi")
    return result


# ══════════════════════════════════════════════════════════════════
#  PROVINCE DATA — ESTIMASI DEMOGRAFIS (fallback jika tanpa OAuth)
# ══════════════════════════════════════════════════════════════════
def estimate_province_from_demographics(total_channel_views: int, year: int, month: int):
    """
    Estimasi distribusi views per provinsi berdasarkan:
    1. Total views channel (data REAL dari YouTube Data API)
    2. Bobot distribusi pengguna internet Indonesia (BPS 2024 + Hootsuite 2024)
    
    Asumsi: ~65% traffic channel berasal dari Indonesia (rata-rata kanal berbahasa Indonesia)
    
    PENTING: Data ini adalah ESTIMASI, bukan data Analytics sesungguhnya.
    Untuk data akurat per provinsi, gunakan mode --oauth.
    """
    print("  [ESTIMASI] Kalkulasi distribusi provinsi dari data demografis...")
    print(f"  Basis: {total_channel_views:,} total views × 65% = ~{int(total_channel_views*0.65):,} views Indonesia")

    id_views = int(total_channel_views * 0.65)
    total_w  = sum(DEMOGRAPHIC_WEIGHTS.values())
    result   = []

    for name, weight in DEMOGRAPHIC_WEIGHTS.items():
        views = int(id_views * weight / total_w)
        result.append({
            "province_code":     next((k for k,v in PROVINCE_MAP.items() if v==name), ""),
            "name":              name,
            "island":            ISLAND_MAP.get(name, "Lainnya"),
            "views":             views,
            "pct_total":         round(weight / total_w * 100, 4),
            "watch_minutes_total": round(views * WATCH_TIME_BASE.get(name, 13.0), 1),
            "avg_watch_time_min":  WATCH_TIME_BASE.get(name, 13.0),
            "avg_view_pct":      round(50 + (WATCH_TIME_BASE.get(name,13) - 13) * 1.5, 1),
            "unique_viewers":    int(views * 0.33),
            "data_source":       "demographic_estimate",   # ← penanda ini bukan data langsung
        })

    result.sort(key=lambda x: x["views"], reverse=True)
    print(f"  ✓ Estimasi selesai: {len(result)} provinsi")
    return result


# ══════════════════════════════════════════════════════════════════
#  HITUNG TREN MoM
# ══════════════════════════════════════════════════════════════════
def calculate_trends(current: list, prev: list) -> list:
    """Tambahkan field trend_mom (% pertumbuhan bulan ke bulan)."""
    prev_map = {p["name"]: p["views"] for p in prev}
    for p in current:
        pv = prev_map.get(p["name"], 0)
        p["trend_mom"] = round((p["views"] - pv) / pv * 100, 2) if pv else 0.0
    return current


# ══════════════════════════════════════════════════════════════════
#  SIMPAN JSON
# ══════════════════════════════════════════════════════════════════
def save_json(data: dict, year: int, month: int) -> str:
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    filename = f"{OUTPUT_DIR}/data_provinsi_{year}-{month:02d}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Tersimpan: {filename}")
    return filename


# ══════════════════════════════════════════════════════════════════
#  MAIN SCRAPER
# ══════════════════════════════════════════════════════════════════
def scrape_month(year: int, month: int, use_oauth: bool = False):
    """
    Scrape data satu bulan.
    
    use_oauth=False → Gunakan API Key saja (data provinsi dari estimasi demografis)
    use_oauth=True  → Tambah OAuth untuk YouTube Analytics API (data provinsi REAL per provinsi)
    """
    print(f"\n{'═'*60}")
    print(f"  Scraping: {calendar.month_name[month]} {year}")
    print(f"  Mode    : {'OAuth + Analytics API (REAL)' if use_oauth else 'API Key + Estimasi Demografis'}")
    print(f"{'═'*60}")

    # 1. Channel info (selalu real)
    channel_info = fetch_channel_info()

    # 2. Video stats (selalu real)
    videos = []
    if channel_info.get("uploads_playlist"):
        videos = fetch_recent_videos(channel_info["uploads_playlist"], max_results=50)

    # 3. Distribusi provinsi
    province_data = None

    if use_oauth:
        try:
            _, yt_analytics = get_oauth_services()
            province_data = fetch_province_analytics(yt_analytics, year, month)
        except FileNotFoundError as e:
            print(f"\n  [ERROR] {e}")
            print("  → Fallback ke estimasi demografis\n")
        except Exception as e:
            print(f"\n  [WARN] OAuth/Analytics error: {e}")
            print("  → Fallback ke estimasi demografis\n")

    if province_data is None:
        province_data = estimate_province_from_demographics(channel_info["view_count"], year, month)

    # 4. Tren MoM (bandingkan dengan file bulan lalu jika ada)
    prev_m, prev_y = (month-1, year) if month > 1 else (12, year-1)
    prev_file = Path(OUTPUT_DIR) / f"data_provinsi_{prev_y}-{prev_m:02d}.json"
    if prev_file.exists():
        print("  Menghitung tren MoM dari bulan sebelumnya...")
        with open(prev_file, encoding="utf-8") as f:
            prev_json = json.load(f)
        province_data = calculate_trends(province_data, prev_json.get("provinces", []))
    else:
        for p in province_data:
            p["trend_mom"] = 0.0

    total_views  = sum(p["views"] for p in province_data)
    total_unique = sum(p["unique_viewers"] for p in province_data)
    avg_wt       = round(sum(p["avg_watch_time_min"] for p in province_data) / len(province_data), 2)
    data_src     = province_data[0].get("data_source", "unknown") if province_data else "unknown"

    output = {
        "meta": {
            "channel_id":          channel_info["channel_id"],
            "channel_name":        channel_info["channel_name"],
            "channel_thumbnail":   channel_info.get("thumbnail",""),
            "channel_subscribers": channel_info.get("subscriber_count",0),
            "channel_total_views": channel_info.get("view_count",0),
            "channel_video_count": channel_info.get("video_count",0),
            "year":                year,
            "month":               month,
            "month_name":          calendar.month_name[month],
            "scraped_at":          datetime.datetime.now().isoformat(),
            "total_views":         total_views,
            "total_unique_viewers":total_unique,
            "avg_watch_time_min":  avg_wt,
            "province_count":      len(province_data),
            "province_data_source": data_src,   # "youtube_analytics_api" atau "demographic_estimate"
            "province_data_note":   (
                "Data distribusi provinsi dari YouTube Analytics API (akurat)."
                if data_src == "youtube_analytics_api"
                else "Data distribusi provinsi merupakan ESTIMASI berdasarkan bobot demografis internet Indonesia (BPS 2024). "
                     "Gunakan --oauth untuk data akurat per provinsi."
            ),
        },
        "videos": videos[:20],   # 20 video terbaru
        "provinces": province_data,
    }

    saved = save_json(output, year, month)

    print(f"\n  ✓ Channel views  : {channel_info['view_count']:,} (REAL)")
    print(f"  ✓ Total video    : {channel_info['video_count']:,} (REAL)")
    print(f"  ✓ Est. ID views  : {total_views:,}")
    print(f"  ✓ Penonton unik  : {total_unique:,}")
    print(f"  ✓ Avg watch time : {avg_wt} mnt")
    print(f"  ✓ Provinsi aktif : {len(province_data)}")
    print(f"  ✓ Sumber data    : {data_src}")
    return saved


def scrape_range(start_year, start_month, end_year, end_month, use_oauth=False):
    results = []
    y, m = start_year, start_month
    while (y < end_year) or (y == end_year and m <= end_month):
        f = scrape_month(y, m, use_oauth=use_oauth)
        results.append(f)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return results


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="KDM YouTube Real-Time Scraper per Provinsi Indonesia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python kdm_scraper.py                          # Bulan lalu, API Key saja
  python kdm_scraper.py --month 5 --year 2025    # Mei 2025, API Key saja
  python kdm_scraper.py --oauth                  # Bulan lalu + OAuth Analytics
  python kdm_scraper.py --range 2025 1 2025 5    # Jan-Mei 2025 (API Key)
  python kdm_scraper.py --range 2025 1 2025 5 --oauth  # Jan-Mei + Analytics API

Perbedaan mode:
  API Key saja  → Channel info, video stats REAL; distribusi provinsi ESTIMASI demografis
  --oauth       → Semua data REAL termasuk distribusi provinsi dari YouTube Analytics API
        """
    )
    parser.add_argument("--year",  type=int, default=datetime.date.today().year)
    parser.add_argument("--month", type=int, default=(datetime.date.today().month - 1) or 12)
    parser.add_argument("--range", nargs=4, type=int,
                        metavar=("START_Y","START_M","END_Y","END_M"),
                        help="Scrape rentang bulan")
    parser.add_argument("--oauth", action="store_true",
                        help="Gunakan OAuth untuk YouTube Analytics API (data provinsi akurat)")
    args = parser.parse_args()

    print("\n" + "═"*60)
    print("  KDM Analytics — Real-Time YouTube Scraper")
    print(f"  Channel  : {CHANNEL_ID}")
    print(f"  API Key  : {API_KEY[:20]}...")
    print("═"*60)

    try:
        if args.range:
            sy, sm, ey, em = args.range
            print(f"\nScraping {calendar.month_name[sm]} {sy} → {calendar.month_name[em]} {ey}")
            files = scrape_range(sy, sm, ey, em, use_oauth=args.oauth)
            print(f"\n✓ Selesai! {len(files)} file tersimpan di ./{OUTPUT_DIR}/")
        else:
            file = scrape_month(args.year, args.month, use_oauth=args.oauth)
            print(f"\n✓ Selesai! File: {file}")
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"""
Langkah selanjutnya:
  1. Buka kdm_dashboard_realtime.html di browser
     (Dashboard ini langsung fetch dari YouTube API — tidak perlu upload JSON)

  ATAU jika ingin mode upload JSON:
  2. Upload file JSON dari folder ./{OUTPUT_DIR}/ ke dashboard versi upload
""")