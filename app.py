from flask import Flask, render_template, request
import os
import uuid
import traceback

# Google Sheets (Service Account)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Drive (OAuth)
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# GOOGLE SHEETS (SERVICE ACCOUNT)
# =========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_sheet = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds_sheet)
sheet = client.open("StudentData").sheet1


# =========================
# GOOGLE DRIVE (OAUTH)
# =========================
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = "token.json"


def get_drive_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


# 👉 YOUR DRIVE FOLDER ID
FOLDER_ID = "1iqefwzb1ztTqUE7GmEBgW1zZ9eSBvzhC"


# =========================
# GENERATE UNIQUE ID
# =========================
def generate_id():
    return "STU-" + str(uuid.uuid4())[:8]


# =========================
# UPLOAD TO GOOGLE DRIVE
# =========================
def upload_to_drive(file_path, student_id):
    service = get_drive_service()

    file_metadata = {
        'name': f'{student_id}.jpg',
        'parents': [FOLDER_ID]
    }

    media = MediaFileUpload(file_path, mimetype='image/jpeg')

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = file.get('id')

    return f"https://drive.google.com/file/d/{file_id}/view"


# =========================
# SAVE TO GOOGLE SHEET
# =========================
def save_to_sheet(data):
    sheet.append_row(data)


# =========================
# ROUTES
# =========================
@app.route('/')
def form():
    return render_template('form.html')


@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form['name']
        student_class = request.form['class']
        phone = request.form['phone']
        photo = request.files['photo']

        student_id = generate_id()

        # Save temporarily
        temp_path = os.path.join(UPLOAD_FOLDER, f"{student_id}.jpg")
        photo.save(temp_path)
        print("✅ Image saved locally")

        # Upload to Drive
        drive_link = upload_to_drive(temp_path, student_id)
        print("✅ Uploaded to Drive:", drive_link)

        # Save to Sheet
        save_to_sheet([
            student_id,
            name,
            student_class,
            phone,
            drive_link
        ])
        print("✅ Saved to Sheet")

        # Delete temp file
        os.remove(temp_path)

        return f"SUCCESS: {student_id}"

    except Exception as e:
        print("❌ ERROR:", e)
        traceback.print_exc()
        return str(e)


# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)