import os
import time
import threading
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ============ CONFIG =============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID"))
IVASMS_EMAIL = os.getenv("IVASMS_EMAIL")
IVASMS_PASSWORD = os.getenv("IVASMS_PASSWORD")
IVASMS_URL = "https://www.ivasms.com/login"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-koyeb-subdomain.koyeb.app
# ==================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

driver = None
monitoring = False
acquired_numbers = []


def start_browser():
    global driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)


def login_ivasms():
    driver.get(IVASMS_URL)
    time.sleep(3)
    driver.find_element(By.NAME, "email").send_keys(IVASMS_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
    time.sleep(5)


def get_available_numbers():
    driver.get("https://www.ivasms.com/test-number")
    time.sleep(3)
    numbers = []
    rows = driver.find_elements(By.XPATH, "//table//tr")
    for row in rows[1:]:
        cols = row.find_elements(By.TAG_NAME, "td")
        if cols:
            country = cols[0].text.strip()
            number = cols[1].text.strip()
            numbers.append(f"{country} {number}")
    return numbers


def acquire_all_numbers():
    driver.get("https://www.ivasms.com/test-number")
    time.sleep(3)
    buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Acquire')]")
    for btn in buttons:
        try:
            btn.click()
            time.sleep(1)
        except:
            continue


def check_for_otps():
    global monitoring
    while monitoring:
        try:
            driver.get("https://www.ivasms.com/client-active-sms")
            time.sleep(3)
            rows = driver.find_elements(By.XPATH, "//table//tr")
            for row in rows[1:]:
                cols = row.find_elements(By.TAG_NAME, "td")
                if cols and "OTP" in cols[2].text:
                    number = cols[0].text.strip()
                    content = cols[2].text.strip()
                    bot.send_message(YOUR_TELEGRAM_ID, f"📩 OTP for {number}: {content}")
        except Exception as e:
            print("Error checking OTPs:", e)
        time.sleep(60)


# === Telegram Handlers ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    global monitoring, acquired_numbers

    bot.reply_to(message, "🔄 Logging into iVASMS...")
    start_browser()
    login_ivasms()
    numbers = get_available_numbers()

    if not numbers:
        bot.send_message(message.chat.id, "❌ No numbers available.")
        return

    acquired_numbers = numbers
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("yes", "no")

    bot.send_message(
        message.chat.id,
        f"Hey Teez Plug Bot is active. Do you want to acquire these numbers?\n\n{', '.join(numbers)}",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text.lower() in ["yes", "no"])
def handle_response(message):
    global monitoring

    if message.text.lower() == "yes":
        acquire_all_numbers()
        bot.send_message(message.chat.id, "✅ Numbers acquired. Monitoring for OTPs...")
        if not monitoring:
            monitoring = True
            threading.Thread(target=check_for_otps, daemon=True).start()
    else:
        bot.send_message(message.chat.id, "❌ Okay, cancelled.")


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "/start - Start the bot\n/help - Show help info")


# === Flask Routes ===
@app.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200


@app.route("/", methods=['GET'])
def index():
    return "🤖 Teez Plug Bot is Running", 200


# === Start Flask App + Set Webhook ===
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
