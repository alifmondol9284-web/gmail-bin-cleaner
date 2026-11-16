import os
import time
import logging
import threading

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("bin-cleaner")

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

# একাধিক অ্যাকাউন্টের refresh token, কমা দিয়ে আলাদা করে দিন
# উদাহরণ: token1,token2,token3,token4,token5
REFRESH_TOKENS = [t.strip() for t in os.environ["GOOGLE_REFRESH_TOKENS"].split(",") if t.strip()]

# কত সেকেন্ড পর পর Bin চেক করবে
INTERVAL = float(os.environ.get("CHECK_INTERVAL_SECONDS", "2"))

# এই প্রেরকদের মেইল Bin-এ থাকলেও মুছবে না (কমা দিয়ে আলাদা করুন)
# উদাহরণ: dutchbanglabank.com,openrouter.ai
KEEP_SENDERS = [s.strip() for s in os.environ.get("KEEP_SENDERS", "").split(",") if s.strip()]

SCOPES = ["https://mail.google.com/"]


def build_query():
    q = "in:trash"
    for sender in KEEP_SENDERS:
        q += f" -from:{sender}"
    return q


def get_service(refresh_token):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def delete_trash(service, query):
    deleted = 0
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me",
            q=query,
            includeSpamTrash=True,
            maxResults=500,
            pageToken=page_token,
        ).execute()
        ids = [m["id"] for m in resp.get("messages", [])]
        if ids:
            # batchDelete স্থায়ীভাবে মোছে
            service.users().messages().batchDelete(
                userId="me", body={"ids": ids}
            ).execute()
            deleted += len(ids)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return deleted


def worker(index, refresh_token):
    query = build_query()
    name = f"account-{index}"
    backoff = 5
    service = None
    while True:
        try:
            if service is None:
                service = get_service(refresh_token)
                try:
                    name = service.users().getProfile(userId="me").execute()["emailAddress"]
                except Exception:
                    pass
                log.info("[%s] started | query: %s", name, query)
            n = delete_trash(service, query)
            if n:
                log.info("[%s] permanently deleted %d message(s)", name, n)
            backoff = 5
            time.sleep(INTERVAL)
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            log.warning("[%s] API error %s: %s", name, status, e)
            if status == 401:
                service = None
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
        except Exception as e:
            log.warning("[%s] error: %s", name, e)
            service = None
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)


def main():
    log.info("Starting %d account(s)", len(REFRESH_TOKENS))
    threads = []
    for i, tok in enumerate(REFRESH_TOKENS, start=1):
        t = threading.Thread(target=worker, args=(i, tok), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
