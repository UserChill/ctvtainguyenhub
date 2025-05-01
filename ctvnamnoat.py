import requests
import os
import shutil
import json
import time  # Thêm time
from datetime import datetime

# ===== THÊM VÀO ĐÂY: Setup lưu file vào thư mục ẩn =====
if os.name == 'nt':  # Windows
    CACHE_DIR = os.path.join(os.getenv('LOCALAPPDATA'), "SystemCache")
else:  # macOS / Linux / Android
    CACHE_DIR = os.path.expanduser("~/.local/share/SystemCache")

os.makedirs(CACHE_DIR, exist_ok=True)
# =======================================================

API_KEY = os.getenv("TAINGUYENHUB_API_KEY", "01035502d75b898bd72674bbd2b4baeb")
PROFILE_URL = "https://tainguyenhub.com/api/profile.php"
UPLOAD_URL = "https://tainguyenhub.com/api/importAccount.php"

SHOPS = {
    "1": ("Clone New Name Việt Vr Phone Có Avt+Bìa", "681116e67eafc", 4),
    "2": ("CLONE VERY HOTMAIL NAME RANDOM NO 2FA", "6813910f11417", 4),
}

UPLOAD_COUNT_FILE = os.path.join(CACHE_DIR, "upload_count.json")
UPLOAD_SUCCESS_UIDS_FILE = os.path.join(CACHE_DIR, "upload_success_uids.json")

def load_upload_count():
    if os.path.exists(UPLOAD_COUNT_FILE):
        with open(UPLOAD_COUNT_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                return data.get("count", 0)
    return 0

def save_upload_count(count):
    with open(UPLOAD_COUNT_FILE, "w") as f:
        json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "count": count}, f)

def load_uploaded_uids():
    if os.path.exists(UPLOAD_SUCCESS_UIDS_FILE):
        with open(UPLOAD_SUCCESS_UIDS_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                return set(data.get("uids", []))
    return set()

def save_uploaded_uids(uids):
    with open(UPLOAD_SUCCESS_UIDS_FILE, "w") as f:
        json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "uids": list(uids)}, f)

upload_count_today = load_upload_count()
uploaded_uids_today = load_uploaded_uids()

def get_terminal_width():
    return shutil.get_terminal_size().columns

def print_boxed_text(title, options):
    term_width = get_terminal_width()
    max_width = min(term_width - 4, 80)
    box_width = max(len(title), max((len(opt) for opt in options), default=0)) + 4
    box_width = min(box_width, max_width)

    print("╔" + "═" * box_width + "╗")
    print("║ " + title.center(box_width - 2) + " ║")
    print("╠" + "═" * box_width + "╣")
    for opt in options:
        lines = [opt[i:i+box_width-2] for i in range(0, len(opt), box_width-2)]
        for line in lines:
            print(f"║ {line.ljust(box_width-2)} ║")
    print("╚" + "═" * box_width + "╝")

def check_balance():
    response = requests.get(PROFILE_URL, params={"api_key": API_KEY})
    if response.status_code == 200:
        data = response.json().get("data", {})
        if data:
            balance = int(float(data.get("money", "0")))
            username = data.get("username", "Không rõ")
            withdrawable = int(balance * 0.96)
            print(f"Username: {username}\nSố dư: {balance:,}\nSố tiền có thể rút (trừ 4%): {withdrawable:,}")
        else:
            print("Lỗi: Tài khoản bị khóa hoặc web lỗi.")
    else:
        print("Lỗi khi lấy thông tin tài khoản!")

def upload_accounts(file_path, code, shop_name, expected_format_count):
    global upload_count_today, uploaded_uids_today

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            accounts = f.read().strip().split("\n")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp {file_path}")
        return

    if not accounts:
        print("Lỗi: Không có dữ liệu trong tệp.")
        return

    valid_accounts = []
    format_errors = []
    seen_uids = set()
    duplicate_accounts = []

    for acc in accounts:
        parts = acc.split("|")
        if len(parts) == expected_format_count and parts[0].isdigit():
            uid = parts[0]
            if uid not in seen_uids:
                valid_accounts.append(acc.replace("-", "|"))
                seen_uids.add(uid)
            else:
                duplicate_accounts.append(acc)
        else:
            format_errors.append(f"Lỗi định dạng ({len(parts)} phần, yêu cầu {expected_format_count}): {acc}")

    already_uploaded_today = []
    upload_success_messages = []

    for acc in valid_accounts:
        uid = acc.split("|")[0]
        if uid in uploaded_uids_today:
            already_uploaded_today.append(acc)
            continue

        response = requests.post(UPLOAD_URL, data={
            "code": code,
            "api_key": API_KEY,
            "account": acc,
            "filter": 1
        })

        time.sleep(0.3)  # === NGỈ 0.2 GIÂY ===

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                upload_success_messages.append(f"Upload thành công: {acc} -> success")
                uploaded_uids_today.add(uid)
            elif "đã tồn tại" in result.get("msg", "").lower():
                already_uploaded_today.append(acc)
            else:
                print(f"Lỗi upload: {acc} -> {result.get('msg', 'Không xác định')}")
        else:
            print(f"Lỗi upload: {acc} -> {response.status_code}")

    upload_count_today = len(uploaded_uids_today)
    save_upload_count(upload_count_today)
    save_uploaded_uids(uploaded_uids_today)

    if duplicate_accounts:
        print_colored_boxed_text("PHÁT HIỆN TÀI KHOẢN TRÙNG", duplicate_accounts, COLOR_YELLOW)

    if already_uploaded_today:
        print_colored_boxed_text("ĐÃ UPLOAD HÔM NAY (BỎ QUA)", already_uploaded_today, COLOR_RED)

    if upload_success_messages:
        print_colored_boxed_text("UPLOAD THÀNH CÔNG", upload_success_messages, COLOR_GREEN)
    if format_errors:
        print_format_errors_box(format_errors, COLOR_YELLOW)

    print_summary_in_box(
        success_count=len(upload_success_messages),
        upload_count_today=upload_count_today,
        duplicate_count=len(duplicate_accounts),
        skipped_today_count=len(already_uploaded_today),
        format_error_count=len(format_errors)
    )

def print_colored_boxed_text(title, options, color_code):
    term_width = get_terminal_width()
    max_width = min(term_width - 4, 80)
    box_width = max(len(title), max((len(opt) for opt in options), default=0)) + 4
    box_width = min(box_width, max_width)

    print("╔" + "═" * box_width + "╗")
    print("║ " + title.center(box_width - 2) + " ║")
    print("╠" + "═" * box_width + "╣")
    for opt in options:
        lines = [opt[i:i+box_width-2] for i in range(0, len(opt), box_width-2)]
        for line in lines:
            print("║ ", end="")
            print(f"\033[{color_code}m{line.ljust(box_width-2)}\033[0m", end="")
            print(" ║")
    print("╚" + "═" * box_width + "╝")

def print_summary_in_box(success_count, upload_count_today, duplicate_count, skipped_today_count, format_error_count):
    term_width = get_terminal_width()
    box_width = min(term_width - 4, 80)

    lines = [
        (f"Tổng upload thành công: {success_count} tài khoản mới.", COLOR_GREEN),
        (f"Tổng số acc đã upload hôm nay: {upload_count_today}", COLOR_GREEN),
        (f"Tổng phát hiện trùng: {duplicate_count} tài khoản.", COLOR_YELLOW),
        (f"Tổng bỏ qua do đã upload hôm nay: {skipped_today_count} tài khoản.", COLOR_RED),
        (f"Tổng số acc lỗi định dạng: {format_error_count} tài khoản.", COLOR_YELLOW)
    ]

    max_line_length = max(len(line) for line, _ in lines)
    box_width = min(max_line_length + 4, box_width)

    print("╔" + "═" * box_width + "╗")
    print("║ " + "TỔNG KẾT".center(box_width - 2) + " ║")
    print("╠" + "═" * box_width + "╣")

    for text, color in lines:
        print("║ ", end="")
        print(f"\033[{color}m{text.ljust(box_width-2)}\033[0m", end="")
        print(" ║")

    print("╚" + "═" * box_width + "╝")

def print_format_errors_box(errors, color_code):
    title = "LỖI ĐỊNH DẠNG"
    term_width = get_terminal_width()
    max_width = min(term_width - 4, 100)
    box_width = max(len(title), max((len(e) for e in errors), default=0)) + 4
    box_width = min(box_width, max_width)

    print("╔" + "═" * box_width + "╗")
    print("║ " + title.center(box_width - 2) + " ║")
    print("╠" + "═" * box_width + "╣")
    for err in errors:
        lines = [err[i:i+box_width-2] for i in range(0, len(err), box_width-2)]
        for line in lines:
            print("║ ", end="")
            print(f"\033[{color_code}m{line.ljust(box_width-2)}\033[0m", end="")
            print(" ║")
    print("╚" + "═" * box_width + "╝")



COLOR_GREEN = "92"
COLOR_YELLOW = "93"
COLOR_RED = "91"
COLOR_GRAY = "90"
COLOR_CYAN = "96"

if __name__ == "__main__":
    print_boxed_text("MENU CHÍNH", ["1: Kiểm tra số dư", "2: Upload tài khoản"])
    choice = input("Chọn chức năng (1 hoặc 2): ").strip()

    if choice == "1":
        check_balance()
    elif choice == "2":
        shop_options = [f"{key}: {shop_name}" for key, (shop_name, _, _) in SHOPS.items()]
        print_boxed_text("CHỌN GIAN HÀNG", shop_options)
        shop_choice = input("Nhập số gian hàng: ").strip()

        if shop_choice in SHOPS:
            shop_name, code, expected_format_count = SHOPS[shop_choice]
            file_path = input("Nhập tên tệp chứa tài khoản: ").strip()
            if not file_path.endswith(".txt"):
                file_path += ".txt"
            upload_accounts(file_path, code, shop_name, expected_format_count)
        else:
            print("Không có gian hàng này!")
    else:
        print("Lựa chọn không hợp lệ!")
