import os
import time
import datetime
import requests
import pytz
import pandas as pd
import yfinance as yf

# ----------------- CONFIGURATION -----------------
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1552329447485607936/R4Y25uhsLcW1gjYORGtF6C1mX0GESVB2XMYRFZZbZN8dysheC3a8YO81lkJRmSaZ_U_4"
TICKER = "NQ=F"
PRICE_OFFSET = 270.0  # MatchTrader Cash Index Offset

JST = pytz.timezone('Asia/Tokyo')
last_briefing_date = None
last_recap_date = None

def send_discord(title, description, color=3066993, footer_text="Nate's Trading Assistant"):
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": footer_text}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord Post Error: {e}")

def get_market_data():
    try:
        df = yf.download(tickers=TICKER, period="5d", interval="15m", progress=False)
        if df is None or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert(JST)
        return df.dropna()
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return None

def get_htf_trend():
    try:
        df_1h = yf.download(tickers=TICKER, period="1mo", interval="1h", progress=False)
        if df_1h is None or len(df_1h) < 100:
            return "N/A", "N/A"
        if isinstance(df_1h.columns, pd.MultiIndex):
            df_1h.columns = df_1h.columns.get_level_values(0)
        df_1h = df_1h.dropna()

        df_1h['EMA_50'] = df_1h['Close'].ewm(span=50, adjust=False).mean()
        df_1h['EMA_200'] = df_1h['Close'].ewm(span=200, adjust=False).mean()

        curr_close = float(df_1h['Close'].iloc[-1])
        t_1h = "📈 BULLISH" if curr_close > float(df_1h['EMA_50'].iloc[-1]) else "📉 BEARISH"
        t_4h = "📈 BULLISH" if curr_close > float(df_1h['EMA_200'].iloc[-1]) else "📉 BEARISH"

        return t_1h, t_4h
    except Exception:
        return "N/A", "N/A"

def send_daily_briefing():
    df = get_market_data()
    if df is None:
        return

    now_jst = datetime.datetime.now(JST)
    today_date = now_jst.date()

    asian_df = df[(df.index.date == today_date) & (df.index.hour >= 9) & (df.index.hour < 15)]
    if asian_df.empty:
        return

    asian_high = float(asian_df['High'].max()) - PRICE_OFFSET
    asian_low = float(asian_df['Low'].min()) - PRICE_OFFSET
    range_size = asian_high - asian_low

    t_1h, t_4h = get_htf_trend()

    if "BULLISH" in t_1h and "BULLISH" in t_4h:
        focus = "Trend က Bullish ညီနေ၍ Asian Low (SSL) ကို သုတ်ပြီး ပြန်လှည့်လာမည့် Buy Setup ကိုသာ စိတ်ရှည်ရှည် ဦးစားပေး စောင့်ကြည့်ပေးပါ။"
    elif "BEARISH" in t_1h and "BEARISH" in t_4h:
        focus = "Trend က Bearish ညီနေ၍ Asian High (BSL) ကို သုတ်ပြီး ပြန်ကျလာမည့် Sell Setup ကိုသာ ဦးစားပေး စောင့်ကြည့်ပေးပါ။"
    else:
        focus = "HTF Trend အချင်းချင်း လွဲနေပါသည် (1H vs 4H)။ အလောတကြီး မရိုက်ဘဲ သန့်ရှင်းသော Liquidity Sweep ထွက်မှသာ ဝင်သင့်ပါသည်။"

    desc = (
        f"Good afternoon ပါ သားရီး! ☕\n"
        f"ဒီနေ့အတွက် NDX100 London Prep အခြေအနေကို အစီရင်ခံ တင်ပြပေးလိုက်ပါတယ်။\n\n"
        f"🧭 HTF Macro Bias:\n"
        f"• 1-Hour Trend: {t_1h}\n"
        f"• 4-Hour Trend: {t_4h}\n\n"
        f"🎯 Asian Benchmark Levels (MatchTrader):\n"
        f"• Asian High (BSL): {asian_high:.2f}\n"
        f"• Asian Low (SSL): {asian_low:.2f}\n"
        f"• Range Spread: {range_size:.2f} pts\n\n"
        f"📋 Today's Strategic Focus:\n"
        f"{focus}\n\n"
        f"⚠️ Execution Reminder:\n"
        f"အမေရိကန် သတင်းရှိပါက ဂရုစိုက်ပါ။ ဒီနေ့အတွက် စည်းကမ်းတကျ အေးအေးဆေးဆေး အနိုင်ယူလိုက်ကြရအောင်ဗျာ!"
    )
    send_discord("🌅 NDX100 | DAILY SESSION BRIEFING", desc, color=3447003, footer_text="London Session Prep • 15:05 JST")

def send_daily_recap():
    df = get_market_data()
    if df is None:
        returnnow_jst = datetime.datetime.now(JST)
    today_date = now_jst.date()

    asian_df = df[(df.index.date == today_date) & (df.index.hour >= 9) & (df.index.hour < 15)]
    trading_df = df[(df.index.date == today_date) & (df.index.hour >= 15)]

    if asian_df.empty or trading_df.empty:
        return

    asian_high = float(asian_df['High'].max()) - PRICE_OFFSET
    asian_low = float(asian_df['Low'].min()) - PRICE_OFFSET

    day_high = float(trading_df['High'].max()) - PRICE_OFFSET
    day_low = float(trading_df['Low'].min()) - PRICE_OFFSET
    day_close = float(trading_df['Close'].iloc[-1]) - PRICE_OFFSET

    swept_low = day_low < asian_low
    swept_high = day_high > asian_high

    if swept_low and not swept_high:
        sweep_text = f"✅ SSL Swept (Asian Low အောက် {day_low:.2f} အထိ Wick ထိုးဆင်းခဲ့သည်)"
    elif swept_high and not swept_low:
        sweep_text = f"✅ BSL Swept (Asian High အထက် {day_high:.2f} အထိ Wick ထိုးတက်ခဲ့သည်)"
    elif swept_low and swept_high:
        sweep_text = f"⚠️ Both Swept (High {day_high:.2f} ရော Low {day_low:.2f} ပါ ထိုးဖောက်ခဲ့သည်)"
    else:
        sweep_text = "❌ No Sweep (Asian Range အတွင်းသာ ပိတ်မိနေခဲ့သည်)"

    if swept_low and day_close > asian_low:
        mss_text = "✅ 15m Bullish Shift Confirmed"
        target_text = "🎯 TP1 (1:2) အောင်မြင်စွာ ရောက်ရှိခဲ့သည်"
        direction_text = "🟢 Bullish Expansion Day"
        note_text = "Setup က Strategy အတိုင်း အတိအကျ ထွက်သွားခဲ့သည်။"
        color = 3066993
    elif swept_high and day_close < asian_high:
        mss_text = "✅ 15m Bearish Shift Confirmed"
        target_text = "🎯 TP1 (1:2) အောင်မြင်စွာ ရောက်ရှိခဲ့သည်"
        direction_text = "🔴 Bearish Expansion Day"
        note_text = "Setup က Strategy အတိုင်း အတိအကျ ထွက်သွားခဲ့သည်။"
        color = 15158332
    elif swept_high and day_close >= asian_high:
        mss_text = "❌ No Reversal MSS (Breakout Continuation)"
        target_text = "➖ Reversal Setup မထွက်ခဲ့ပါ"
        direction_text = "🔵 Strong Bullish Trend Day"
        note_text = "Reversal မပြဘဲ တစ်ရိုးတည်း အရှိန်ပြင်းပြင်း ထိုးတက်သွားခဲ့သည်။"
        color = 3447003
    elif not swept_low and not swept_high:
        mss_text = "➖ No Setup Triggered"
        target_text = "➖ 0 Trade Day"
        direction_text = "⚪ Choppy / Consolidation Day"
        note_text = "Liquidity မသုတ်ဘဲ Range အတွင်း ငြိမ်နေ၍ အနားယူရမည့်နေ့ ဖြစ်ခဲ့သည်။"
        color = 9807270
    else:
        mss_text = "⚠️ Volatile Market Shift"
        target_text = "➖ Complex Session"
        direction_text = "🟡 High Volatility Session"
        note_text = "ဈေးကွက် အတက်အကျ ပြင်းထန်ခဲ့သော နေ့ဖြစ်ခဲ့သည်။"
        color = 15844367

    desc = (
        f"Good night ပါ သားရီး! 🌙\n"
        f"ဒီနေ့တစ်နေ့တာ NDX100 Price Action မှတ်တမ်းကို သုံးသပ် တင်ပြပေးလိုက်ပါတယ်။\n\n"
        f"📊 Session Action Summary:\n"
        f"• Sweep Detected: {sweep_text}\n"
        f"• MSS Confirmation: {mss_text}\n"
        f"• Expansion Target: {target_text}\n\n"
        f"📈 Daily Extremes:\n"
        f"• Day High: {day_high:.2f}\n"
        f"• Day Low: {day_low:.2f}\n"
        f"• Net Direction: {direction_text}\n\n"
        f"💡 Note: {note_text}\n\n"
        f"ဒီနေ့အတွက် Trading စည်းကမ်းတွေကို ထိန်းသိမ်းနိုင်ခဲ့တာ ဂုဏ်ယူပါတယ်ဗျာ။ စိတ်လက်အေးချမ်းစွာ ကောင်းကောင်း အနားယူလိုက်ပါဦး! မနက်ဖြန်ကျမှ ထပ်တွေ့ကြမယ်!"
    )
    send_discord("🌙 NDX100 | DAILY RECAP & JOURNAL", desc, color=color, footer_text="Daily Close Journal • 00:00 JST")

# ----------------- STARTUP DIRECT EXECUTION -----------------
send_discord(
    "🤖 Nate's Trading Assistant Online!",
    "မင်္ဂလာပါ သားရီး!\n"
    "ကိုယ်ပိုင် Trading Assistant စနစ် အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ။\n\n"
    "• Daily Briefing: နေ့လယ် ၃:၀၅ JST (London Prep)\n"
    "• Daily Recap & Journal: ည ၁၂:၀၀ JST (NY Close)\n"
    "• Price Calibration: MatchTrader Offset (-270 pts) တပ်ဆင်ပြီး။\n\n"
    "၂၄ နာရီလုံး ဈေးကွက်ကို သေချာ စောင့်ကြည့်ပြီး အချိန်တန်ရင် အစီရင်ခံပေးပါ့မယ်!",
    color=3066993
)# ----------------- SCHEDULER LOOP -----------------
while True:
    try:
        now_jst = datetime.datetime.now(JST)
        today = now_jst.date()
        hour = now_jst.hour
        minute = now_jst.minute

        if hour == 15 and minute >= 5 and last_briefing_date != today:
            send_daily_briefing()
            last_briefing_date = today

        if hour == 0 and minute >= 0 and last_recap_date != today:
            send_daily_recap()
            last_recap_date = today

    except Exception as e:
        print(f"Scheduler Loop Error: {e}")

    time.sleep(30)
