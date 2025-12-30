import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"


class SteamReviewsError(RuntimeError):
    pass

'''
decorator that auto generates boilerplate code for dunder methods
used for classes that store data
'''
@dataclass
class NormalizedReview:
    recommendationid: str
    steamid: str
    language: str
    review: str
    voted_up: bool
    timestamp_created: int
    timestamp_updated: int
    author_num_games_owned: int
    author_num_reviews: int
    author_playtime_forever: int
    author_playtime_last_two_weeks: int
    author_playtime_at_review: int
    votes_up: int
    votes_funny: int
    weighted_vote_score: str
    comment_count: int
    steam_purchase: bool
    received_for_free: bool
    written_during_early_access: bool


'''
Schema enforcement layer that takes any messiness that you pull from the Steam API 
and ensures it fully matches our data format so we can properly use pandas. 
Normalizes via: 
    -Forcing consistent types
    -Flattens nested author object
    -Handles missing keys
'''
def _normalize_review(r: Dict[str, Any]) -> NormalizedReview:
    a = r.get("author", {}) or {}
    return NormalizedReview(
        recommendationid=str(r.get("recommendationid", "")),
        steamid=str(a.get("steamid", "")),
        language=r.get("language", ""),
        review=r.get("review", ""),
        voted_up=bool(r.get("voted_up", False)),
        timestamp_created=int(r.get("timestamp_created", 0)),
        timestamp_updated=int(r.get("timestamp_updated", 0)),
        author_num_games_owned=int(a.get("num_games_owned", 0)),
        author_num_reviews=int(a.get("num_reviews", 0)),
        author_playtime_forever=int(a.get("playtime_forever", 0)),
        author_playtime_last_two_weeks=int(a.get("playtime_last_two_weeks", 0)),
        author_playtime_at_review=int(a.get("playtime_at_review", 0)),
        votes_up=int(r.get("votes_up", 0)),
        votes_funny=int(r.get("votes_funny", 0)),
        weighted_vote_score=str(r.get("weighted_vote_score", "")),
        comment_count=int(r.get("comment_count", 0)),
        steam_purchase=bool(r.get("steam_purchase", False)),
        received_for_free=bool(r.get("received_for_free", False)),
        written_during_early_access=bool(r.get("written_during_early_access", False)),
    )

'''
    Fetch Steam Store user reviews for ONE app (AppID) via cursor pagination.

    Practical notes:
    - Use filter_mode="recent" or "updated" for predictable pagination end.
    - Steam returns `cursor` already URL-escaped; pass it back verbatim.
'''
def fetch_all_steam_reviews_for_app(
    appid: int,
    *,
    language: str = "all",                 # "all" or e.g. "english"
    review_type: str = "all",              # all | positive | negative
    purchase_type: str = "all",            # all | steam | non_steam_purchase
    filter_mode: str = "recent",           # recent | updated | all
    day_range: int = 9223372036854775807,  # huge number => “all time”
    num_per_page: int = 100,               # max 100
    filter_offtopic_activity: int = 1,     # 1 filters “off-topic”/review-bomb activity
    include_raw: bool = False,             # include the raw review objects too
    normalize: bool = True,                # return cleaned/consistent fields
    max_reviews: Optional[int] = None,     # safety cap
    sleep_seconds: float = 0.25,           # be polite
    timeout_seconds: float = 30.0,
    session: Optional[requests.Session] = None
    
) -> Dict[str, Any]:
    
    if not (1 <= num_per_page <= 100):
        raise ValueError("num_per_page must be between 1 and 100")

    sess = session or requests.Session()
    cursor = "*"  # first page
    seen_cursors = set()

    normalized_reviews: List[Dict[str, Any]] = []
    raw_reviews: List[Dict[str, Any]] = []

    while True:
        # Safety guard against weird loops
        if cursor in seen_cursors:
            break
        seen_cursors.add(cursor)

        params = {
            "json": 1,
            "cursor": cursor,
            "language": language,
            "review_type": review_type,
            "purchase_type": purchase_type,
            "filter": filter_mode,
            "day_range": day_range,
            "num_per_page": num_per_page,
            "filter_offtopic_activity": filter_offtopic_activity,
        }

        url = STEAM_REVIEWS_URL.format(appid=appid)
        resp = sess.get(url, params=params, timeout=timeout_seconds)
        if resp.status_code != 200:
            raise SteamReviewsError(f"HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if data.get("success") != 1:
            raise SteamReviewsError(f"Steam returned success={data.get('success')}: {data}")

        page_reviews = data.get("reviews") or []
        next_cursor = data.get("cursor", cursor)

        if not page_reviews:
            cursor = next_cursor
            break

        if include_raw:
            raw_reviews.extend(page_reviews)

        if normalize:
            for r in page_reviews:
                normalized_reviews.append(asdict(_normalize_review(r)))
        else:
            # If you want “as-is” but without top-level extras, this is the raw page objects
            normalized_reviews.extend(page_reviews)

        cursor = next_cursor

        #Cuts off any reviews after exceeding max_reviews parameter
        if max_reviews is not None and len(normalized_reviews) >= max_reviews:
            normalized_reviews = normalized_reviews[:max_reviews]
            if include_raw:
                raw_reviews = raw_reviews[:max_reviews]
            break

        time.sleep(sleep_seconds)

    result: Dict[str, Any] = {
        "appid": appid,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_params": {
            "language": language,
            "review_type": review_type,
            "purchase_type": purchase_type,
            "filter": filter_mode,
            "day_range": day_range,
            "num_per_page": num_per_page,
            "filter_offtopic_activity": filter_offtopic_activity,
        },
        "count": len(normalized_reviews),
        "last_cursor": cursor,
        "reviews": normalized_reviews,
    }

    if include_raw:
        result["raw_reviews"] = raw_reviews

    return result


def save_reviews_json(dataset: Dict[str, Any], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Download Steam Store reviews for a single AppID and save to JSON.")
    p.add_argument("--appid", type=int, default=4134990, help="Steam AppID (e.g., 413150). Default is 4134990: Pixelate TD")
    p.add_argument("--language", default="all", help='Review language (e.g., "all", "english", "brazilian")')
    p.add_argument("--review-type", default="all", choices=["all", "positive", "negative"], help="Filter by review sentiment")
    p.add_argument("--purchase-type", default="all", choices=["all", "steam", "non_steam_purchase"], help="Filter by purchase type")
    p.add_argument("--filter-mode", default="recent", choices=["recent", "updated", "all"], help="Paging mode (recent/updated recommended)")
    p.add_argument("--day-range", type=int, default=9223372036854775807, help="Lookback window in days (huge default = all time)")
    p.add_argument("--num-per-page", type=int, default=100, help="Reviews per page (1-100)")
    p.add_argument("--filter-offtopic-activity", type=int, default=1, choices=[0, 1], help="1 filters off-topic/review-bomb activity; 0 includes it")
    p.add_argument("--max-reviews", type=int, default=1000, help="Stop after downloading this many reviews")
    p.add_argument("--sleep-seconds", type=float, default=0.25, help="Delay between requests (polite throttling)")
    p.add_argument("--timeout-seconds", type=float, default=30.0, help="Request timeout in seconds")

    # Flags
    p.add_argument("--include-raw", action="store_true", help="Include raw review objects in output JSON")
    p.add_argument("--no-normalize", action="store_true", help="Do not normalize reviews (store raw page review objects)")

    # Output
    p.add_argument(
        "--out",
        default=None,
        help='Output JSON path. Default: "steam_reviews_<appid>.json" in current directory.',
    )
    return p


if __name__ == "__main__":
    #appid = 1245620  # example: Elden Ring
    #appid = 4134990 #example: Pixelate TD
    #appid = 413150 #stardew valley
    parser = build_arg_parser() 
    args = parser.parse_args()

    normalize = not args.no_normalize
    out_file = args.out or f"steam_reviews_{args.appid}.json"

    data = fetch_all_steam_reviews_for_app(
        args.appid,
        language=args.language,
        filter_mode=args.filter_mode,
        review_type=args.review_type,
        purchase_type=args.purchase_type,
        normalize=normalize,
        max_reviews=args.max_reviews,
        include_raw=args.include_raw,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
        day_range=args.day_range,
        num_per_page=args.num_per_page,
        filter_offtopic_activity=args.filter_offtopic_activity,
    )

    save_reviews_json(data, out_file)
    print(f"Saved {data['count']} reviews to {out_file}")