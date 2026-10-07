# cron: 10 12 * * *
# const $ = new Env('联通营业厅签到')
# coding=utf-8
"""中国联通营业厅每日签到（适配呆呆面板）

认证方式优先级（放 .env，任选其一即可）：

  1) UNICOM_TOKEN=token_online[#appId][#YYYY-MM-DD]
  2) UNICOM_COOKIE=完整 Cookie[#YYYY-MM-DD]
  3) UNICOM_ACCOUNT=手机号#登录密码[#appId][#YYYY-MM-DD]

模块（Cookie / ecs_token 可跑的部分）：
  首页签到、领取签到奖励、话费红包、月签有礼、任务中心、
  SigninApp 积分/翻倍/1G 日包、娱乐打卡、沃之树、
  看视频流量、金币抽奖、天天领现金、通通乡村、
  权益超市抽奖、会员中心浏览领积分、沃云手机积分、
  联通云盘（签到/AI/抽奖/校园季/上传大比拼）、沃阅读积分、
  每周一 10:00 抢兑 10 元话费券。

多账号用 & 连接。密码登录若触发短信风控，改用 Cookie 或 token_online。
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import string
import sys
import time
import uuid
from time import sleep
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.Util.Padding import pad

APP_VERSION = "android@12.1000"
DEVICE_MODEL = "M2007J1SC"
APP_UA = (
    "Mozilla/5.0 (Linux; Android 13; M2007J1SC Build/TKQ1.221114.001; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 "
    "Mobile Safari/537.36; unicom{version:android@12.1000,desmobile:0};"
    "devicetype{deviceBrand:Xiaomi,deviceModel:M2007J1SC};OSVersion/13;ltst;"
)
MARKET_H5_UA = APP_UA
MARKET_UA = APP_UA
MARKET_BASE = "https://backward.bol.wo.cn/prod-api"
MARKET_MEMBER_CENTER_PAGE_ID = "s782351687947921408"
MARKET_MEMBER_CENTER_DISTRIBUTE_ID = "D1161369893988319232"
MARKET_MEMBER_CENTER_PARTNERS_ID = "1703"
MARKET_MEMBER_CENTER_CLIENT_TYPE = "marketUnicom"
MARKET_MEMBER_CENTER_TASK_CODE = "s769153426294495232"
_MARKET_JF_CACHE = {"ticket": None, "secretKey": None}
UPHONE_H5API = "https://uphone.wostore.cn/h5api"
UPHONE_CHANNEL = "ST-Wode"
UPHONE_CHANNEL_H5 = "ST-Jingang002"
UPHONE_EDOP_APP_ID = "edop_unicom_68e8fa69"
UPHONE_ACT_SIGN = "Points_Sign_2507"
UPHONE_ACT_OBTAIN = "Points_Obtain_2507"
UPHONE_ACT_EXCHANGE = "Points_Exchange_2507"
UPHONE_OBTAIN_SKIP = frozenset({"012-4", "TASK2026010601"})
UPHONE_APP_UA = (
    "ChinaUnicom4.x/12.13 (com.chinaunicom.mobilebusiness; build:1; iOS 27.0.0) "
    "Alamofire/4.7.3 unicom{version:iphone_c@12.1300}"
)
UPHONE_H5_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko)  unicom{version:iphone_c@12.1300};ltst;OSVersion/27.0"
)
CLOUD_EDOP_APP_ID = "edop_unicom_d67b3e30"
CLOUD_CLIENT_ID = "1001000003"
CLOUD_JF_PARTNERS = "1649"
CLOUD_PAN_SIGN_SECRET = "s8Hf3LqP9xN2vM5bR7tY1wZ4cA6eG0K"
CLOUD_FILEINFO_IV = "wNSOYIB1k1DjY5lA"
CLOUD_LOTTERY_DEFAULT = "MjU="
CAMPUS_ACTIVITY_DEFAULT = "MzU="
CLOUD_BATTLE_DEFAULT = "Mzg="
CLOUD_BATTLE_TOUCHPOINT = "300200030001"
CLOUD_BATTLE_PAGE = "uploadBattle"
CAMPUS_UPLOAD_URL = "https://tjupload.pan.wo.cn/openapi/client/upload2C"
CLOUD_BATTLE_UPLOAD_DEFAULT = "https://hyupload.pan.wo.cn/openapi/client/upload2C"
WOREAD_BASE = "https://10010.woread.com.cn/ng_woread_service/rest"
WOREAD_KEY = b"woreadst^&*12345"
WOREAD_IV = b"16-Bytes--String"
WOREAD_APPID = "10000002"
WOREAD_APPSECRET = "7k1HcDL8RKvc"
WOREAD_JF_PARTNERS = "1706"
WOREAD_SIGN_TASK = "s818795876839563264"
WOREAD_CNTINDEX = 3120941
WOREAD_CHAPTERALLINDEX = 120470473
LOGIN_URL = "https://m.client.10010.com/mobileService/login.htm"
ONLINE_URL = "https://m.client.10010.com/mobileService/onLine.htm"
SIGNIN_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/signin/daySign"
CONTINUOUS_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/signin/getContinuous"
TASK_LIST_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/taskList"
COMPLETE_TASK_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/completeTask"
TASK_REWARD_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/task/getTaskReward"
MONTH_SIGN_URL = "https://activity.10010.com/sixPalaceGridTurntableLottery/floor/getMonthSign"
GET_TASK_IP_URL = "https://m.client.10010.com/taskcallback/topstories/gettaskip"
OPENPLAT_URL = "https://m.client.10010.com/mobileService/openPlatform/openPlatLineNew.htm"
PRIZE_LIST_URL = "https://act.10010.com/SigninApp/new_convert/prizeList"
PRIZE_CONVERT_URL = "https://act.10010.com/SigninApp/convert/prizeConvert"
PRIZE_RESULT_URL = "https://act.10010.com/SigninApp/convert/prizeConvertResult"
TTXC_BASE_URL = "https://epay.10010.com/cu-ca-game-front"
TTXC_APP_BASE_URL = "https://epay.10010.com/cu-ca-app-front"
TTXC_CHANNEL = "225"
TTXC_REFERER = "https://epay.10010.com/cu-ca-game-web/index.html?channel=qdqp"
TTXC_UA = APP_UA
TTXC_NEWBIE_STEPS = ["G01", "G02", "G03", "G03_2", "G04", "G05", "G09", "G10", "G11", "G12"]
TTXC_GARBAGE_WAIT = 8
TTXC_GROW_MAX = 4
TTXC_HARVEST_WAIT = 2

PUBLIC_KEY = '''-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDc+CZK9bBA9IU+gZUOc6
FUGu7yO9WpTNB0PzmgFBh96Mg1WrovD1oqZ+eIF4LjvxKXGOdI79JRdve9
NPhQo07+uqGQgE4imwNnRx7PFtCRryiIEcUoavuNtuRVoBAm6qdB0Srctg
aqGfLgKvZHOnwTjyNqjBUxzMeQlEC2czEMSwIDAQAB
-----END PUBLIC KEY-----'''

SIGNIN_APP_UA = APP_UA


ENV_FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
ENV_DATE_RE = re.compile(r"#(\d{4}-\d{2}-\d{2}|\d{8})\s*$")


def env_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def strip_env_date(value):
    value = (value or "").strip()
    match = ENV_DATE_RE.search(value)
    if match:
        return value[: match.start()].rstrip(), match.group(1)
    return value, ""


def stamp_env_date(value, date_str=None):
    core, _ = strip_env_date(value)
    if not core:
        return value
    return f"{core}#{date_str or env_today()}"


def load_dotenv():
    if not os.path.isfile(ENV_FILE):
        return
    with open(ENV_FILE, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def write_env_key(key, value):
    if not key or value is None:
        return False
    lines = []
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    found = False
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped and stripped.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.environ[key] = value
    return True


def update_env_date(key, raw_value=None, account=None, multi=True):
    current = raw_value if raw_value is not None else (os.getenv(key) or "")
    if not current.strip():
        return False
    today = env_today()
    parts = [p.strip() for p in re.split(r"[&]", current) if p.strip()] if multi else [current.strip()]
    updated = []
    changed = False
    for part in parts:
        core, old_date = strip_env_date(part)
        if account:
            hit = account in core.split("#")
        else:
            hit = True
        if hit:
            stamped = f"{core}#{today}"
            updated.append(stamped)
            if old_date != today or stamped != part:
                changed = True
        else:
            updated.append(part)
    if not changed:
        return False
    joiner = "&" if multi else ""
    new_value = joiner.join(updated)
    if write_env_key(key, new_value):
        print(f"  变量 {key} 已更新日期 {today}")
        return True
    return False


def load_accounts(raw):
    accounts = []
    for item in re.split(r"[&]", raw or ""):
        item, _ = strip_env_date(item.strip())
        if not item:
            continue
        parts = item.split("#")
        if len(parts) < 2:
            print("跳过格式错误的账号（需要 手机号#APP登录密码[#appId]）")
            continue
        phone = parts[0].strip()
        password = parts[1].strip()
        appid = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else ""
        accounts.append((phone, password, appid))
    return accounts


def load_tokens(raw):
    tokens = []
    for item in re.split(r"[&]", raw or ""):
        item, _ = strip_env_date(item.strip())
        if not item:
            continue
        parts = item.split("#")
        token = parts[0].strip()
        appid = parts[1].strip() if len(parts) >= 2 else ""
        if token:
            tokens.append((token, appid))
    return tokens


def rsa_encrypt(text):
    payload = str(text) + "".join(str(random.randint(0, 9)) for _ in range(6))
    rsakey = RSA.importKey(PUBLIC_KEY)
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    return base64.b64encode(cipher.encrypt(payload.encode("utf-8"))).decode("utf-8")


def gen_appid():
    rnd = lambda: str(random.randint(0, 9))
    return (
        f"{rnd()}f{rnd()}af{rnd()}{rnd()}ad{rnd()}"
        "912d306b5053abf90c7ebbb695887bc"
        "870ae0706d573c348539c26c5c0a878641fcc0d3e90acb9be1e6ef858a"
        "59af546f3c826988332376b7d18c8ea2398ee3a9c3db947e2471d32a49"
    ) + rnd() + rnd()


def random_string(length, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for _ in range(length))


def parse_cookie_map(cookie_header):
    mapping = {}
    if not cookie_header:
        return mapping
    for item in cookie_header.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        mapping[k.strip()] = v.strip()
    return mapping


def cookie_get(cookie_header, name, default=""):
    return parse_cookie_map(cookie_header).get(name, default)


def apply_cookie(session, cookie_header):
    for k, v in parse_cookie_map(cookie_header).items():
        session.cookies.set(k, v, domain=".10010.com")


def seed_device_cookies(session, token_online, appid=""):
    tid = uuid.uuid4().hex
    session.cookies.set("TOKENID_COOKIE", "chinaunicom-" + tid, domain=".10010.com")
    session.cookies.set("UNICOM_TOKENID", tid, domain=".10010.com")
    session.cookies.set("sdkuuid", tid, domain=".10010.com")
    session.cookies.set("token_online", token_online, domain=".10010.com")
    if appid:
        session.cookies.set("appId", appid, domain=".10010.com")


def login(session, mobile, passwd, appid):
    if not appid:
        appid = gen_appid()
    payload = {
        "version": APP_VERSION,
        "mobile": rsa_encrypt(mobile),
        "reqtime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deviceModel": DEVICE_MODEL,
        "netWay": "Wifi",
        "isR4": "0",
        "password": rsa_encrypt(passwd),
        "appId": appid,
    }
    headers = {
        "Host": "m.client.10010.com",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "keep-alive",
        "User-Agent": APP_UA,
        "Accept-Language": "zh-cn",
    }
    try:
        resp = session.post(LOGIN_URL, data=payload, headers=headers, timeout=30)
        body = resp.json()
    except Exception as e:
        return False, f"登录请求异常：{e}", ""
    code = str(body.get("code"))
    if code in ("0", "0000") and body.get("token_online"):
        return True, "登录成功", body["token_online"]
    msg = body.get("dsc") or body.get("desc") or json.dumps(body, ensure_ascii=False)
    return False, msg, ""


def online(session, token_online, appid=""):
    data = {
        "isFirstInstall": "1",
        "netWay": "Wifi",
        "version": APP_VERSION,
        "token_online": token_online,
        "provinceChanel": "general",
        "deviceModel": DEVICE_MODEL,
        "step": "dingshi",
        "androidId": uuid.uuid4().hex[:16],
        "reqtime": int(time.time() * 1000),
    }
    if appid:
        data["appId"] = appid
    try:
        resp = session.post(
            ONLINE_URL,
            data=data,
            headers={"User-Agent": APP_UA, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        body = resp.json()
    except Exception as e:
        return False, f"onLine 请求异常：{e}"
    if str(body.get("code")) in ("0", "0000"):
        ecs = body.get("ecs_token")
        if ecs:
            session.cookies.set("ecs_token", ecs, domain=".10010.com")
        desmobile = body.get("desmobile") or ""
        if len(desmobile) == 11 and desmobile.isdigit():
            session.cookies.set("c_mobile", desmobile, domain=".10010.com")
        return True, "在线登录成功"
    return False, body.get("msg") or body.get("desc") or json.dumps(body, ensure_ascii=False)


def base_headers(cookie_header=None, extra=None):
    headers = {
        "user-agent": APP_UA,
        "referer": "https://img.client.10010.com",
        "origin": "https://img.client.10010.com",
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json, text/plain, */*",
    }
    if cookie_header:
        headers["cookie"] = cookie_header
    if extra:
        headers.update(extra)
    return headers


def api(session, method, url, cookie_header=None, timeout=15, extra_headers=None, **kwargs):
    headers = base_headers(cookie_header, extra_headers)
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))
    try:
        resp = session.request(method, url, headers=headers, timeout=timeout, **kwargs)
        return resp
    except Exception as e:
        print(f"  请求异常 {url}: {e}")
        return None


def safe_json(resp):
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def signin(session, cookie_header=None):
    last = None
    for attempt in range(1, 4):
        resp = api(session, "POST", SIGNIN_URL, cookie_header, data={})
        body = safe_json(resp)
        if body is None:
            last = "签到请求失败"
            sleep(attempt * 2)
            continue
        code = str(body.get("code"))
        desc = body.get("desc") or body.get("dsc") or ""
        if code == "0000":
            data = body.get("data") or {}
            reward = data.get("redSignMessage") or ""
            status = data.get("statusDesc") or ""
            msg = f"签到成功 [{status}]{reward}"
            print(f"  {msg}")
            return True, reward or "签到成功"
        if code == "0002" and "已经签到" in desc:
            print("  今日已签到")
            return True, "今日已签到"
        print(f"  第 {attempt} 次签到失败：[code={code}] {desc}")
        last = f"[code={code}] {desc}"
        if code == "0001":
            break
        sleep(attempt * 2)
    return False, last


def sign_get_continuous(session, cookie_header=None):
    print("==== 首页签到 ====")
    imei = cookie_get(cookie_header, "sdkuuid") or uuid.uuid4().hex
    resp = api(
        session,
        "GET",
        CONTINUOUS_URL,
        cookie_header,
        params={"taskId": "", "channel": "wode", "imei": imei},
    )
    body = safe_json(resp)
    if not body:
        print("  查询签到状态失败")
        return signin(session, cookie_header)
    code = str(body.get("code"))
    if code != "0000":
        print(f"  查询签到状态失败[{code}]: {body.get('desc', '')}")
        return signin(session, cookie_header)
    signed = (body.get("data") or {}).get("todayIsSignIn", "n") == "y"
    print(f"  今天{'已' if signed else '未'}签到")
    if signed:
        return True, "今日已签到"
    sleep(1)
    return signin(session, cookie_header)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def session_cookie(session, name, cookie_header=None):
    val = session.cookies.get(name) or ""
    if val:
        return val
    return cookie_get(cookie_header, name)


def sign_claim_signin_rewards(session, cookie_header=None):
    print("==== 领取签到奖励 ====")
    extra = {"referer": "https://img.client.10010.com/"}
    claimed = 0
    for type_code in ("1", "2"):
        resp = api(
            session,
            "GET",
            TASK_LIST_URL,
            cookie_header,
            params={"type": type_code},
            extra_headers=extra,
            timeout=10,
        )
        body = safe_json(resp)
        if not body or str(body.get("code")) != "0000":
            continue
        tag_list = (body.get("data") or {}).get("tagList", []) or []
        task_list = (body.get("data") or {}).get("taskList", []) or []
        all_tasks = task_list + [t for tag in tag_list for t in tag.get("taskDTOList", [])]
        for task in [t for t in all_tasks if t]:
            name = task.get("taskName") or ""
            if str(task.get("taskState")) != "0":
                continue
            if type_code == "2" and "签到" not in name:
                continue
            print(f"  领取签到奖励 [{name}]")
            sign_get_task_reward(session, cookie_header, task.get("id"))
            claimed += 1
            sleep(1)
    if claimed == 0:
        print("  暂无可领取的签到奖励")
    return claimed


def sign_grab_execute(session, cookie_header, candidate):
    extra = {
        "Origin": "https://img.client.10010.com",
        "Referer": "https://img.client.10010.com/",
        "X-Requested-With": "com.sinovatech.unicom.ui",
    }
    grab_url = (os.getenv("UNICOM_GRAB_URL") or "").strip() or PRIZE_CONVERT_URL
    for i in range(1, 6):
        print(f"  [第{i}次] 发起兑换 {candidate['name']}...")
        resp = api(
            session,
            "POST",
            grab_url,
            cookie_header,
            data={"product_id": candidate["id"], "typeCode": candidate["typeCode"]},
            extra_headers=extra,
        )
        body = safe_json(resp)
        if not body:
            sleep(0.2)
            continue
        uuid_val = (body.get("data") or {}).get("uuid")
        status = str(body.get("status"))
        if status == "0000" and uuid_val:
            print(f"  提交成功，工单 {uuid_val}，查询结果...")
            check = api(
                session,
                "POST",
                PRIZE_RESULT_URL,
                cookie_header,
                data={"uuid": uuid_val},
                extra_headers=extra,
            )
            final = safe_json(check) or {}
            if str(final.get("status")) == "0000":
                print(f"  抢兑成功: {candidate['name']}")
                return True
            err_code = (final.get("data") or {}).get("errorCode", "")
            msg = final.get("msg") or final.get("message") or ""
            print(f"  抢兑失败[{final.get('status')}] {err_code} {msg}")
        else:
            print(f"  提交结果: {body.get('msg') or body.get('message') or status}")
        sleep(0.2)
    return False


def sign_grab_coupon(session, cookie_header=None, amount=None, wait=True):
    amount = str(amount or os.getenv("UNICOM_GRAB_AMOUNT") or "10")
    print(f"==== 抢兑 {amount} 元话费券 ====")
    extra = {"Origin": "https://img.client.10010.com"}
    resp = api(session, "POST", PRIZE_LIST_URL, cookie_header, extra_headers=extra)
    body = safe_json(resp)
    if not body or str(body.get("status")) != "0000":
        print(f"  获取奖品列表失败: {(body or {}).get('msg', '')}")
        return False
    details = (body.get("data") or {}).get("datails") or {}
    tab_items = details.get("tabItems") or []
    candidates = []
    now = datetime.datetime.now()
    for tab in tab_items:
        products = tab.get("timeLimitQuanListData") or []
        round_time_str = tab.get("time") or ""
        round_date = None
        try:
            if round_time_str and ":" in round_time_str:
                date_str = now.strftime("%Y/%m/%d")
                full_time_str = f"{date_str} {round_time_str}"
                if len(round_time_str) <= 8:
                    round_date = datetime.datetime.strptime(full_time_str, "%Y/%m/%d %H:%M")
                else:
                    round_date = datetime.datetime.strptime(round_time_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            round_date = None
        for item in products:
            p_name = item.get("product_name") or ""
            if amount in p_name and ("元" in p_name or "话费" in p_name):
                print(f"  发现目标: {p_name} (场次 {round_time_str})")
                candidates.append({
                    "id": item.get("product_id"),
                    "name": p_name,
                    "typeCode": item.get("type_code") or "0",
                    "timeStr": round_time_str,
                    "startTime": round_date,
                })
    if not candidates:
        print(f"  未匹配到 {amount} 元话费券")
        return False
    best = None
    min_diff = float("inf")
    now = datetime.datetime.now()
    for cand in candidates:
        start_time = cand["startTime"]
        if not start_time:
            continue
        diff = (start_time - now).total_seconds()
        if diff > 0:
            score = diff
        elif diff > -600:
            score = abs(diff) + 10000
        else:
            score = abs(diff) + 90000
        if score < min_diff:
            min_diff = score
            best = cand
    if not best:
        best = candidates[0]
    print(f"  锁定场次: [{best['timeStr']}] {best['name']}")
    if wait and best.get("startTime"):
        wait_seconds = (best["startTime"] - datetime.datetime.now()).total_seconds()
        if wait_seconds > 180:
            print(f"  距离开抢还有 {wait_seconds:.0f}s，大于3分钟，跳过等待")
            return False
        if wait_seconds > 0:
            print(f"  等待开抢 {wait_seconds:.1f}s")
            while (best["startTime"] - datetime.datetime.now()).total_seconds() > 0.5:
                sleep(0.5)
    return sign_grab_execute(session, cookie_header, best)


def is_weekly_grab_window(now=None):
    now = now or datetime.datetime.now()
    return now.weekday() == 0 and now.hour == 10


def sign_get_telephone(session, cookie_header=None, is_initial=False, ctx=None):
    resp = api(session, "POST", "https://act.10010.com/SigninApp/convert/getTelephone", cookie_header, data={})
    body = safe_json(resp)
    if not body or str(body.get("status")) != "0000" or not body.get("data"):
        if body:
            print(f"  话费红包查询失败[{body.get('status')}]: {body.get('msg', '')}")
        return None
    try:
        amount = float((body.get("data") or {}).get("telephone", 0) or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if ctx is None:
        ctx = {}
    if is_initial:
        ctx["sign_initial_amount"] = amount
        print(f"  话费红包: 运行前总额 {amount:.2f}元")
        return amount
    if "sign_initial_amount" in ctx:
        print(f"  话费红包: 本次运行增加 {amount - ctx['sign_initial_amount']:.2f}元")
    msg = f"  话费红包: 总额 {amount:.2f}元"
    try:
        exp_num = float((body.get("data") or {}).get("needexpNumber", 0) or 0)
    except (TypeError, ValueError):
        exp_num = 0.0
    if exp_num > 0:
        month = (body.get("data") or {}).get("month", "")
        msg += f"，其中 {body['data'].get('needexpNumber', '0')}元 将于 {month}月底到期"
    print(msg)
    return amount


def gettaskip(session, cookie_header=None, mobile=""):
    order_id = random_string(32, string.ascii_uppercase + string.digits)
    try:
        api(
            session,
            "POST",
            GET_TASK_IP_URL,
            cookie_header,
            data={"mobile": mobile or "", "orderId": order_id},
            timeout=8,
        )
    except Exception:
        pass
    return order_id


def sign_do_task(session, cookie_header, task, mobile=""):
    url = task.get("url") or ""
    name = task.get("taskName") or ""
    if url != "1" and url.startswith("http"):
        api(session, "GET", url, cookie_header)
        print(f"  任务中心: 浏览页面 [{name}]")
        sleep(random.uniform(5, 7))
    order_id = gettaskip(session, cookie_header, mobile)
    resp = api(
        session,
        "GET",
        COMPLETE_TASK_URL,
        cookie_header,
        params={"taskId": task.get("id"), "orderId": order_id, "systemCode": "QDQD"},
    )
    body = safe_json(resp)
    if not body:
        print(f"  任务中心: 任务 [{name}] 完成请求失败")
        return
    code = str(body.get("code"))
    if code == "0000":
        print(f"  任务中心: 任务 [{name}] 已完成")
    else:
        print(f"  任务中心: 任务 [{name}] 完成失败[{code}]: {body.get('desc', '')}")


def sign_get_task_reward(session, cookie_header, task_id, task_type=None, record_id=None):
    params = {"taskId": task_id}
    extra = None
    if task_type is not None:
        params["taskType"] = task_type
        extra = {"referer": "https://img.client.10010.com/"}
    if record_id is not None:
        params["id"] = record_id
    resp = api(session, "GET", TASK_REWARD_URL, cookie_header, params=params, extra_headers=extra)
    body = safe_json(resp)
    if not body:
        print("  领取奖励请求失败")
        return
    code = str(body.get("code"))
    data = body.get("data") or {}
    if code == "0000" and str(data.get("code", "")) == "0000":
        prize = f"[{data.get('prizeName', '')}] {data.get('prizeNameRed', '')}".strip()
        print(f"  领取奖励: {prize or data.get('statusDesc', '领取成功')}")
    else:
        print(f"  领取奖励失败[{data.get('code') or code}]: {data.get('desc') or body.get('desc', '')}")


def sign_get_task_list(session, cookie_header=None, mobile=""):
    print("==== 任务中心 ====")
    extra = {"referer": "https://img.client.10010.com/"}
    for i in range(12):
        resp = api(session, "GET", TASK_LIST_URL, cookie_header, params={"type": "2"}, extra_headers=extra, timeout=10)
        body = safe_json(resp)
        if not body:
            return
        code = str(body.get("code"))
        if code == "0329" or "火爆" in str(body.get("desc", "")):
            print("  任务中心: 系统繁忙(0329)，停止后续尝试")
            break
        if code != "0000":
            print(f"  任务中心: 获取任务列表失败[{code}]: {body.get('desc', '')}")
            return
        tag_list = (body.get("data") or {}).get("tagList", []) or []
        task_list = (body.get("data") or {}).get("taskList", []) or []
        all_tasks = task_list + [t for tag in tag_list for t in tag.get("taskDTOList", [])]
        all_tasks = [t for t in all_tasks if t]
        if not all_tasks:
            if i == 0:
                print("  任务中心: 当前无任何任务")
            break
        do_task = next((t for t in all_tasks if t.get("taskState") == "1" and t.get("taskType") == "5"), None)
        if do_task:
            print(f"  任务中心: 开始执行 [{do_task.get('taskName')}]")
            sign_do_task(session, cookie_header, do_task, mobile)
            sleep(3)
            continue
        claim_task = next((t for t in all_tasks if t.get("taskState") == "0"), None)
        if claim_task:
            print(f"  任务中心: 领取 [{claim_task.get('taskName')}]")
            sign_get_task_reward(session, cookie_header, claim_task.get("id"))
            sleep(2)
            continue
        if i == 0:
            print("  任务中心: 没有可执行或可领取的任务")
        else:
            print("  任务中心: 所有任务处理完毕")
        break


def sign_month_sign_gift(session, cookie_header=None):
    print("==== 月签有礼 ====")
    extra = {"referer": "https://img.client.10010.com/"}
    resp = api(session, "GET", MONTH_SIGN_URL, cookie_header, extra_headers=extra)
    body = safe_json(resp)
    if not body or str(body.get("code")) != "0000":
        desc = (body or {}).get("desc", "")
        print(f"  月签有礼: 查询失败[{(body or {}).get('code')}]: {desc}")
        return
    task_list = (body.get("data") or {}).get("taskList", []) or []
    if not task_list:
        print("  月签有礼: 暂无月签任务")
        return
    claim_tasks = [t for t in task_list if str(t.get("taskStatus")) == "1" and t.get("taskId") and t.get("id")]
    claimed_count = sum(1 for t in task_list if str(t.get("taskStatus")) == "2")
    if not claim_tasks:
        print(f"  月签有礼: 暂无可领取奖励，已领取 {claimed_count}/{len(task_list)}")
        return
    for task in claim_tasks:
        name = task.get("taskName") or "月签奖励"
        print(f"  月签有礼: 领取 [{name}]")
        sign_get_task_reward(
            session,
            cookie_header,
            task.get("taskId"),
            task_type="30",
            record_id=task.get("id"),
        )
        sleep(1)


def sign_query_my_prizes(session, cookie_header=None):
    print("==== 账户明细 ====")
    resp = api(
        session,
        "POST",
        "https://act.10010.com/SigninApp/convert/phoneDetails",
        cookie_header,
        data={"log_type": "1", "number": "1", "list_num": ""},
        extra_headers={"origin": "https://img.client.10010.com"},
    )
    body = safe_json(resp)
    if not body or str(body.get("status")) != "0000":
        return
    data = (body.get("data") or {}).get("detailedBO", []) or []
    logged = 0
    for item in data:
        if logged >= 5:
            break
        remark = item.get("remark", "")
        buss_name = item.get("from_bussname", "")
        if "兑换" not in remark and "兑换" not in buss_name:
            continue
        if logged == 0:
            print("  最近兑换记录:")
        amount = item.get("booksNumber") or item.get("books_number") or "0"
        print(f"    {item.get('order_time', '')} | {remark} (变动:{amount})")
        logged += 1
    if logged == 0:
        print("  暂无兑换记录")


def points_sign(session, cookie_header=None):
    print("==== SigninApp 积分签到 ====")
    extra = {
        "user-agent": SIGNIN_APP_UA,
        "referer": "https://img.client.10010.com",
        "origin": "https://img.client.10010.com",
    }

    def post(path, data=None):
        return api(
            session,
            "POST",
            f"https://act.10010.com/SigninApp/{path}",
            cookie_header,
            data=data or {},
            extra_headers=extra,
        )

    res0 = safe_json(post("signin/getIntegral"))
    if res0 and str(res0.get("status")) == "0000":
        print(f"  签到前积分: {(res0.get('data') or {}).get('integralTotal')}")
    res1 = safe_json(post("signin/getContinuous"))
    sleep(2)
    today_signed = ""
    if res1:
        today_signed = str((res1.get("data") or {}).get("todaySigned", ""))
    if today_signed == "1":
        res2 = safe_json(post("signin/daySign"))
        if res2:
            print(f"  积分签到: {res2.get('msg') or res2.get('status') or '已请求'}")
    else:
        print("  积分签到: 今天已签到")
    sleep(2)
    res3 = safe_json(post("signin/bannerAdPlayingLogo"))
    if res3 and str(res3.get("status")) == "0000":
        print("  积分翻倍成功")
    elif res3:
        print(f"  积分翻倍: {res3.get('msg') or ''}")
    res4 = safe_json(post("signin/getIntegral"))
    if res4 and str(res4.get("status")) == "0000":
        print(f"  签到后积分: {(res4.get('data') or {}).get('integralTotal')}")
    post("doTask/finishVideo")
    post("doTask/getTaskInfo")
    res7 = safe_json(post("doTask/getPrize"))
    if res7 and str(res7.get("status")) == "0000":
        print("  1G流量日包领取成功")
    elif res7:
        print(f"  1G流量日包: {res7.get('msg') or res7.get('status') or '失败'}")


def extra_daily_tasks(session, cookie_header=None):
    print("==== 娱乐打卡 / 沃之树 / 流量 / 金币抽奖 ====")
    extra = {
        "user-agent": SIGNIN_APP_UA,
        "referer": "https://img.client.10010.com",
        "origin": "https://img.client.10010.com",
    }
    data1 = {"methodType": "signin", "clientVersion": "12.1000", "deviceType": "Android"}
    res1 = api(
        session,
        "POST",
        "https://m.client.10010.com/producGame_signin",
        cookie_header,
        data=data1,
        extra_headers=extra,
    )
    body1 = safe_json(res1)
    if body1:
        print(f"  每日打卡: {body1.get('respDesc') or body1.get('msg') or ''}")
    res5 = api(
        session,
        "POST",
        "https://m.client.10010.com/mactivity/arbordayJson/arbor/3/0/3/grow.htm",
        cookie_header,
        extra_headers=extra,
    )
    body5 = safe_json(res5)
    if body5:
        print(f"  每日浇水: {body5.get('msg') or body5.get('desc') or ''}")
    print("  看视频/下载APP流量奖励...")
    for _ in range(3):
        api(session, "POST", "https://act.10010.com/SigninApp/mySignin/addFlow", cookie_header, data={"stepflag": 22}, extra_headers=extra)
        sleep(2)
        api(session, "POST", "https://act.10010.com/SigninApp/mySignin/addFlow", cookie_header, data={"stepflag": 23}, extra_headers=extra)
    print("  看视频流量任务完成")
    res7 = api(
        session,
        "POST",
        "https://m.client.10010.com/dailylottery/static/textdl/userLogin",
        cookie_header,
        extra_headers=extra,
    )
    if res7 is None:
        print("  金币抽奖: 登录页请求失败")
        return
    found = re.findall(r"encryptmobile=(.+?)';", res7.text or "")
    if not found:
        print("  金币抽奖: 未拿到 encryptmobile，跳过")
        return
    data8 = {"usernumberofjsp": found[0], "flag": "convert"}
    for _ in range(3):
        res8 = api(
            session,
            "POST",
            "https://m.client.10010.com/dailylottery/static/doubleball/choujiang",
            cookie_header,
            data=data8,
            extra_headers=extra,
        )
        body8 = safe_json(res8)
        if body8:
            print(f"  金币抽奖: {body8.get('RspMsg') or body8.get('msg') or ''}")
        sleep(2)


def open_plat_line_new(session, cookie_header, to_url):
    try:
        headers = base_headers(cookie_header)
        resp = session.get(OPENPLAT_URL, params={"to_url": to_url}, headers=headers, allow_redirects=False, timeout=15)
    except Exception as e:
        print(f"  openPlatLineNew 异常: {e}")
        return None
    loc = resp.headers.get("Location") if resp is not None else None
    if resp is not None and resp.status_code in (301, 302, 303, 307, 308) and loc:
        qs = parse_qs(urlparse(loc).query)
        ticket = (qs.get("ticket") or [""])[0]
        type_val = (qs.get("type") or [""])[0]
        if ticket:
            return {"ticket": ticket, "type": type_val, "loc": loc}
        print("  openPlatLineNew: 重定向中无 ticket")
        return None
    code = resp.status_code if resp is not None else "?"
    print(f"  openPlatLineNew: 状态码 {code}")
    return None


def parse_jwt_payload(token):
    try:
        parts = (token or "").split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def market_signature_headers(user_token, query_string="", json_body=""):
    token = (user_token or "").replace("Bearer ", "").strip()
    parsed = parse_jwt_payload(token)
    login_id = parsed.get("loginId", "")
    if not login_id:
        return {}
    app_secret = hashlib.md5(f"al:ak:{login_id}".encode("utf-8")).hexdigest()
    nonce = str(uuid.uuid4())
    message = f"{login_id}{app_secret}{nonce}{query_string or ''}{json_body or ''}"
    signature = base64.b64encode(
        hmac.new(app_secret.encode("utf-8"), message.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    return {
        "X-User-Id": login_id,
        "X-Nonce": nonce,
        "X-Timestamp": str(int(time.time() * 1000)),
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


def market_headers(user_token):
    return {
        "User-Agent": MARKET_UA,
        "Authorization": f"Bearer {(user_token or '').replace('Bearer ', '').strip()}",
        "Content-Type": "application/json",
        "X-Requested-With": "com.sinovatech.unicom.ui",
    }


def market_get_user_token(session, ticket):
    url = f"{MARKET_BASE}/auth/marketUnicomLogin?ticket={ticket}"
    headers = {"User-Agent": MARKET_UA, "Connection": "Keep-Alive", "Accept-Encoding": "gzip"}
    for attempt in range(1, 4):
        try:
            res = session.post(url, headers=headers, timeout=30).json()
            if str(res.get("code")) == "200":
                data = res.get("data")
                token = data.get("token") if isinstance(data, dict) else data
                if token:
                    return token
            print(f"  权益超市: 获取 userToken 失败: {res.get('msg') or res.get('code')}")
        except Exception as e:
            print(f"  权益超市: 获取 userToken 异常: {e}")
        if attempt < 3:
            sleep(5)
    return None


def market_user_raffle(session, user_token):
    try:
        query_string = f"id=12&channel=unicomTab&timeVerRan={int(time.time() * 1000)}"
        headers = market_headers(user_token)
        headers.update(market_signature_headers(user_token, query_string, "{}"))
        headers["Referer"] = "https://contact.bol.wo.cn/market"
        res = session.post(
            f"{MARKET_BASE}/promotion/home/raffleActivity/userRaffle?{query_string}",
            headers=headers, data="{}", timeout=15,
        ).json()
        if str(res.get("code")) == "200":
            data = res.get("data") or {}
            prize_name = data.get("prizesName", "") if isinstance(data, dict) else ""
            message = (data.get("message") if isinstance(data, dict) else "") or res.get("msg") or ""
            if prize_name and "谢谢参与" not in prize_name:
                print(f"  权益超市: 抽奖成功: {prize_name}")
            else:
                print(f"  权益超市: 未中奖: {message}")
            return True
        print(f"  权益超市: 抽奖失败: {res.get('msg') or res.get('code')}")
        return False
    except Exception as e:
        print(f"  权益超市: 抽奖异常: {e}")
        return False


def market_get_points_ticket(session, user_token):
    try:
        res = session.get(
            f"{MARKET_BASE}/auth/getTicket?channel=pointsPlatform",
            headers={
                "Authorization": f"Bearer {(user_token or '').replace('Bearer ', '').strip()}",
                "User-Agent": MARKET_UA,
            },
            timeout=15,
        ).json()
        if str(res.get("code")) == "200" and res.get("data"):
            return res.get("data")
        print(f"  会员中心: 获取 points ticket 失败: {res.get('msg') or res}")
    except Exception as e:
        print(f"  会员中心: 获取 points ticket 异常: {e}")
    return None


def market_member_center_base_headers(points_ticket):
    referer = (
        f"https://m.jf.10010.com/ts-mobile/well/{MARKET_MEMBER_CENTER_PAGE_ID}"
        f"?distributeId={MARKET_MEMBER_CENTER_DISTRIBUTE_ID}"
        f"&partnersId={MARKET_MEMBER_CENTER_PARTNERS_ID}"
        f"&clientType={MARKET_MEMBER_CENTER_CLIENT_TYPE}"
        f"&ticket={points_ticket}"
    )
    return {
        "origin": "https://m.jf.10010.com",
        "clienttype": MARKET_MEMBER_CENTER_CLIENT_TYPE,
        "ticket": points_ticket,
        "partnersid": MARKET_MEMBER_CENTER_PARTNERS_ID,
        "content-type": "application/json;charset=UTF-8",
        "pageid": MARKET_MEMBER_CENTER_PAGE_ID,
        "Accept": "application/json, text/plain, */*",
        "Referer": referer,
        "User-Agent": MARKET_H5_UA,
        "X-Requested-With": "com.sinovatech.unicom.ui",
    }


def market_get_secret_key_jf(session, points_ticket):
    if _MARKET_JF_CACHE.get("secretKey") and _MARKET_JF_CACHE.get("ticket") == points_ticket:
        return _MARKET_JF_CACHE["secretKey"]
    try:
        res = session.get(
            "https://m.jf.10010.com/jf-external-application/jftask/getSecretKey",
            headers=market_member_center_base_headers(points_ticket),
            timeout=10,
        ).json()
        secret = (res.get("data") or {}).get("secretKey")
        if str(res.get("code")) == "0000" and secret:
            _MARKET_JF_CACHE["ticket"] = points_ticket
            _MARKET_JF_CACHE["secretKey"] = secret.encode("utf-8")
            return _MARKET_JF_CACHE["secretKey"]
        print(f"  会员中心: getSecretKey 失败: {res}")
    except Exception as e:
        print(f"  会员中心: getSecretKey 异常: {e}")
    return None


def market_build_signature_headers_jf(session, points_ticket):
    secret_key = market_get_secret_key_jf(session, points_ticket)
    if not secret_key:
        return {}
    request_ts = str(round(time.time() * 1000))
    nonce = "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyz", k=8))
    signature = hmac.new(secret_key, f"{nonce}{request_ts}".encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "x-request-timestamp": request_ts,
        "x-request-nonce": nonce,
        "x-request-signature": signature,
    }


def market_member_center_headers(session, points_ticket, with_sign=False):
    headers = market_member_center_base_headers(points_ticket)
    if with_sign:
        headers.update(market_build_signature_headers_jf(session, points_ticket))
    return headers


def market_prepare_member_center_context(session, points_ticket):
    try:
        session.post(
            "https://m.jf.10010.com/jf-external-application/page/query",
            json={
                "activityId": MARKET_MEMBER_CENTER_PAGE_ID,
                "distributeId": MARKET_MEMBER_CENTER_DISTRIBUTE_ID,
                "partnersId": MARKET_MEMBER_CENTER_PARTNERS_ID,
            },
            headers=market_member_center_headers(session, points_ticket, with_sign=True),
            timeout=10,
        )
    except Exception as e:
        print(f"  会员中心: page/query 预热异常: {e}")
    try:
        session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/userInfo",
            json={},
            headers=market_member_center_headers(session, points_ticket, with_sign=True),
            timeout=10,
        )
    except Exception as e:
        print(f"  会员中心: userInfo 预热异常: {e}")


def market_member_center_finish_code(task):
    return safe_int(task.get("finish", task.get("status", 0)), 0)


def market_member_center_finish_text(task):
    finish_text = str(task.get("finishText", "")).strip()
    if finish_text:
        return finish_text
    return {
        0: "未完成",
        99: "待领取",
        100: "已领取",
    }.get(market_member_center_finish_code(task), "未知状态")


def market_query_member_center_task(session, points_ticket):
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/taskDetail",
            json={},
            headers=market_member_center_headers(session, points_ticket, with_sign=True),
            timeout=10,
        ).json()
        if str(res.get("code")) != "0000":
            print(f"  会员中心: 查询任务失败: {res}")
            return None
        task_list = ((res.get("data") or {}).get("taskDetail") or {}).get("taskList") or []
        return next(
            (task for task in task_list if str(task.get("taskCode")) == MARKET_MEMBER_CENTER_TASK_CODE),
            None,
        )
    except Exception as e:
        print(f"  会员中心: 查询任务异常: {e}")
        return None


def market_wait_member_center_task_state(session, points_ticket, expected_codes, attempts=4, delay=2):
    task = None
    for idx in range(1, attempts + 1):
        task = market_query_member_center_task(session, points_ticket)
        if task:
            finish_code = market_member_center_finish_code(task)
            finish_text = market_member_center_finish_text(task)
            text_matches = (
                (finish_text == "待领取" and 99 in expected_codes)
                or (finish_text == "已领取" and 100 in expected_codes)
            )
            if finish_code in expected_codes or text_matches:
                return task
            print(
                f"  会员中心: 第{idx}次回查状态 {finish_text}/{finish_code}，"
                f"本月进度 {safe_int(task.get('finishCount'), 0)}/{safe_int(task.get('needCount'), 0)}"
            )
        if idx < attempts:
            sleep(delay)
            market_prepare_member_center_context(session, points_ticket)
    return task


def market_mark_member_center_browse_done(session, user_token, task_fix_id):
    try:
        token = (user_token or "").replace("Bearer ", "").strip()
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "https://contact.bol.wo.cn",
            "Referer": "https://contact.bol.wo.cn/",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": MARKET_H5_UA,
            "X-Requested-With": "com.sinovatech.unicom.ui",
        }
        detail = session.get(
            f"{MARKET_BASE}/promotion/activityTask/getActivityTaskDetailByFixId?taskFixId={task_fix_id}",
            headers=headers,
            timeout=10,
        ).json()
        if str(detail.get("code")) != "200":
            print(f"  会员中心: 获取任务详情失败: {detail.get('msg') or detail}")
            return False
        task_data = detail.get("data") or {}
        check_key = task_data.get("param1")
        wait_seconds = max(safe_int(task_data.get("content"), 17), 15)
        if not check_key:
            print("  会员中心: 未拿到 checkKey，跳过浏览任务")
            return False
        print(f"  会员中心: 模拟浏览 {wait_seconds} 秒")
        sleep(wait_seconds)
        check = session.post(
            f"{MARKET_BASE}/promotion/activityTaskShare/checkView?checkKey={check_key}",
            json={},
            headers=headers,
            timeout=10,
        ).json()
        if str(check.get("code")) == "200" and check.get("data") is True:
            print("  会员中心: 浏览完成，任务已进入待领取")
            return True
        print(f"  会员中心: checkView 失败: {check.get('msg') or check}")
    except Exception as e:
        print(f"  会员中心: 浏览任务异常: {e}")
    return False


def market_receive_member_center_points(session, points_ticket):
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jfmarkettask/receive",
            json={"taskCode": MARKET_MEMBER_CENTER_TASK_CODE},
            headers=market_member_center_headers(session, points_ticket, with_sign=True),
            timeout=10,
        ).json()
        if str(res.get("code")) == "0000":
            score = (res.get("data") or {}).get("score", "未知积分")
            title = (res.get("data") or {}).get("title", "领取成功")
            print(f"  会员中心: {title}，获得 {score}")
            return True
        print(f"  会员中心: 领取失败: {res.get('msg') or res}")
    except Exception as e:
        print(f"  会员中心: 领取异常: {e}")
    return False


def market_do_monthly_view_tasks(session, user_token):
    token = (user_token or "").replace("Bearer ", "").strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": MARKET_H5_UA,
        "Origin": "https://contact.bol.wo.cn",
        "Referer": "https://contact.bol.wo.cn/",
        "Content-Type": "application/json",
        "X-Requested-With": "com.sinovatech.unicom.ui",
    }
    try:
        res = session.get(
            f"{MARKET_BASE}/promotion/activityTask/getAllActivityTasks?activityId=12",
            headers=headers,
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  权益超市任务: 获取列表异常: {e}")
        return
    if str(res.get("code")) != "200":
        print(f"  权益超市任务: 获取列表失败: {res.get('msg') or res.get('code')}")
        return
    tasks = (res.get("data") or {}).get("activityTaskUserDetailVOList") or []
    for task in tasks:
        name = task.get("name") or ""
        param = task.get("param1") or ""
        triggered = safe_int(task.get("triggeredTime"), 0)
        trigger = safe_int(task.get("triggerTime"), 0)
        if any(k in name for k in ("购买", "秒杀", "分享")):
            continue
        if trigger and triggered >= trigger:
            print(f"  权益超市任务: {name} [已完成]")
            continue
        if not param:
            continue
        if not any(k in name for k in ("浏览", "查看")):
            continue
        try:
            check = session.post(
                f"{MARKET_BASE}/promotion/activityTaskShare/checkView?checkKey={param}",
                json={},
                headers=headers,
                timeout=15,
            ).json()
            if str(check.get("code")) == "200":
                print(f"  权益超市任务: {name} [浏览成功]")
            else:
                print(f"  权益超市任务: {name} [失败] {check.get('msg') or check.get('code')}")
        except Exception as e:
            print(f"  权益超市任务: {name} [异常] {e}")
        sleep(1)


def market_member_center_task(session, user_token):
    print("==== 会员中心浏览领积分 ====")
    market_do_monthly_view_tasks(session, user_token)
    points_ticket = market_get_points_ticket(session, user_token)
    if not points_ticket:
        return
    market_prepare_member_center_context(session, points_ticket)
    task = market_query_member_center_task(session, points_ticket)
    if not task:
        print("  会员中心: 活动页已失效或本月无浏览积分任务，跳过")
        return
    finish_code = market_member_center_finish_code(task)
    finish_text = market_member_center_finish_text(task)
    finish_count = safe_int(task.get("finishCount"), 0)
    need_count = safe_int(task.get("needCount"), 0)
    print(f"  会员中心: 当前状态 {finish_text}/{finish_code}，本月进度 {finish_count}/{need_count}")
    if need_count and finish_count >= need_count:
        print("  会员中心: 本月次数已达上限")
        return
    if finish_code == 100 or finish_text == "已领取":
        print("  会员中心: 今日已领取，跳过")
        return
    if finish_code == 0 or finish_text == "未完成":
        jump_url = str(task.get("jumpUrl", "")).strip()
        match = re.search(r"taskFixId=(\d+)", jump_url)
        task_fix_id = match.group(1) if match else "90"
        if not market_mark_member_center_browse_done(session, user_token, task_fix_id):
            return
        market_prepare_member_center_context(session, points_ticket)
        task = market_wait_member_center_task_state(session, points_ticket, {99, 100}, attempts=4, delay=2)
        if not task:
            return
        finish_code = market_member_center_finish_code(task)
        finish_text = market_member_center_finish_text(task)
        print(
            f"  会员中心: 浏览后状态 {finish_text}/{finish_code}，"
            f"本月进度 {safe_int(task.get('finishCount'), 0)}/{safe_int(task.get('needCount'), 0)}"
        )
    if finish_code == 99 or finish_text == "待领取":
        market_receive_member_center_points(session, points_ticket)
    elif finish_code != 100:
        print("  会员中心: 状态未及时刷新，尝试直接领奖")
        if not market_receive_member_center_points(session, points_ticket):
            print("  会员中心: 直接领奖失败，跳过")


def market_rights_lottery(session, cookie_header=None):
    print("==== 权益超市抽奖 ====")
    try:
        ticket_res = open_plat_line_new(session, cookie_header, "https://contact.bol.wo.cn/market")
    except Exception as e:
        print(f"  权益超市: 获取 ticket 异常: {e}")
        return
    ticket = (ticket_res or {}).get("ticket")
    if not ticket:
        print("  权益超市: 获取 ticket 失败，跳过")
        return
    user_token = market_get_user_token(session, ticket)
    if not user_token:
        print("  权益超市: 获取 userToken 失败，跳过")
        return

    count = 0
    try:
        query_string = f"id=12&channel=unicomTab&timeVerRan={int(time.time() * 1000)}"
        headers = market_headers(user_token)
        headers.update(market_signature_headers(user_token, query_string, "{}"))
        headers["Referer"] = "https://contact.bol.wo.cn/market"
        res = session.post(
            f"{MARKET_BASE}/promotion/home/raffleActivity/getUserRaffleCountExt?{query_string}",
            headers=headers, data="{}", timeout=15,
        ).json()
        if str(res.get("code")) == "200":
            data = res.get("data")
            count = int(data.get("raffleCount") or 0) if isinstance(data, dict) else int(data or 0)
        else:
            print(f"  权益超市: 查询抽奖次数失败: {res.get('msg') or res.get('code')}")
            count = 0
    except Exception as e:
        print(f"  权益超市: 查询抽奖次数异常: {e}")
        count = 0

    if count <= 0:
        print("  权益超市: 当前无抽奖次数")
    else:
        print(f"  权益超市: 当前抽奖次数 {count}")
        for i in range(count):
            print(f"  权益超市: 第 {i + 1} 次抽奖...")
            if not market_user_raffle(session, user_token):
                break
            sleep(3 + random.random() * 2)

    sleep(2)
    market_member_center_task(session, user_token)


def uphone_biz_ok(data):
    if not isinstance(data, dict):
        return False
    return data.get("code") in (200, "200", 0, "0")


def uphone_app_headers(cp_token="", extra=None):
    headers = {
        "User-Agent": UPHONE_APP_UA,
        "Accept": "*/*",
        "channel": UPHONE_CHANNEL,
        "channelCode": UPHONE_CHANNEL,
        "deviceId": "0",
    }
    if cp_token:
        headers["Authorization"] = cp_token
    if extra:
        headers.update(extra)
    return headers


def uphone_h5_headers(usr_token="", extra=None):
    headers = {
        "User-Agent": UPHONE_H5_UA,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://uphone.wostore.cn",
    }
    if usr_token:
        headers["X-USR-TOKEN"] = usr_token
    if extra:
        headers.update(extra)
    return headers


def uphone_sso_login(session, cookie_header=None):
    ecs_token = session.cookies.get("ecs_token") or cookie_get(cookie_header, "ecs_token")
    if not ecs_token:
        print("  云手机: 无 ecs_token，跳过")
        return None
    try:
        r = session.get(
            "https://m.client.10010.com/edop_ng/getTicketByNative",
            params={"token": ecs_token, "appId": UPHONE_EDOP_APP_ID},
            headers={"User-Agent": UPHONE_APP_UA, "Accept": "*/*"},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云手机: 换 ticket 异常: {e}")
        return None
    ticket = r.get("ticket")
    if not ticket and isinstance(r.get("data"), dict):
        ticket = r.get("data").get("ticket")
    if not ticket:
        print(f"  云手机: 换 ticket 失败: {r.get('rsp_desc') or r.get('msg') or r.get('code') or r.get('rsp_code')}")
        return None
    try:
        r2 = session.post(
            f"{UPHONE_H5API}/token-service/getTokenByTicket",
            headers=uphone_app_headers(extra={"Content-Type": "application/json"}),
            json={"channel": UPHONE_CHANNEL, "ticket": ticket},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云手机: 换 cpToken 异常: {e}")
        return None
    token = r2.get("data")
    if isinstance(token, dict):
        token = token.get("data") or token.get("token")
    if not (uphone_biz_ok(r2) and isinstance(token, str) and token.startswith("eyJ")):
        print(f"  云手机: 换 cpToken 失败: {r2.get('msg') or r2.get('code')}")
        return None
    print("  云手机: SSO 成功")
    return token


def uphone_activity_login(session, cp_token, activity_id):
    try:
        r = session.post(
            f"{UPHONE_H5API}/activity-service/user/login",
            headers=uphone_h5_headers(),
            json={
                "identityType": "cloudPhoneLogin",
                "code": cp_token,
                "channelId": UPHONE_CHANNEL_H5,
                "activityId": activity_id,
                "device": "device",
            },
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云手机: 活动登录异常({activity_id}): {e}")
        return None
    nested = r.get("data") if isinstance(r.get("data"), dict) else None
    tok = nested.get("user_token") if isinstance(nested, dict) else None
    if not (uphone_biz_ok(r) and tok):
        print(f"  云手机: 活动登录失败({activity_id}): {r.get('msg') or r.get('code')}")
        return None
    return str(tok)


def uphone_points_summary(session, usr_token):
    try:
        r = session.get(
            f"{UPHONE_H5API}/activity-service/points/v1/summary",
            headers=uphone_h5_headers(usr_token),
            params={"activityCode": UPHONE_ACT_EXCHANGE},
            timeout=15,
        ).json()
    except Exception:
        return None
    nested = r.get("data") if isinstance(r.get("data"), dict) else None
    if not (uphone_biz_ok(r) and isinstance(nested, dict)):
        return None
    inner = nested.get("data")
    return inner if isinstance(inner, dict) else nested


def uphone_sign(session, usr_token):
    try:
        r = session.post(
            f"{UPHONE_H5API}/activity-service/points/v1/sign",
            headers=uphone_h5_headers(usr_token),
            json={"activityCode": UPHONE_ACT_SIGN},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云手机: 签到异常: {e}")
        return False
    if uphone_biz_ok(r):
        print(f"  云手机: 签到成功: {r.get('msg') or 'ok'}")
        return True
    msg = str(r.get("msg") or "")
    if any(k in msg for k in ("已签", "签过", "重复")):
        print(f"  云手机: 今日已签到: {msg}")
        return True
    print(f"  云手机: 签到失败: {msg or r.get('code')}")
    return False


def uphone_task_list(session, usr_token, activity_code):
    try:
        r = session.post(
            f"{UPHONE_H5API}/activity-service/user/task/list",
            headers=uphone_h5_headers(usr_token),
            json={"activityCode": activity_code},
            timeout=15,
        ).json()
    except Exception:
        return []
    nested = r.get("data") if isinstance(r.get("data"), dict) else r
    if not isinstance(nested, dict):
        return []
    task_list = nested.get("taskList") or []
    return task_list if isinstance(task_list, list) else []


def uphone_task_logs(session, usr_token, task_code, detail):
    try:
        r = session.post(
            f"{UPHONE_H5API}/activity-service/user/task/logs",
            headers=uphone_h5_headers(usr_token),
            json={"logType": "01", "logCode": task_code, "logSource": "01", "logDetail": detail},
            timeout=15,
        ).json()
    except Exception:
        return False, None
    nested = r.get("data") if isinstance(r.get("data"), dict) else r
    return uphone_biz_ok(nested if isinstance(nested, dict) else r), nested if isinstance(nested, dict) else r


def uphone_raffle_get(session, usr_token, activity_code, task_code):
    try:
        r = session.post(
            f"{UPHONE_H5API}/activity-service/user/task/raffle/get",
            headers=uphone_h5_headers(usr_token),
            json={"activityCode": activity_code, "taskCode": task_code},
            timeout=15,
        ).json()
    except Exception:
        return False, None
    nested = r.get("data") if isinstance(r.get("data"), dict) else r
    body = nested if isinstance(nested, dict) else r
    if isinstance(body, dict) and body.get("code") in (10301, "10301"):
        print(f"  云手机: 领奖受限 {task_code}: {body.get('msg')}")
        return False, body
    return uphone_biz_ok(body if isinstance(body, dict) else r), body


def uphone_obtain_tasks(session, usr_token):
    tasks = uphone_task_list(session, usr_token, UPHONE_ACT_OBTAIN)
    claimed = logged = skipped = 0
    for t in tasks:
        if t.get("status") != "UNCLAIMED":
            continue
        code = str(t.get("taskCode") or "")
        ok, _ = uphone_raffle_get(session, usr_token, UPHONE_ACT_OBTAIN, code)
        if ok:
            claimed += 1
            print(f"  云手机: 领取 {code} {t.get('taskName')} +{t.get('pointsCount')}")
        sleep(0.3)
    tasks = uphone_task_list(session, usr_token, UPHONE_ACT_OBTAIN)
    for t in tasks:
        code = str(t.get("taskCode") or "")
        name = str(t.get("taskName") or code)
        if t.get("status") != "INCOMPLETE":
            continue
        if code in UPHONE_OBTAIN_SKIP:
            skipped += 1
            continue
        ok, body = uphone_task_logs(session, usr_token, code, name)
        if not ok:
            print(f"  云手机: 任务上报失败 {code}: {(body or {}).get('msg')}")
            sleep(0.2)
            continue
        logged += 1
        sleep(0.3)
        tasks2 = uphone_task_list(session, usr_token, UPHONE_ACT_OBTAIN)
        t2 = next((x for x in tasks2 if x.get("taskCode") == code), None)
        if not t2 or t2.get("status") != "UNCLAIMED":
            print(f"  云手机: 任务未达可领 {code} status={t2.get('status') if t2 else '?'}")
            continue
        ok, _ = uphone_raffle_get(session, usr_token, UPHONE_ACT_OBTAIN, code)
        if ok:
            claimed += 1
            print(f"  云手机: 完成 {code} {name} +{t.get('pointsCount')}")
        sleep(0.3)
    print(f"  云手机: 积分任务 claimed={claimed} logged={logged} skipped={skipped}")


def uphone_points_task(session, cookie_header=None):
    print("==== 沃云手机积分 ====")
    cp_token = uphone_sso_login(session, cookie_header)
    if not cp_token:
        return
    usr_token = uphone_activity_login(session, cp_token, UPHONE_ACT_SIGN)
    if not usr_token:
        return
    uphone_sign(session, usr_token)
    obtain_token = uphone_activity_login(session, cp_token, UPHONE_ACT_OBTAIN)
    if obtain_token:
        uphone_obtain_tasks(session, obtain_token)
        usr_token = obtain_token
    summary = uphone_points_summary(session, usr_token)
    if summary:
        print(f"  云手机: 余额 {summary.get('balanceScoreNum')}")


def get_bizchannelinfo(session, cookie_header, rpt_id=""):
    cookies = session.cookies.get_dict()
    cookies.update(parse_cookie_map(cookie_header))
    info = {
        "bizChannelCode": "225",
        "disriBiz": "party",
        "unionSessionId": "",
        "stType": "",
        "stDesmobile": "",
        "source": "",
        "rptId": rpt_id,
        "ticket": "",
        "tongdunTokenId": cookies.get("TOKENID_COOKIE", ""),
        "xindunTokenId": cookies.get("UNICOM_TOKENID", ""),
    }
    return json.dumps(info, ensure_ascii=False)


def get_epay_authinfo(session_id="", token_id="", user_id=""):
    return json.dumps(
        {"mobile": "", "sessionId": session_id, "tokenId": token_id, "userId": user_id},
        ensure_ascii=False,
    )


def ttlxj_task(session, cookie_header=None):
    print("==== 天天领现金 ====")
    state = {"sessionId": "", "tokenId": "", "userId": "", "rptId": ""}

    def epay_headers():
        return {
            "bizchannelinfo": get_bizchannelinfo(session, cookie_header, state["rptId"]),
            "authinfo": get_epay_authinfo(state["sessionId"], state["tokenId"], state["userId"]),
        }

    def authorize(ticket, type_val, referer_url):
        payload = {
            "response_type": "rptid",
            "client_id": "73b138fd-250c-4126-94e2-48cbcc8b9cbe",
            "redirect_uri": "https://epay.10010.com/ci-mps-st-web/",
            "login_hint": {
                "credential_type": "st_ticket",
                "credential": ticket,
                "st_type": type_val,
                "force_logout": True,
                "source": "app_sjyyt",
            },
            "device_info": {
                "token_id": f"chinaunicom-pro-{int(time.time() * 1000)}-{random_string(13)}",
                "trace_id": random_string(32),
            },
        }
        headers = base_headers(cookie_header, {"Origin": "https://epay.10010.com", "Referer": referer_url, "content-type": "application/json"})
        try:
            res = session.post("https://epay.10010.com/woauth2/v2/authorize", json=payload, headers=headers, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"  天天领现金 authorize 异常: {e}")
            return False

    def auth_check():
        headers = base_headers(cookie_header, epay_headers())
        headers["content-type"] = "application/json"
        try:
            res = session.post("https://epay.10010.com/ps-pafs-auth-front/v1/auth/check", headers=headers, json={}, timeout=10)
            data = res.json()
        except Exception as e:
            print(f"  天天领现金 auth_check 异常: {e}")
            return False
        code = data.get("code")
        if code == "0000":
            auth_info = (data.get("data") or {}).get("authInfo") or {}
            state["sessionId"] = auth_info.get("sessionId", "")
            state["tokenId"] = auth_info.get("tokenId", "")
            state["userId"] = auth_info.get("userId", "")
            return True
        if code == "2101000100":
            login_url = (data.get("data") or {}).get("woauth_login_url")
            if login_url:
                return ttlxj_login(login_url)
        print(f"  天天领现金 AuthCheck 失败[{code}]: {data.get('msg')}")
        return False

    def ttlxj_login(login_url):
        full_url = f"{login_url}https://epay.10010.com/ci-mcss-party-web/clockIn/?bizFrom=225&bizChannelCode=225"
        try:
            res = session.get(full_url, headers=base_headers(cookie_header), allow_redirects=False, timeout=10)
        except Exception as e:
            print(f"  天天领现金 login 异常: {e}")
            return False
        loc = res.headers.get("Location") if res is not None else None
        if res is not None and res.status_code in (301, 302, 303, 307, 308) and loc:
            rptid = (parse_qs(urlparse(loc).query).get("rptid") or [""])[0]
            if rptid:
                state["rptId"] = rptid
                return auth_check()
            print("  天天领现金: Login 跳转后无 rptid")
            return False
        print(f"  天天领现金: Login 失败[{getattr(res, 'status_code', '?')}]")
        return False

    def do_tasks():
        headers = base_headers(cookie_header, epay_headers())
        headers["content-type"] = "application/json"
        try:
            res = session.post(
                "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/userDrawInfo",
                json={},
                headers=headers,
                timeout=10,
            )
            data = res.json()
        except Exception as e:
            print(f"  天天领现金 查询异常: {e}")
            return
        if data.get("code") != "0000":
            print(f"  天天领现金: 查询失败: {data.get('msg')}")
            return
        day_of_week = (data.get("data") or {}).get("dayOfWeek", "")
        draw_key = f"day{day_of_week}"
        if (data.get("data") or {}).get(draw_key) == "1":
            print("  天天领现金: 今天未打卡")
            today_js = (datetime.datetime.now().weekday() + 1) % 7
            draw_type = "C" if today_js == 0 else "B"
            unify_draw(draw_type)
        else:
            print("  天天领现金: 今天已打卡")

    def unify_draw(draw_type):
        headers = base_headers(cookie_header, epay_headers())
        req_data = {"drawType": draw_type, "bizFrom": "225", "activityId": "TTLXJ20210330"}
        try:
            res = session.post(
                "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/unifyDrawNew",
                data=req_data,
                headers=headers,
                timeout=10,
            )
            data = res.json()
        except Exception as e:
            print(f"  天天领现金 抽奖异常: {e}")
            return
        if data.get("code") == "0000":
            prize = (data.get("data") or {}).get("prizeName", "未知奖品")
            print(f"  天天领现金: 抽奖成功: {prize}")
        else:
            print(f"  天天领现金: 抽奖失败: {data.get('msg')}")

    def query_available():
        headers = base_headers(cookie_header, epay_headers())
        headers["content-type"] = "application/json"
        try:
            res = session.post(
                "https://epay.10010.com/ci-mcss-party-front/v1/ttlxj/queryAvailable",
                json={},
                headers=headers,
                timeout=10,
            )
            data = res.json()
        except Exception as e:
            print(f"  天天领现金 余额查询异常: {e}")
            return
        if data.get("code") != "0000":
            print(f"  天天领现金: 查询余额失败: {data.get('msg')}")
            return
        d = data.get("data") or {}
        amount_raw = int(d.get("availableAmount", "0") or 0)
        msg = f"  天天领现金: 可用立减金 {amount_raw / 100:.2f}元"
        seven_day = int(d.get("sevenDayExpireAmount", 0) or 0)
        if seven_day > 0:
            msg += f", 7天内过期 {seven_day / 100:.2f}元"
        print(msg)

    for attempt in range(1, 4):
        ticket_res = open_plat_line_new(session, cookie_header, "https://epay.10010.com/ci-mps-st-web/ttlxj/")
        if not ticket_res or not ticket_res.get("ticket"):
            print(f"  天天领现金: 获取 ticket 失败 ({attempt}/3)")
            sleep(2)
            continue
        if authorize(ticket_res["ticket"], ticket_res["type"], ticket_res["loc"]) and auth_check():
            do_tasks()
            query_available()
            return
        print(f"  天天领现金: 授权失败 ({attempt}/3)")
        sleep(2)
    print("  天天领现金: 跳过")


class TtxcFarm:
    def __init__(self, session, cookie_header=None):
        self.session = session
        self.cookie_header = cookie_header
        self.token = ""
        self.user_id = ""
        self.nick_name = ""
        self.newbie_list = []
        self.charge_level = {}
        self.no_energy = False
        self.unicom_token_id = session_cookie(session, "UNICOM_TOKENID", cookie_header) or random_string(32)

    def headers(self, auth=True, extra=None):
        headers = {
            "User-Agent": TTXC_UA,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://epay.10010.com",
            "Referer": TTXC_REFERER,
            "X-Requested-With": "com.sinovatech.unicom.ui",
        }
        if auth and self.token:
            headers["Authorization"] = self.token
        if extra:
            headers.update(extra)
        return headers

    def post(self, path, payload=None, auth=True, with_user=True):
        data = dict(payload or {})
        if with_user:
            data.setdefault("userId", self.user_id or "")
        data.setdefault("channel", TTXC_CHANNEL)
        try:
            resp = self.session.post(
                f"{TTXC_BASE_URL}{path}",
                json=data,
                headers=self.headers(auth=auth),
                timeout=15,
            )
            return resp.json()
        except Exception as e:
            print(f"  通通乡村 {path} 异常: {e}")
            return {}

    def finish_woauth(self, login_url):
        try:
            res = self.session.get(
                login_url,
                headers={"Referer": "https://epay.10010.com/", "User-Agent": TTXC_UA},
                timeout=15,
            )
        except Exception as e:
            print(f"  通通乡村 woauth 异常: {e}")
            return False
        match = re.search(r'var token = "([^"]+)"', res.text or "")
        if not match:
            return False
        next_url = (
            "https://epay.10010.com/woauth2/after-collected-device-digest"
            f"?deviceDigestTraceId=&deviceDigestTokenId=&token={quote(match.group(1))}&source=app_sjyyt"
        )
        referer = login_url
        ok = False
        for _ in range(8):
            try:
                r = self.session.get(
                    next_url,
                    allow_redirects=False,
                    headers={"Referer": referer, "User-Agent": TTXC_UA},
                    timeout=15,
                )
            except Exception:
                return False
            loc = r.headers.get("Location") or r.headers.get("location")
            if not loc:
                ok = r.status_code == 200
                break
            if loc.startswith("/"):
                loc = urljoin(next_url, loc)
            referer, next_url = next_url, loc
        ecs = session_cookie(self.session, "ecs_token", self.cookie_header)
        if ecs:
            self.session.cookies.set("ecs_token", ecs, domain=".10010.com")
        return ok

    def init_game(self):
        ecs = session_cookie(self.session, "ecs_token", self.cookie_header)
        if not ecs:
            print("  通通乡村: 缺少 ecs_token，跳过")
            return False
        self.session.cookies.set("ecs_token", ecs, domain=".10010.com")
        url = f"{TTXC_APP_BASE_URL}/v1/login/ttGame?channel={TTXC_CHANNEL}&rptId="
        last = {}
        for attempt in range(1, 4):
            try:
                res = self.session.post(
                    url,
                    json={"unicomTokenId": self.unicom_token_id},
                    headers=self.headers(auth=False),
                    timeout=15,
                )
                last = res.json() if res is not None else {}
            except Exception as e:
                print(f"  通通乡村 init 异常: {e}")
                last = {}
            if last.get("code") == "0000":
                return True
            if last.get("code") == "4003" and last.get("data"):
                if self.finish_woauth(last.get("data")):
                    if any(c.name == "CucaSession" for c in self.session.cookies):
                        return True
                    continue
            if attempt < 3:
                sleep(2)
        print(f"  通通乡村初始化失败[{last.get('code')}]: {last.get('msg', '')}")
        return False

    def login(self):
        if not self.init_game():
            return False
        data = self.post("/user/v1/login", auth=False, with_user=False)
        if data.get("code") != 0:
            print(f"  通通乡村登录失败[{data.get('code')}]: {data.get('msg', '')}")
            return False
        user = data.get("data") or {}
        self.user_id = user.get("userId", "")
        self.token = data.get("token", "")
        self.charge_level = user.get("chargeLevel") or {}
        self.newbie_list = user.get("newbieList")
        self.nick_name = user.get("nickName") or ""
        if not self.user_id or not self.token:
            print("  通通乡村登录响应缺少 userId/token")
            return False
        carbon = self.charge_level.get("carbonNum", 0)
        eco = self.charge_level.get("ecologyAmount", 0)
        print(f"  通通乡村登录成功，碳能量{carbon}g，生态值{eco}")
        return True

    def newbie_done(self):
        steps = self.newbie_list
        if not isinstance(steps, list):
            return True
        return all(step in steps for step in TTXC_NEWBIE_STEPS)

    def newbie_need(self, step):
        return isinstance(self.newbie_list, list) and step not in self.newbie_list

    def newbie_mark(self, step):
        target = []
        for item in TTXC_NEWBIE_STEPS:
            target.append(item)
            if item == step:
                break
        data = self.post("/user/v1/newbie", {"newbieList": target, "type": 1})
        if data.get("code") == 0:
            self.newbie_list = data.get("data") or target
            return True
        print(f"  新手步骤{step}失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def sign(self):
        info = self.post("/client/v1/sign/info", {})
        code = (info.get("data") or {}).get("signinCode")
        if not code:
            print("  通通乡村: 获取签到码失败")
            return
        user = self.post("/client/v1/sign/user", {"code": code})
        last_time = str((user.get("data") or {}).get("lastSigninTime") or "")
        if last_time[:10] == datetime.datetime.now().strftime("%Y-%m-%d"):
            print("  通通乡村: 今日已签到")
            return
        data = self.post("/client/v1/sign/signIn", {"code": code})
        if data.get("code") == 0:
            print("  通通乡村: 签到成功")
        else:
            print(f"  通通乡村签到失败[{data.get('code')}]: {data.get('msg', '')}")

    def get_tasks(self):
        data = self.post("/client/v1/task/list", {})
        if data.get("code") != 0:
            print(f"  通通乡村任务列表失败[{data.get('code')}]: {data.get('msg', '')}")
            return []
        tasks = []
        for group in data.get("data") or []:
            for task in group.get("taskList") or []:
                task["taskGroupName"] = group.get("taskGroupName", "")
                tasks.append(task)
        return tasks

    def finish_task(self, task):
        task_id = task.get("taskCode")
        if not task_id:
            return False
        data = self.post("/client/v1/task/finish", {"taskId": task_id})
        name = task.get("taskTitle", task_id)
        if data.get("code") == 0:
            reward = task.get("carbonEnergyAmount") or 0
            print(f"  领取[{name}]成功 +{reward}g")
            return True
        print(f"  领取[{name}]失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def do_task(self, task):
        data = self.post("/client/v1/task/do", {"taskId": task.get("taskCode")})
        name = task.get("taskTitle", task.get("taskCode", ""))
        if data.get("code") == 0:
            print(f"  已执行[{name}]")
            return True
        print(f"  执行[{name}]失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def claim_ready(self, tasks, claimed):
        count = 0
        for task in tasks:
            task_id = task.get("taskCode")
            if task.get("taskStatus") == "UNCLA" and task_id not in claimed:
                if self.finish_task(task):
                    claimed.add(task_id)
                    count += 1
        return count

    def do_jump_tasks(self, tasks):
        count = 0
        for task in tasks:
            if task.get("taskType") == "GAME" and task.get("taskStatus") == "UNDO" and task.get("jumpUrl"):
                if self.do_task(task):
                    count += 1
                sleep(1)
        return count

    def do_garbage(self, tasks):
        task = next(
            (
                t
                for t in tasks
                if t.get("taskType") == "GAME"
                and t.get("taskStatus") == "UNDO"
                and "垃圾分类" in t.get("taskTitle", "")
            ),
            None,
        )
        if not task:
            return False
        start = self.post("/user/v1/start", {})
        answer_no = (start.get("data") or {}).get("answerNo")
        if not answer_no:
            print("  垃圾分类开始失败")
            return False
        sleep(TTXC_GARBAGE_WAIT)
        data = self.post("/user/v1/finish", {"answerNo": answer_no})
        if data.get("code") == 0:
            print("  垃圾分类已通关")
            return True
        print(f"  垃圾分类失败[{data.get('code')}]: {data.get('msg', '')}")
        return False

    def get_lands(self):
        land = safe_int((self.charge_level or {}).get("land"), 4)
        data = self.post("/plant/v1/user", {"land": land})
        if data.get("code") != 0:
            print(f"  获取土地失败[{data.get('code')}]: {data.get('msg', '')}")
            return []
        return data.get("data") or []

    def get_plant_id(self):
        data = self.post("/client/v1/plant/page", {"itemType": "SPE", "pageNum": 1, "pageSize": 20})
        items = (data.get("data") or {}).get("list") or []
        return items[0].get("itemNo", "") if items else ""

    def plant_land(self, land_index, plant_id=None):
        plant_id = plant_id or self.get_plant_id()
        if not plant_id or not land_index:
            return None
        buy = self.post("/client/v1/plant/buy", {"plantId": plant_id, "gameCfgId": ""})
        if buy.get("code") != 0:
            print(f"  购买种子失败[{buy.get('code')}]: {buy.get('msg', '')}")
            return None
        data = self.post("/plant/v1/planting", {"landIndex": land_index, "plantId": plant_id})
        if data.get("code") == 0:
            print(f"  已在地块{land_index}种植")
            return {"landIndex": land_index, "status": 3, "plant": {"plantId": plant_id}}
        print(f"  地块{land_index}种植失败[{data.get('code')}]: {data.get('msg', '')}")
        return None

    def ensure_planted(self, lands):
        active = [l for l in lands if l.get("status") in [2, 3] and (l.get("plant") or {}).get("plantId")]
        empty = [l for l in lands if l.get("status") == 1]
        if not empty:
            return active
        plant_id = self.get_plant_id()
        if not plant_id:
            return active
        for land in empty[:2]:
            planted = self.plant_land(land.get("landIndex"), plant_id)
            if planted:
                active.append(planted)
        return active

    def charge_land(self, land, mock=None):
        if not land:
            return None
        plant = land.get("plant") or {}
        plant_id, land_index = plant.get("plantId"), land.get("landIndex")
        if not plant_id or not land_index:
            return None
        payload = {"landIndex": land_index, "plantId": plant_id}
        if mock is not None:
            payload["mock"] = mock
        data = self.post("/plant/v1/charge", payload)
        if data.get("code") == 0:
            print(f"  地块{land_index}充能成功")
            result = data.get("data") or {}
            if result and not result.get("plant"):
                result["plant"] = plant
            return result or land
        print(f"  地块{land_index}充能失败[{data.get('code')}]: {data.get('msg', '')}")
        if "余额不足" in str(data.get("msg", "")):
            self.no_energy = True
        return None

    def harvest_land(self, land, newbie=False):
        if not land:
            return None
        plant = land.get("plant") or {}
        plant_id, land_index = plant.get("plantId"), land.get("landIndex")
        if not plant_id or not land_index:
            return None
        if land.get("status") == 2 and TTXC_HARVEST_WAIT > 0:
            sleep(TTXC_HARVEST_WAIT)
        path = "/plant/v1/newHarvest" if newbie else "/plant/v1/harvest"
        data = self.post(path, {"landIndex": land_index, "plantId": plant_id})
        if data.get("code") == 0:
            print(f"  地块{land_index}收获成功")
            return data.get("data") or {"landIndex": land_index, "status": 1, "plant": None}
        print(f"  地块{land_index}收获失败[{data.get('code')}]: {data.get('msg', '')}")
        return None

    def harvest_and_replant(self, land):
        harvested = self.harvest_land(land)
        if harvested and land:
            return self.plant_land(land.get("landIndex"))
        return None

    def farm_tasks(self, tasks):
        charge_task = next((t for t in tasks if "10次作物充能" in t.get("taskTitle", "")), None)
        harvest_task = next((t for t in tasks if "收获一次作物" in t.get("taskTitle", "")), None)
        charge_pending = charge_task if (charge_task or {}).get("taskStatus") == "UNDO" else None
        harvest_pending = harvest_task if (harvest_task or {}).get("taskStatus") == "UNDO" else None
        if not charge_pending and not harvest_pending:
            return
        lands = self.get_lands()
        active = self.ensure_planted(lands)
        if harvest_pending:
            for land in active:
                if land.get("status") == 2:
                    self.harvest_and_replant(land)
        if not active:
            print("  没有可充能作物")
            return
        need = min(safe_int((charge_pending or {}).get("finishValue")) - safe_int((charge_pending or {}).get("doneValue")), TTXC_GROW_MAX)
        charged = 0
        for land in active:
            if self.no_energy or charged >= max(need, 1):
                break
            if land.get("status") == 3 and (land.get("plant") or {}).get("plantId"):
                result = self.charge_land(land)
                if result:
                    charged += 1
                    sleep(1)

    def run(self):
        print("==== 通通乡村 ====")
        if not self.login():
            return False
        claimed = set()
        self.sign()
        tasks = self.get_tasks()
        self.claim_ready(tasks, claimed)
        self.do_jump_tasks(tasks)
        self.do_garbage(tasks)
        self.farm_tasks(tasks)
        tasks = self.get_tasks()
        self.claim_ready(tasks, claimed)
        return True


def ttxc_task(session, cookie_header=None):
    TtxcFarm(session, cookie_header).run()


def cloud_env(name, default=""):
    return (os.getenv(name) or default).strip()


def cloud_activity_sign(payload):
    raw = "&".join(f"{k}={payload[k]}" for k in sorted(payload)) + f"&secret={CLOUD_PAN_SIGN_SECRET}"
    return hmac.new(CLOUD_PAN_SIGN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()


def cloud_encrypt_fileinfo(info, token):
    key = (token[:16]).encode()
    cipher = AES.new(key, AES.MODE_CBC, CLOUD_FILEINFO_IV.encode())
    plaintext = json.dumps(info, separators=(",", ":"))
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode(), AES.block_size))).decode()


def cloud_meta_code(data):
    if not isinstance(data, dict):
        return ""
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    return str(meta.get("code") or data.get("code") or "")


def cloud_extract_ticket(payload):
    if not isinstance(payload, dict):
        return ""
    ticket = payload.get("ticket")
    data = payload.get("data")
    if not ticket and isinstance(data, dict):
        ticket = data.get("ticket")
    return ticket or ""


def cloud_phone_location(session, state, cookie_header=None):
    cached = ((state or {}).get("provinceCode"), (state or {}).get("provinceName"))
    if cached[0] and cached[1]:
        return cached
    mobile = (
        session.cookies.get("c_mobile")
        or cookie_get(cookie_header, "c_mobile")
        or ""
    )
    token = (state or {}).get("userToken") or ""
    if not mobile or not token:
        return "", ""
    cipher = AES.new(b"CBWGjFHjZdhTf7h8", AES.MODE_CBC, CLOUD_FILEINFO_IV.encode())
    enc = base64.b64encode(cipher.encrypt(pad(mobile.encode(), AES.block_size))).decode()
    try:
        res = session.post(
            "https://panservice.mail.wo.cn/api-user/user/info/query",
            json={"mobile": enc},
            headers=cloud_activity_headers(state),
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘: 查询归属地异常: {e}")
        return "", ""
    result = res.get("result") if isinstance(res.get("result"), dict) else {}
    code = str(result.get("provinceCode") or "").lstrip("0") or str(result.get("provinceCode") or "")
    name = str(result.get("provinceName") or "")
    if code and name:
        state["provinceCode"] = code
        state["provinceName"] = name
        print(f"  云盘: 归属地 {name}({code})")
        return code, name
    return "", ""


def cloud_dispatcher_login(session, ticket, login_key="HandheldHallAutoLogin"):
    timestamp = str(int(time.time() * 1000))
    rnd = str(random.randint(123456, 199999))
    sign = hashlib.md5(f"{login_key}{timestamp}{rnd}wohome".encode()).hexdigest()
    try:
        r2 = session.post(
            "https://panservice.mail.wo.cn/wohome/dispatcher",
            headers={"User-Agent": APP_UA, "Content-Type": "application/json"},
            json={
                "header": {
                    "key": login_key,
                    "resTime": timestamp,
                    "reqSeq": rnd,
                    "channel": "wohome",
                    "version": "",
                    "sign": sign,
                },
                "body": {"clientId": CLOUD_CLIENT_ID, "ticket": ticket},
            },
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云盘: dispatcher 异常: {e}")
        return None
    data = r2.get("RSP") if isinstance(r2.get("RSP"), dict) else r2
    nested = data.get("DATA") if isinstance(data, dict) else None
    token = nested.get("token") if isinstance(nested, dict) else ""
    if not token and isinstance(r2.get("body"), dict):
        token = r2.get("body").get("token") or ""
    if token:
        return token, r2
    return None, r2


def cloud_openplat_ticket(session, cookie_header=None):
    entry = (
        "https://panservice.mail.wo.cn/h5/activitymobile/campusSeason"
        f"?activityId={quote(cloud_env('UNICOM_CAMPUS_ACTIVITY_ID', CAMPUS_ACTIVITY_DEFAULT))}&type=02"
    )
    try:
        r = session.get(
            "https://m.client.10010.com/mobileService/openPlatform/openPlatLineNew.htm",
            params={"to_url": entry},
            headers=base_headers(cookie_header, {"User-Agent": APP_UA}),
            allow_redirects=False,
            timeout=15,
        )
    except Exception as e:
        print(f"  云盘: openPlat 异常: {e}")
        return ""
    loc = r.headers.get("Location") or r.headers.get("location") or ""
    ticket = (parse_qs(urlparse(loc).query).get("ticket") or [""])[0]
    return ticket


def cloud_native_ticket(session, cookie_header=None):
    ecs_token = session.cookies.get("ecs_token") or cookie_get(cookie_header, "ecs_token")
    if not ecs_token:
        return ""
    try:
        r = session.get(
            "https://m.client.10010.com/edop_ng/getTicketByNative",
            params={"appId": CLOUD_EDOP_APP_ID, "token": ecs_token},
            headers={"User-Agent": APP_UA, "Accept": "*/*"},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云盘: 换 native ticket 异常: {e}")
        return ""
    return cloud_extract_ticket(r)


def cloud_pan_login(session, cookie_header=None):
    ticket = cloud_native_ticket(session, cookie_header)
    token = None
    if ticket:
        token, _ = cloud_dispatcher_login(session, ticket, "HandheldHallAutoLoginV2")
        if not token:
            token, _ = cloud_dispatcher_login(session, ticket, "HandheldHallAutoLogin")
    if not token:
        ticket = cloud_openplat_ticket(session, cookie_header)
        if not ticket:
            print("  云盘: 换 ticket 失败")
            return None
        token, r2 = cloud_dispatcher_login(session, ticket, "HandheldHallAutoLogin")
        if not token:
            token, r2 = cloud_dispatcher_login(session, ticket, "HandheldHallAutoLoginV2")
        if not token:
            desc = ""
            if isinstance(r2, dict) and isinstance(r2.get("RSP"), dict):
                desc = r2.get("RSP").get("RSP_DESC") or r2.get("RSP").get("RSP_CODE") or ""
            print(f"  云盘: 换 userToken 失败: {desc or '无 token'}")
            return None
    print("  云盘: SSO 成功")
    return {"userToken": token, "ticket": ticket}


def cloud_userticket(session, state):
    token = (state or {}).get("userToken") or ""
    if not token:
        return ""
    headers = {
        "User-Agent": APP_UA,
        "Content-Type": "application/json",
        "X-YP-Access-Token": token,
        "accesstoken": token,
        "token": token,
        "clientId": CLOUD_CLIENT_ID,
        "X-YP-Client-Id": CLOUD_CLIENT_ID,
        "source-type": "woapi",
        "app-type": "unicom",
    }
    try:
        res = session.post(
            "https://panservice.mail.wo.cn/api-user/api/user/ticket",
            json={},
            headers=headers,
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云盘: userticket 异常: {e}")
        return ""
    ticket = ((res.get("result") or {}) if isinstance(res, dict) else {}).get("ticket")
    if ticket:
        state["userticket"] = ticket
        return ticket
    print(f"  云盘: userticket 失败: {res}")
    return ""


def cloud_jf_headers(state, with_sign=False):
    ticket = (state or {}).get("userticket") or ""
    headers = {
        "User-Agent": APP_UA,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://m.jf.10010.com",
        "ticket": ticket,
        "partnersid": CLOUD_JF_PARTNERS,
        "clienttype": "yunpan_android",
        "x-requested-with": "com.sinovatech.unicom.ui",
    }
    jea = (state or {}).get("jeaId")
    if jea:
        headers["Cookie"] = f"_jea_id={jea};"
    if with_sign:
        secret = (state or {}).get("secretKey")
        if secret:
            request_ts = str(round(time.time() * 1000))
            nonce = "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyz", k=8))
            signature = hmac.new(secret, f"{nonce}{request_ts}".encode(), hashlib.sha256).hexdigest()
            headers.update({
                "x-request-timestamp": request_ts,
                "x-request-nonce": nonce,
                "x-request-signature": signature,
            })
    return headers


def cloud_capture_jea(session, state, response=None):
    jea = session.cookies.get("_jea_id") or ""
    if not jea and response is not None:
        cookie = response.headers.get("Set-Cookie") or response.headers.get("set-cookie") or ""
        match = re.search(r"_jea_id=([^;]+)", cookie)
        if match:
            jea = match.group(1)
    if jea:
        state["jeaId"] = jea
    return jea


def cloud_userinfo(session, state):
    if not cloud_userticket(session, state):
        return None
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/userInfo",
            json={},
            headers=cloud_jf_headers(state),
            timeout=10,
        )
        cloud_capture_jea(session, state, res)
        data = res.json()
    except Exception as e:
        print(f"  云盘: userInfo 异常: {e}")
        return None
    info = data.get("data") if isinstance(data, dict) else None
    if isinstance(info, dict):
        avail = info.get("availableScore")
        today = info.get("todayEarnScore", 0)
        if "initial_avail" not in state:
            state["initial_avail"] = avail
            print(f"  云盘: 运行前 今日已赚 {today} 可用积分 {avail}")
        else:
            try:
                earned = int(avail) - int(state.get("initial_avail") or 0)
            except (TypeError, ValueError):
                earned = 0
            print(f"  云盘: 运行后 今日已赚 {today} 可用 {avail} 本次 {earned}")
        return info
    return None


def cloud_secret_key(session, state):
    if state.get("secretKey"):
        return state["secretKey"]
    if not state.get("userticket") or not state.get("jeaId"):
        return None
    try:
        res = session.get(
            "https://m.jf.10010.com/jf-external-application/jftask/getSecretKey",
            headers=cloud_jf_headers(state),
            timeout=10,
        ).json()
        secret = (res.get("data") or {}).get("secretKey")
        if str(res.get("code")) == "0000" and secret:
            state["secretKey"] = secret.encode("utf-8")
            return state["secretKey"]
        print(f"  云盘: getSecretKey 失败: {res.get('code') or res}")
    except Exception as e:
        print(f"  云盘: getSecretKey 异常: {e}")
    return None


def cloud_task_list(session, state):
    if not cloud_userticket(session, state):
        return []
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/taskDetail",
            json={},
            headers=cloud_jf_headers(state),
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘: taskDetail 异常: {e}")
        return []
    if not isinstance(res, dict):
        return []
    return ((res.get("data") or {}).get("taskDetail") or {}).get("taskList") or []


def cloud_to_finish(session, state, task_code):
    if not cloud_userticket(session, state):
        return False
    cloud_secret_key(session, state)
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/toFinish",
            json={"taskCode": task_code},
            headers=cloud_jf_headers(state, with_sign=True),
            timeout=10,
        ).json()
        return str(res.get("code")) == "0000" or res.get("data") is True
    except Exception:
        return False


def cloud_do_sign(session, state, task_code, task_name):
    if not cloud_userticket(session, state):
        return
    cloud_secret_key(session, state)
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/sign",
            json={"taskCode": task_code},
            headers=cloud_jf_headers(state, with_sign=True),
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘: [{task_name}] 签到异常: {e}")
        return
    score = (res.get("data") or {}).get("score") if isinstance(res.get("data"), dict) else None
    if "0000" in str(res.get("code")) and score:
        print(f"  云盘: [{task_name}] 完成, 积分 {score}")
    elif any(k in str(res.get("msg") or res.get("message") or "") for k in ("已签", "签过", "重复")):
        print(f"  云盘: [{task_name}] 今日已签到")
    else:
        print(f"  云盘: [{task_name}] {res.get('msg') or res.get('code') or '失败'}")


def cloud_do_popup(session, state, task_name):
    if not cloud_userticket(session, state):
        return
    sleep(2)
    try:
        res = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/popUp",
            json={},
            headers=cloud_jf_headers(state),
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘: [{task_name}] 领奖异常: {e}")
        return
    code = str((res.get("meta") or {}).get("code") or res.get("code") or "")
    if code in ("0000", "0"):
        score = (res.get("data") or {}).get("score", 0) if isinstance(res.get("data"), dict) else 0
        print(f"  云盘: [{task_name}] 领取完成{(' 积分 ' + str(score)) if score else ''}")
    else:
        print(f"  云盘: [{task_name}] 领取失败: {res.get('msg') or code}")


def cloud_ai_chat(session, state, task_code, task_name):
    token = (state or {}).get("userToken") or ""
    if not token:
        return False
    headers = {
        "accept": "text/event-stream",
        "X-YP-Access-Token": token,
        "X-YP-App-Version": "5.0.12",
        "X-YP-Client-Id": "1001000035",
        "User-Agent": APP_UA,
        "Content-Type": "application/json",
        "Origin": "https://panservice.mail.wo.cn",
        "Referer": f"https://panservice.mail.wo.cn/h5/wocloud_ai/?modelType=0&clientId=1001000035&touchpoint=300300010001&token={token}",
    }
    payload = {
        "input": "你好",
        "platform": 2,
        "modelId": 0,
        "tag": 21,
        "subTag": 210000,
        "conversationId": "",
        "knowledgeId": "",
        "referFileInfo": [],
    }
    try:
        res = session.post(
            "https://panservice.mail.wo.cn/wohome/ai/assistant/query",
            json=payload,
            headers=headers,
            timeout=30,
            stream=True,
        )
        body = ""
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                body += chunk.decode("utf-8", errors="ignore")
            if len(body) > 2048:
                break
        if '"finish":1' in body or "success" in body or res.status_code == 200:
            print(f"  云盘: [{task_name}] AI 互动成功")
            cloud_do_popup(session, state, task_name)
            return True
        print(f"  云盘: [{task_name}] AI 互动失败 HTTP {res.status_code}")
    except Exception as e:
        print(f"  云盘: [{task_name}] AI 异常: {e}")
    return False


def cloud_activity_headers(state, activity_id="", extra=None):
    token = (state or {}).get("userToken") or ""
    headers = {
        "User-Agent": APP_UA,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "source-type": "woapi",
        "clientId": "1001000165",
        "X-YP-Client-Id": "1001000165",
        "token": token,
        "X-YP-Access-Token": token,
        "X-SH-Access-Token": "",
        "X-YP-GRAY-FLAG": "undefined",
        "Origin": "https://panservice.mail.wo.cn",
        "requestTime": str(int(time.time() * 1000)),
    }
    if activity_id:
        headers["Referer"] = (
            "https://panservice.mail.wo.cn/h5/activitymobile/fileUploadActive"
            f"?touchpoint=300300010005&activityId={quote(activity_id)}&token={token}"
        )
    if extra:
        headers.update(extra)
    return headers


def cloud_lottery_times(session, state, activity_id):
    try:
        res = session.get(
            "https://panservice.mail.wo.cn/activity/lottery/lottery-times",
            params={"activityId": activity_id},
            headers=cloud_activity_headers(state, activity_id),
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘: 查询抽奖次数异常: {e}")
        return None, 0
    result = res.get("result")
    count = 0
    if isinstance(result, int):
        count = result
    elif isinstance(result, dict):
        for key in ("times", "lotteryTimes", "freeTimes", "drawTimes", "count"):
            if key in result:
                count = safe_int(result.get(key), 0)
                break
    return res, max(count, 0)


def cloud_draw_lottery(session, state):
    activity_id = cloud_env("UNICOM_CLOUD_LOTTERY_ACTIVITY_ID", CLOUD_LOTTERY_DEFAULT)
    times_res, count = cloud_lottery_times(session, state, activity_id)
    if times_res is None:
        return
    code = cloud_meta_code(times_res)
    if code not in ("200", "90003603"):
        print(f"  云盘: 抽奖活动[{activity_id}] 无效: {times_res.get('meta', {}).get('message') or code}")
        return
    if count <= 0:
        print(f"  云盘: 抽奖活动[{activity_id}] 当前无抽奖次数")
        return
    print(f"  云盘: 抽奖次数 {count}")
    for _ in range(min(count, 5)):
        try:
            res = session.post(
                "https://panservice.mail.wo.cn/activity/lottery",
                json={"activityId": activity_id},
                headers=cloud_activity_headers(state, activity_id),
                timeout=10,
            ).json()
        except Exception as e:
            print(f"  云盘: 抽奖异常: {e}")
            break
        if cloud_meta_code(res) == "92000017":
            print("  云盘: 转盘已抽奖")
            return
        prize = (res.get("result") or {}).get("prizeName") if isinstance(res.get("result"), dict) else ""
        if prize:
            print(f"  云盘: 转盘获得 {prize}")
        else:
            print(f"  云盘: 抽奖结果 {res.get('meta', {}).get('message') or cloud_meta_code(res)}")
            break
        sleep(1.5)


def cloud_run_daily_tasks(session, state):
    tasks = cloud_task_list(session, state)
    if not tasks:
        print("  云盘: 任务列表为空")
        return
    names = [t.get("taskName", "?") for t in tasks]
    print(f"  云盘: 任务列表({len(tasks)}): {', '.join(names)}")
    for task in tasks:
        sleep(0.5)
        name = task.get("taskName") or ""
        code = task.get("taskCode")
        finish_text = str(task.get("finishText") or "")
        finished = safe_int(task.get("finishCount"), 0)
        required = safe_int(task.get("needCount"), 0)
        if finish_text == "待领取":
            cloud_do_popup(session, state, name)
            continue
        if finish_text in ("已完成", "已领取") or task.get("finishState") is True or (required > 0 and finished >= required):
            print(f"  云盘: [{name}] 已完成")
            continue
        print(f"  云盘: 开始 [{name}] {finished}/{required}")
        if "签到" in name:
            cloud_to_finish(session, state, code)
            cloud_do_sign(session, state, code, name)
        elif "AI" in name or "通通" in name:
            cloud_to_finish(session, state, code)
            cloud_ai_chat(session, state, code, name)
        elif any(k in name for k in ("微信备份", "通讯录", "上传容量", "1GB", "邀请")):
            print(f"  云盘: [{name}] 需真实行为，跳过")
        else:
            cloud_to_finish(session, state, code)
            sleep(1)
            cloud_do_popup(session, state, name)


def cloud_upload2c(session, state, url, file_name, content, referer=None):
    token = (state or {}).get("userToken") or ""
    if not token:
        return False, "缺少云盘 userToken"
    file_info = {
        "batchNo": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "fileName": file_name,
        "fileSize": len(content),
        "fileType": 1,
        "directoryId": "0",
        "spaceType": "0",
    }
    form = {
        "uniqueId": f"{int(time.time() * 1000)}_{random.randint(100000, 999999)}",
        "accessToken": token,
        "psToken": "",
        "totalPart": "1",
        "partSize": str(len(content)),
        "partIndex": "1",
        "channel": "wocloud",
        "fileName": file_name,
        "fileSize": str(len(content)),
        "directoryId": "0",
        "spaceType": "0",
        "fileInfo": cloud_encrypt_fileinfo(file_info, token),
    }
    headers = {
        "User-Agent": APP_UA,
        "Referer": referer or "https://panservice.mail.wo.cn/",
        "accessToken": token,
        "access-token": token,
    }
    try:
        res = session.post(url, data=form, files={"file": (file_name, content, "text/plain")}, headers=headers, timeout=30)
        data = res.json()
    except Exception as e:
        return False, str(e)[:120]
    if str(data.get("code")) == "0000":
        fid = data.get("data", {}).get("fid", "") if isinstance(data.get("data"), dict) else ""
        return True, f"上传成功 {file_name} fid={str(fid)[:24]}"
    return False, str(data.get("msg") or data.get("message") or data.get("code") or res.text[:80])


def cloud_signed_post(session, state, path, key, activity_id, extra=None, headers=None):
    hdrs = headers or cloud_activity_headers(state, activity_id)
    try:
        ts = session.post(
            "https://panservice.mail.wo.cn/activity/getTimestamp",
            headers=hdrs,
            json={"key": key},
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  云盘活动: getTimestamp 异常: {e}")
        return {}
    result = (ts.get("result") if isinstance(ts.get("result"), dict) else None) or ((ts.get("data") or {}).get("result") if isinstance(ts.get("data"), dict) else {}) or {}
    nonce, timestamp = result.get("nonce"), result.get("timestamp")
    if not nonce or not timestamp:
        print(f"  云盘活动: getTimestamp 失败 {cloud_meta_code(ts)}")
        return {}
    body = {"activityId": activity_id, **(extra or {})}
    body["nonce"] = nonce
    body["timestamp"] = timestamp
    body["sign"] = cloud_activity_sign(body)
    try:
        return session.post(
            f"https://panservice.mail.wo.cn{path}",
            headers=hdrs,
            json=body,
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  云盘活动: {path} 异常: {e}")
        return {}


def campus_headers(state, activity_id):
    token = (state or {}).get("userToken") or ""
    return {
        "X-YP-Access-Token": token,
        "token": token,
        "Access-Token": token,
        "source-type": "woapi",
        "clientId": "1001000165",
        "X-YP-Client-Id": CLOUD_CLIENT_ID,
        "Content-Type": "application/json",
        "requestTime": str(int(time.time() * 1000)),
        "User-Agent": APP_UA,
        "Origin": "https://panservice.mail.wo.cn",
        "Referer": (
            "https://panservice.mail.wo.cn/h5/activitymobile/campusSeason"
            f"?activityId={quote(activity_id)}&type=02&token={token}&clientid={CLOUD_CLIENT_ID}"
        ),
    }


def campus_task(session, state):
    print("==== 云盘校园季 ====")
    if not (state or {}).get("userToken"):
        print("  校园季: 缺少 userToken，跳过")
        return
    activity_id = cloud_env("UNICOM_CAMPUS_ACTIVITY_ID", CAMPUS_ACTIVITY_DEFAULT)
    headers = campus_headers(state, activity_id)
    try:
        r = session.post(
            "https://panservice.mail.wo.cn/activity/task/activate",
            headers=headers,
            json={"activityId": activity_id},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  校园季: 激活异常: {e}")
        return
    if cloud_meta_code(r) != "200":
        print(f"  校园季: 激活失败 {r.get('meta', {}).get('message') or cloud_meta_code(r)}")
        return
    print("  校园季: 激活成功")
    tl = cloud_signed_post(session, state, "/activity/school/task/list", "activity:school:activate", activity_id, headers=headers)
    done = {}
    for t in ((tl.get("result") or {}).get("taskList") or []):
        code = str(t.get("taskCode") or "")
        name = t.get("taskName") or code
        daily = safe_int(t.get("dailyLimit"), 0)
        cur = safe_int(t.get("doneCount"), 0)
        if code in ("30004", "30008"):
            done[code] = daily > 0 and cur >= daily
            print(f"  校园季: [{name}] {cur}/{daily}{' (已满)' if done[code] else ''}")
    if done.get("30004"):
        print("  校园季: 上传任务已满，跳过")
    else:
        ok, msg = cloud_upload2c(session, state, CAMPUS_UPLOAD_URL, "1.txt", b"1", referer="https://panservice.mail.wo.cn/")
        print(f"  校园季: 上传{'成功' if ok else '失败'}: {msg}")
        if ok:
            sleep(3)
    if done.get("30008"):
        print("  校园季: AI 任务已满，跳过")
    else:
        cloud_ai_chat(session, state, "30008", "学习助手")
    try:
        lt = session.get(
            "https://panservice.mail.wo.cn/activity/lottery/lottery-times",
            params={"activityId": activity_id},
            headers=headers,
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  校园季: 查询抽奖次数异常: {e}")
        return
    times = lt.get("result")
    times = times if isinstance(times, int) else 0
    if times <= 0:
        print("  校园季: 当前无可抽奖次数")
        return
    for _ in range(min(times, 5)):
        res = cloud_signed_post(session, state, "/activity/lottery", "activity:lottery", activity_id, headers=headers)
        if cloud_meta_code(res) == "200":
            prize = (res.get("result") or {}).get("prizeName") or "未知奖品"
            print(f"  校园季: 抽奖成功 {prize}")
        else:
            print(f"  校园季: 抽奖失败 {res.get('meta', {}).get('message') or cloud_meta_code(res)}")
            break
        sleep(1.5)


def battle_headers(state, activity_id, referer=""):
    token = (state or {}).get("userToken") or ""
    return {
        "X-YP-Access-Token": token,
        "Accept": "application/json, text/plain, */*",
        "source-type": "woapi",
        "requestTime": str(int(time.time() * 1000)),
        "User-Agent": APP_UA,
        "clientId": "1001000165",
        "X-SH-Access-Token": "",
        "X-YP-GRAY-FLAG": "undefined",
        "Content-Type": "application/json",
        "X-YP-Client-Id": CLOUD_CLIENT_ID,
        "token": token,
        "Origin": "https://panservice.mail.wo.cn",
        "Referer": referer or (
            f"https://panservice.mail.wo.cn/h5/activitymobile/{CLOUD_BATTLE_PAGE}"
            f"?activityId={quote(activity_id)}&type=02&touchpoint={CLOUD_BATTLE_TOUCHPOINT}"
            f"&clientid={CLOUD_CLIENT_ID}&token={token}"
        ),
    }


def battle_enter(session, state, activity_id):
    token = (state or {}).get("userToken") or ""
    if not token:
        return ""
    entry = (
        f"https://panservice.mail.wo.cn/h5/activitymobile/{CLOUD_BATTLE_PAGE}"
        f"?activityId={quote(activity_id)}&touchpoint={CLOUD_BATTLE_TOUCHPOINT}"
        f"&clientid={CLOUD_CLIENT_ID}&token={token}"
    )
    try:
        r = session.get(
            "https://m.client.10010.com/mobileService/openPlatform/openPlatLineNew.htm",
            params={"to_url": entry},
            headers={"User-Agent": APP_UA},
            allow_redirects=False,
            timeout=15,
        )
    except Exception as e:
        print(f"  上传大比拼: 进入活动页异常: {e}")
        return ""
    url = r.headers.get("location") or r.headers.get("Location") or ""
    for _ in range(4):
        if not url:
            break
        if url.startswith("/"):
            url = urljoin("https://panservice.mail.wo.cn", url)
        q = parse_qs(urlparse(url).query)
        new_token = (q.get("token") or [""])[0]
        if new_token:
            state["userToken"] = new_token
        if "ticket=" in url:
            return url.split("#", 1)[0]
        try:
            nxt = session.get(url, headers={"User-Agent": APP_UA}, allow_redirects=False, timeout=15)
        except Exception:
            break
        loc = nxt.headers.get("location") or nxt.headers.get("Location") or ""
        if not loc or loc == url:
            return url.split("#", 1)[0] if "ticket=" in url else ""
        url = loc
    return ""


def cloud_battle_task(session, state, cookie_header=None):
    print("==== 云盘上传大比拼 ====")
    if not (state or {}).get("userToken"):
        print("  上传大比拼: 缺少 userToken，跳过")
        return
    activity_id = cloud_env("UNICOM_BATTLE_ACTIVITY_ID", CLOUD_BATTLE_DEFAULT)
    referer = battle_enter(session, state, activity_id)
    if not referer:
        print("  上传大比拼: 进入活动页失败")
        return
    headers = battle_headers(state, activity_id, referer)
    try:
        status = session.get(
            "https://panservice.mail.wo.cn/activity/activity-status",
            params={"activityId": activity_id},
            headers=headers,
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  上传大比拼: 查询活动状态异常: {e}")
        return
    if cloud_meta_code(status) != "200":
        print(f"  上传大比拼: 查询活动状态失败 {status.get('meta', {}).get('message') or cloud_meta_code(status)}")
        return
    activity_status = safe_int((status.get("result") or {}).get("activityStatus"), -1)
    if activity_status != 1:
        print("  上传大比拼: 活动未上线或已结束，可用 UNICOM_BATTLE_ACTIVITY_ID 换期")
        return
    try:
        check = session.get(
            "https://panservice.mail.wo.cn/activity/checkActivityStatus",
            params={"activityId": activity_id},
            headers=headers,
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  上传大比拼: 查询冲榜状态异常: {e}")
        return
    opened = safe_int((check.get("result") or {}).get("state"), 0) == 1 if cloud_meta_code(check) == "200" else None
    if opened is None:
        print("  上传大比拼: 查询冲榜状态失败")
        return
    if not opened:
        province_code, province_name = cloud_phone_location(session, state, cookie_header)
        if not province_code or not province_name:
            print("  上传大比拼: 冲榜未开启，缺省份信息")
            return
        try:
            open_res = session.post(
                "https://panservice.mail.wo.cn/activity/openActivity",
                json={
                    "activityId": activity_id,
                    "provinceCode": province_code,
                    "provinceName": province_name,
                },
                headers=headers,
                timeout=10,
            ).json()
        except Exception as e:
            print(f"  上传大比拼: 开启冲榜异常: {e}")
            return
        if cloud_meta_code(open_res) == "200" and safe_int((open_res.get("result") or {}).get("state"), 0) == 1:
            print(f"  上传大比拼: 开启冲榜成功 {province_name}")
        else:
            print(f"  上传大比拼: 开启冲榜失败 {open_res.get('meta', {}).get('message') or cloud_meta_code(open_res)}")
            return
    else:
        print("  上传大比拼: 冲榜已开启")
    try:
        records = session.get(
            "https://panservice.mail.wo.cn/activity/lottery/recordList",
            params={"activityId": activity_id},
            headers=headers,
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  上传大比拼: 查询抽奖记录异常: {e}")
        return
    today = env_today()
    for item in records.get("result") or []:
        if isinstance(item, dict) and str(item.get("createTime") or "")[:10] == today:
            print("  上传大比拼: 今日已抽奖")
            return
    def battle_times():
        try:
            res = session.get(
                "https://panservice.mail.wo.cn/activity/lottery/lottery-times",
                params={"activityId": activity_id},
                headers=headers,
                timeout=10,
            ).json()
        except Exception as e:
            print(f"  上传大比拼: 查询抽奖次数异常: {e}")
            return None, 0
        result = res.get("result")
        count = result if isinstance(result, int) else 0
        return res, max(count, 0)

    times_res, times = battle_times()
    if times_res is None:
        return
    if times <= 0:
        upload_urls = [
            u.strip()
            for u in cloud_env("UNICOM_BATTLE_UPLOAD_URL", CLOUD_BATTLE_UPLOAD_DEFAULT).split(",")
            if u.strip()
        ]
        file_name = cloud_env("UNICOM_CLOUD_BATTLE_FILE", "文本.txt") or "文本.txt"
        content = (cloud_env("UNICOM_CLOUD_BATTLE_CONTENT", "1") or "1").encode("utf-8")
        uploaded = False
        for url in upload_urls:
            ok, msg = cloud_upload2c(session, state, url, file_name, content, referer=referer)
            print(f"  上传大比拼: {msg}")
            if ok:
                uploaded = True
                break
        if uploaded:
            for i in range(8):
                if i:
                    sleep(1)
                _, times = battle_times()
                if times > 0:
                    break
        if times <= 0:
            print("  上传大比拼: 上传后未获得抽奖次数")
            return
    print(f"  上传大比拼: 抽奖次数 {times}")
    res = cloud_signed_post(session, state, "/activity/lottery", "activity:lottery", activity_id, headers=headers)
    if cloud_meta_code(res) == "200":
        prize = (res.get("result") or {}).get("prizeName") or "未知奖品"
        print(f"  上传大比拼: 抽奖成功 {prize}")
    else:
        print(f"  上传大比拼: 抽奖失败 {res.get('meta', {}).get('message') or cloud_meta_code(res)}")


def cloud_pan_task(session, cookie_header=None):
    print("==== 联通云盘 ====")
    state = cloud_pan_login(session, cookie_header)
    if not state:
        return
    sleep(0.5)
    cloud_userinfo(session, state)
    cloud_secret_key(session, state)
    cloud_run_daily_tasks(session, state)
    sleep(0.5)
    cloud_userinfo(session, state)
    sleep(1)
    cloud_draw_lottery(session, state)
    sleep(1)
    campus_task(session, state)
    sleep(1)
    cloud_battle_task(session, state, cookie_header)


def woread_aes(data):
    if isinstance(data, dict):
        plain = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    else:
        plain = str(data)
    cipher = AES.new(WOREAD_KEY, AES.MODE_CBC, WOREAD_IV)
    ct = cipher.encrypt(pad(plain.encode("utf-8"), 16))
    return base64.b64encode(ct.hex().encode()).decode()


def woread_aes_phone(phone):
    cipher = AES.new(WOREAD_KEY, AES.MODE_CBC, WOREAD_IV)
    ct = cipher.encrypt(pad(str(phone).encode("utf-8"), 16))
    return base64.b64encode(ct.hex().encode()).decode()


def woread_ts():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def woread_task(session, cookie_header=None, mobile=""):
    print("==== 沃阅读积分 ====")
    ecs_token = session.cookies.get("ecs_token") or cookie_get(cookie_header, "ecs_token")
    mobile = mobile or session.cookies.get("c_mobile") or cookie_get(cookie_header, "c_mobile") or ""
    if not ecs_token or not mobile:
        print("  沃阅读: 缺少 ecs_token 或手机号，跳过")
        return
    hdrs = {
        "User-Agent": APP_UA,
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": "https://10010.woread.com.cn/ng_woread/",
        "Origin": "https://10010.woread.com.cn",
    }
    session.cookies.set("ecs_token", ecs_token, domain=".woread.com.cn")
    session.cookies.set("ecs_token", ecs_token, domain=".10010.com.cn")
    session.cookies.set("u_account", mobile, domain=".woread.com.cn")
    ts_ms = str(int(time.time() * 1000))
    md5sig = hashlib.md5(f"{WOREAD_APPID}{WOREAD_APPSECRET}{ts_ms}".encode()).hexdigest()
    try:
        r = session.post(
            f"{WOREAD_BASE}/app/auth/{WOREAD_APPID}/{ts_ms}/{md5sig}",
            headers=hdrs,
            json={"sign": woread_aes({"timestamp": woread_ts()})},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  沃阅读: getAccessToken 异常: {e}")
        return
    accesstoken = ((r.get("data") or {}) if isinstance(r.get("data"), dict) else {}).get("accesstoken") if str(r.get("code")) == "0000" else ""
    if not accesstoken:
        print(f"  沃阅读: getAccessToken 失败: {r.get('message') or r.get('code')}")
        return
    hdrs["accesstoken"] = accesstoken
    try:
        r = session.post(
            f"{WOREAD_BASE}/account/login",
            headers={**hdrs, "noPassToken": "true"},
            json={"sign": woread_aes({"phone": woread_aes_phone(mobile), "timestamp": woread_ts()})},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  沃阅读: accountLogin 异常: {e}")
        return
    if str(r.get("code")) != "0000":
        print(f"  沃阅读: accountLogin 失败: {r.get('message') or r.get('code')}")
        return
    d = r.get("data") or {}
    token, verify_code = d.get("token") or "", d.get("verifycode") or ""
    user_id, user_index = d.get("userid") or "", d.get("userindex") or ""
    if not token or not verify_code:
        print("  沃阅读: accountLogin 凭证不完整")
        return
    print(f"  沃阅读: 登录成功 {mobile[:3]}****{mobile[-4:] if len(mobile) >= 7 else ''}")
    user_fields = {
        "token": token,
        "userId": user_id,
        "userIndex": user_index,
        "userAccount": mobile,
        "verifyCode": verify_code,
    }
    try:
        r = session.post(
            f"{WOREAD_BASE}/activity/getPointCenterTicket",
            headers=hdrs,
            json={"sign": woread_aes({"timestamp": woread_ts(), **user_fields})},
            timeout=15,
        ).json()
    except Exception as e:
        print(f"  沃阅读: 换票异常: {e}")
        return
    well_url = r.get("data") or "" if str(r.get("code")) == "0000" else ""
    if not isinstance(well_url, str) or "ticket=" not in well_url:
        print(f"  沃阅读: 换票失败: {r.get('message') or r.get('code')}")
        return
    ticket = re.search(r"ticket=([^&]+)", well_url).group(1)
    print("  沃阅读: 换票成功")
    try:
        r = session.get(
            "https://m.jf.10010.com/jf-external-application/jftask/getSecretKey",
            headers={
                "ticket": ticket,
                "partnersid": WOREAD_JF_PARTNERS,
                "clienttype": "aiting_unicom",
                "User-Agent": APP_UA,
                "Referer": well_url,
                "Accept": "application/json, text/plain, */*",
            },
            timeout=10,
        )
        data = r.json()
    except Exception as e:
        print(f"  沃阅读: getSecretKey 异常: {e}")
        return
    if str(data.get("code")) != "0000":
        print(f"  沃阅读: getSecretKey 失败: {data.get('message') or data.get('code')}")
        return
    secret_key = ((data.get("data") or {}) if isinstance(data.get("data"), dict) else {}).get("secretKey") or ""
    if not secret_key:
        print("  沃阅读: getSecretKey 无密钥")
        return
    jea = session.cookies.get("_jea_id") or ""
    cookie = r.headers.get("Set-Cookie") or ""
    match = re.search(r"_jea_id=([^;]+)", cookie)
    if match:
        jea = match.group(1)

    def jf_headers():
        ts = str(int(time.time() * 1000))
        nonce = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        sig = hmac.new(secret_key.encode(), f"{nonce}{ts}".encode(), hashlib.sha256).hexdigest()
        return {
            "ticket": ticket,
            "User-Agent": APP_UA,
            "partnersid": WOREAD_JF_PARTNERS,
            "clienttype": "aiting_unicom",
            "Cookie": f"_jea_id={jea}",
            "X-Request-Timestamp": ts,
            "X-Request-Nonce": nonce,
            "X-Request-Signature": sig,
            "Referer": well_url,
            "Origin": "https://m.jf.10010.com",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        }

    chapter_params = {
        "chapterSeno": "3",
        "cntIndex": WOREAD_CNTINDEX,
        "beginChapter": 4,
        "timestamp": woread_ts(),
        **user_fields,
    }
    try:
        r = session.post(
            f"{WOREAD_BASE}/cnt/readChapter?cntindex={WOREAD_CNTINDEX}&chapterallindex={WOREAD_CHAPTERALLINDEX}&chapterseno=3",
            headers=hdrs,
            json={"sign": woread_aes(chapter_params)},
            timeout=15,
        ).json()
        if str(r.get("code")) == "0000":
            print("  沃阅读: readChapter 成功")
        else:
            print(f"  沃阅读: readChapter {r.get('message') or r.get('code')}")
    except Exception as e:
        print(f"  沃阅读: readChapter 异常: {e}")
    sleep(1)
    try:
        session.post(
            f"{WOREAD_BASE}/basics/newreadadd",
            headers=hdrs,
            json={"sign": woread_aes({
                "userid": user_id,
                "cntindex": WOREAD_CNTINDEX,
                "chapterallindex": WOREAD_CHAPTERALLINDEX,
                "cnttype": 1,
                "cntname": "大清权臣李鸿章",
                "chaptertitle": "少年，胸怀壮志",
                "readtype": 1,
                "timestamp": woread_ts(),
                **user_fields,
            })},
            timeout=15,
        )
    except Exception:
        pass
    sleep(1)
    try:
        r = session.post(
            f"{WOREAD_BASE}/history/addReadTime",
            headers=hdrs,
            json={"sign": woread_aes({
                "readTime": 2,
                "cntIndex": WOREAD_CNTINDEX,
                "cntType": 1,
                "cntindex": WOREAD_CNTINDEX,
                "cnttype": 1,
                "chapterallindex": WOREAD_CHAPTERALLINDEX,
                "chapterseno": 3,
                "channelid": "18000688",
                "chapterid": "13120941003",
                "readtype": 1,
                "isend": "0",
                "timestamp": woread_ts(),
                **user_fields,
            })},
            timeout=15,
        ).json()
        if str(r.get("code")) == "0000":
            print(f"  沃阅读: 阅读上报 +2分钟 weektime={(r.get('data') or {}).get('weektime')}")
        else:
            print(f"  沃阅读: 阅读上报 {r.get('message') or r.get('code')} (冷却/已满)")
    except Exception as e:
        print(f"  沃阅读: 阅读上报异常: {e}")
    try:
        r = session.post(
            "https://m.jf.10010.com/jf-external-application/uasptask/sign",
            headers=jf_headers(),
            json={"taskCode": WOREAD_SIGN_TASK},
            timeout=10,
        ).json()
        if str(r.get("code")) == "0000":
            info = r.get("data") or {}
            print(f"  沃阅读: 签到成功 {info.get('title', '')} +{info.get('score', '')}")
        else:
            print(f"  沃阅读: 签到 {r.get('message') or r.get('code')} (可能已签)")
    except Exception as e:
        print(f"  沃阅读: 签到异常: {e}")
    try:
        r = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/taskDetail",
            headers=jf_headers(),
            json={},
            timeout=10,
        ).json()
    except Exception as e:
        print(f"  沃阅读: taskDetail 异常: {e}")
        return
    if str(r.get("code")) != "0000":
        print(f"  沃阅读: taskDetail 失败: {r.get('message') or r.get('code')}")
        return
    tasks = ((r.get("data") or {}).get("taskDetail") or {}).get("taskList") or []
    skip_kw = ("邀请", "会员", "分享", "限时福利")
    claimed = 0
    for t in tasks:
        name = t.get("taskName") or ""
        if any(k in name for k in skip_kw):
            continue
        if safe_int(t.get("finishCount"), 0) >= safe_int(t.get("needCount"), 1):
            continue
        try:
            r2 = session.post(
                "https://m.jf.10010.com/jf-external-application/jftask/toFinish",
                headers=jf_headers(),
                json={"taskCode": t.get("taskCode")},
                timeout=10,
            ).json()
            ok = r2.get("data") is True or str(r2.get("code")) == "0000"
        except Exception:
            ok = False
        print(f"  沃阅读: 领积分 [{name}]: {'成功' if ok else '未达条件'}")
        if ok:
            claimed += 1
        sleep(1)
    try:
        r3 = session.post(
            "https://m.jf.10010.com/jf-external-application/jftask/userInfo",
            headers=jf_headers(),
            json={},
            timeout=10,
        ).json()
        if str(r3.get("code")) == "0000":
            ui = r3.get("data") or {}
            print(f"  沃阅读: 今日积分 {ui.get('todayEarnScore')} 可用 {ui.get('availableScore')} 累计 {ui.get('allEarnScore')}")
    except Exception:
        pass
    print(f"  沃阅读: 共领 {claimed} 项积分")


def run_all(session, cookie_header=None, mobile="", grab_only=False):
    if cookie_header:
        apply_cookie(session, cookie_header)
    if not mobile:
        mobile = session.cookies.get("c_mobile") or cookie_get(cookie_header, "c_mobile") or ""
    if grab_only or is_weekly_grab_window():
        ok = sign_grab_coupon(session, cookie_header, amount="10", wait=True)
        return ok, "抢兑"
    ctx = {}
    ok, msg = sign_get_continuous(session, cookie_header)
    sign_claim_signin_rewards(session, cookie_header)
    sign_get_telephone(session, cookie_header, is_initial=True, ctx=ctx)
    sign_month_sign_gift(session, cookie_header)
    sign_get_task_list(session, cookie_header, mobile=mobile)
    sign_claim_signin_rewards(session, cookie_header)
    points_sign(session, cookie_header)
    extra_daily_tasks(session, cookie_header)
    ttlxj_task(session, cookie_header)
    ttxc_task(session, cookie_header)
    market_rights_lottery(session, cookie_header)
    uphone_points_task(session, cookie_header)
    cloud_pan_task(session, cookie_header)
    woread_task(session, cookie_header, mobile=mobile)
    sign_get_telephone(session, cookie_header, is_initial=False, ctx=ctx)
    sign_query_my_prizes(session, cookie_header)
    return ok, msg


def main():
    load_dotenv()
    grab_only = (os.getenv("UNICOM_GRAB_ONLY") or "").strip() in ("1", "true", "True") or "--grab" in sys.argv
    token_raw = (os.getenv("UNICOM_TOKEN") or "").strip()
    cookie, _ = strip_env_date((os.getenv("UNICOM_COOKIE") or "").strip())
    accounts = load_accounts(os.getenv("UNICOM_ACCOUNT"))
    tokens = load_tokens(token_raw)
    if grab_only:
        print("模式: 仅抢兑 10 元话费券")

    if not cookie and not accounts and not tokens:
        print("未获取到变量 UNICOM_TOKEN / UNICOM_COOKIE / UNICOM_ACCOUNT")
        print("  UNICOM_TOKEN=token_online[#appId]")
        print("  UNICOM_COOKIE=完整Cookie")
        print("  UNICOM_ACCOUNT=手机号#APP登录密码[#appId]")
        return 0

    ok_count = 0

    if tokens:
        print(f"中国联通签到（token_online 模式）：共 {len(tokens)} 个 token")
        for idx, (token, appid) in enumerate(tokens, start=1):
            print(f"\n======== 第 {idx} 个 token ========")
            session = requests.Session()
            seed_device_cookies(session, token, appid)
            ok, msg = online(session, token, appid)
            print(">>>在线登录：", msg)
            if not ok:
                continue
            ok, _ = run_all(session, grab_only=grab_only)
            if ok:
                update_env_date("UNICOM_TOKEN", token_raw, account=token)
                ok_count += 1
            sleep(2)
    elif cookie:
        print("中国联通签到（Cookie 模式）")
        session = requests.Session()
        ok, _ = run_all(session, cookie_header=cookie, grab_only=grab_only)
        if ok:
            update_env_date("UNICOM_COOKIE", os.getenv("UNICOM_COOKIE") or cookie, multi=False)
            ok_count += 1
    else:
        print(f"中国联通签到（密码模式）：共 {len(accounts)} 个账号")
        for idx, (phone, password, appid) in enumerate(accounts, start=1):
            masked = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone
            print(f"\n======== 第 {idx} 个账号 {masked} ========")
            session = requests.Session()
            logged, msg, token = login(session, phone, password, appid)
            print(">>>登录：", msg)
            if not logged:
                if "短信验证码" in msg:
                    print("  联通触发短信验证码风控，密码登录不可用。")
                    print("  请改用 UNICOM_TOKEN=token_online 或 UNICOM_COOKIE。")
                continue
            ok, msg = online(session, token, appid)
            print(">>>在线登录：", msg)
            if not ok:
                continue
            ok, _ = run_all(session, mobile=phone, grab_only=grab_only)
            if ok:
                update_env_date("UNICOM_ACCOUNT", os.getenv("UNICOM_ACCOUNT") or "", account=phone)
                ok_count += 1
            sleep(2)

    print(f"\n完成：成功 {ok_count} 项")
    return 0 if ok_count else 1


if __name__ == "__main__":
    sys.exit(main())
