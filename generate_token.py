from kiteconnect import KiteConnect

# ===============================
# Zerodha App Credentials
# ===============================
API_KEY = "dn0fxv4myw1bk1sa"
API_SECRET = "vluodvfuvka679d0jn88v1elsx7zgnny"

# ===============================
# Create Kite client
# ===============================
kite = KiteConnect(api_key=API_KEY)

# Step 1: Print login URL
print("\n🔗 Login using this URL:")
print(kite.login_url())

# Step 2: Paste request_token after login
request_token = input("\nPaste request_token here: ").strip()

# Step 3: Generate session
data = kite.generate_session(
    request_token=request_token,
    api_secret=API_SECRET
)

# Step 4: Print access token
print("\n✅ ACCESS TOKEN GENERATED SUCCESSFULLY")
print("ACCESS_TOKEN =", data["access_token"])
