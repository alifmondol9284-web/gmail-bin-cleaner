"""
এটি শুধু নিজের কম্পিউটারে চালাবেন (Render-এ নয়)।
credentials.json ফাইলটি এই ফোল্ডারে রাখুন।
প্রতিটি Gmail অ্যাকাউন্টের জন্য একবার করে চালাতে হবে (৫টি অ্যাকাউন্ট = ৫ বার)।
প্রতিবার ব্রাউজারে ওই অ্যাকাউন্টটি দিয়ে লগইন করবেন।
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://mail.google.com/"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

email = build("gmail", "v1", credentials=creds).users().getProfile(userId="me").execute()["emailAddress"]

print("\n==== অ্যাকাউন্ট:", email, "====")
print("GOOGLE_CLIENT_ID     =", creds.client_id)
print("GOOGLE_CLIENT_SECRET =", creds.client_secret)
print("REFRESH TOKEN        =", creds.refresh_token)
print("\nএই টোকেন গোপন রাখুন, GitHub-এ দেবেন না।")
print("৫টি টোকেন কমা দিয়ে জুড়ে GOOGLE_REFRESH_TOKENS-এ দেবেন।")