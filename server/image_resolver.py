"""
image_resolver.py

Resolves a bird species image URL from Wikipedia or Flickr.
Results are cached in memory (keyed by scientific name) so each species
is only looked up once per server run.

Falls back to the static placeholder if:
  - IMAGE_PROVIDER is not set
  - The provider returns no image
  - A network/API error occurs
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

PLACEHOLDER_URL = "/static/placeholder.png"

# In-memory cache: sci_name -> image_url (or PLACEHOLDER_URL)
_cache: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------

def _wikipedia_image(sci_name: str) -> str | None:
    page_title = sci_name.replace(" ", "_")
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}",
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Wikipedia summary request failed for %r: %s", sci_name, exc)
        return None

    original = data.get("originalimage", {}).get("source")
    if not original:
        return None

    # Cap width at 1280px using Wikimedia thumb URL convention
    if "/commons/" in original:
        filename = original.rsplit("/", 1)[-1]
        thumb_url = original.replace("/commons/", "/commons/thumb/") + f"/1280px-{filename}"
        return thumb_url

    return original


# ---------------------------------------------------------------------------
# Flickr
# ---------------------------------------------------------------------------

def _flickr_image(sci_name: str, api_key: str, filter_email: str | None = None) -> str | None:
    # Build search query
    params: dict = {
        "method": "flickr.photos.search",
        "api_key": api_key,
        "text": sci_name,
        "sort": "relevance",
        "content_type": 1,  # photos only
        "license": "1,2,3,4,5,6,9,10",  # open licenses
        "extras": "url_c,owner_name",
        "per_page": 1,
        "format": "json",
        "nojsoncallback": 1,
    }

    if filter_email:
        # Resolve email -> NSID first
        try:
            r = requests.get(
                "https://www.flickr.com/services/rest/",
                params={
                    "method": "flickr.people.findByEmail",
                    "api_key": api_key,
                    "find_email": filter_email,
                    "format": "json",
                    "nojsoncallback": 1,
                },
                timeout=8,
            )
            r.raise_for_status()
            nsid = r.json().get("user", {}).get("nsid")
            if nsid:
                params["user_id"] = nsid
        except Exception as exc:
            logger.warning("Flickr NSID lookup failed: %s", exc)

    try:
        resp = requests.get("https://www.flickr.com/services/rest/", params=params, timeout=8)
        resp.raise_for_status()
        photos = resp.json().get("photos", {}).get("photo", [])
    except Exception as exc:
        logger.warning("Flickr search failed for %r: %s", sci_name, exc)
        return None

    if not photos:
        return None

    photo = photos[0]
    # Prefer url_c (medium 800); fall back to constructing from farm/server/id/secret
    if photo.get("url_c"):
        return photo["url_c"]

    farm = photo.get("farm")
    server = photo.get("server")
    pid = photo.get("id")
    secret = photo.get("secret")
    if all([farm, server, pid, secret]):
        return f"https://farm{farm}.static.flickr.com/{server}/{pid}_{secret}.jpg"

    return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def resolve_image_url(sci_name: str) -> str:
    """
    Return a cached image URL for `sci_name`, fetching from the configured
    provider if not yet cached. Returns PLACEHOLDER_URL on any failure.
    """
    if sci_name in _cache:
        return _cache[sci_name]

    provider = os.environ.get("IMAGE_PROVIDER", "").upper()
    url: str | None = None

    if provider == "WIKIPEDIA":
        url = _wikipedia_image(sci_name)
    elif provider == "FLICKR":
        api_key = os.environ.get("FLICKR_API_KEY", "")
        if api_key:
            filter_email = os.environ.get("FLICKR_FILTER_EMAIL") or None
            url = _flickr_image(sci_name, api_key, filter_email)
        else:
            logger.warning("IMAGE_PROVIDER=FLICKR but FLICKR_API_KEY is not set")

    result = url if url else PLACEHOLDER_URL
    _cache[sci_name] = result
    logger.debug("Image resolved for %r -> %s", sci_name, result)
    return result
