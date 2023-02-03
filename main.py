"""
author: Zakkoree
"""
# python -m playwright codegen --target python -o 'my.py' -b chromium https://woiden.id/login
# 安装playwright库
# pip install playwright

# 安装浏览器驱动文件（安装过程稍微有点慢）
# playwright install-deps --with-deps
# playwright install --with-deps

import re
import os
import sys
import time
import random
import requests
import ffmpy3
import urllib
import telepot
import ibmAPI
import tencentAPI
import azureAPI
import json
from aip import AipSpeech
from commonlog import Logger
from playwright.sync_api import Playwright, sync_playwright, expect
from twocaptcha import TwoCaptcha
import redis
from pydub import AudioSegment


with open('config/config.json', 'r') as f:
    config = json.load(f)

origin_host = config['origin_host']
telegramID_of_hax_or_woiden = config['telegramID_of_hax_or_woiden']
password_of_hax_or_woiden = config['password_of_hax_or_woiden']
telegram_bot_token_to_send_result = config['telegram_bot_token_to_send_result']
telegramID_to_receive_result = config['telegramID_to_receive_result']
pushplus_token_to_send_result = config['pushplus_token_to_send_result']

redis_host = config['redis']['host']
redis_port = int(config['redis']['port'])
redis_username = config['redis']['username']
redis_password = config['redis']['password']

asr_choice = config['asr_choice']
asr_tencent_secret_id = config['asr_tencent']['secret_id']
asr_tencent_secret_key = config['asr_tencent']['secret_key']
asr_ibm_url = config['asr_ibm']['ibm_url']
asr_ibm_key = config['asr_ibm']['ibm_key']
asr_baidu_app_id = config['asr_baidu']['app_id']
asr_baidu_api_key = config['asr_baidu']['api_key']
asr_baidu_secret_key = config['asr_baidu']['secret_key']
asr_azure_key = config['asr_azure']['key']
asr_azure_region = config['asr_azure']['region']

twoCaptcha_api_key = config['twoCaptcha_api_key']

print("将要自动续签的域名是：", origin_host)
print("将要自动续签的telegramID是:", telegramID_of_hax_or_woiden)

GITHUB = False
# 用户信息


renew_path = "/vps-renew"
login_path = "/login"
info_path = "/vps-info"
renew_code_path = '/vps-renew-code'
google_recaptchaV3_js_path = "/dist/js/renew-vps.js"

# 网络连接超时时间（1000ms=1s）
timeout = 1000 * 60 * 2
# 登陆重试次数
loginRetryNum = 2
# 续订重试次数  0=直到续订成功(虽然不用重新登陆验证,但不建议使用0,不可控,正常的5次以内可以成功)  
extendRetryNum = 10
# 续订重试间隔时间（秒）
intervalTime = 10

additional_information = '''@Zakkoree https://github.com/Zakkoree/woiden_extend'''
additional_information_ten = '''@Zakkoree <a href="https://github.com/Zakkoree/woiden_extend">https://github.com/Zakkoree/woiden_extend</a>'''
 
logger = Logger(LoggerName="Extend")

message = None

## 延迟停留
def delay():
    time.sleep(random.randint(2, 5))

## 电报机器人和pushplus公众号推送消息-续期结果
def send(txt):
    try:
        sendmessage = '''{0} {1}
        {2}'''.format(origin_host, txt, additional_information)
        bot = telepot.Bot(telegram_bot_token_to_send_result)
        bot.sendMessage(telegramID_to_receive_result, sendmessage, parse_mode=None, disable_web_page_preview=None, disable_notification=None,
                    reply_to_message_id=None, reply_markup=None)
        logger.info("Telebot push")
    except Exception as e:
        logger.error(e)
    # tencent push
    try:
        url = 'http://www.pushplus.plus/send'
        data = {
            "token":pushplus_token_to_send_result,
            "title":origin_host,
            # "template":"markdown",
            "content": "telegramID: " + telegramID_of_hax_or_woiden + "--" + txt + additional_information_ten
        }
        body=json.dumps(data).encode(encoding='utf-8')
        headers = {'Content-Type':'application/json'}
        requests.post(url,data=body,headers=headers)
        logger.info("Tencent push")
    except Exception as e:
        logger.error(e)


## 主函数 打开无头浏览器并执行js脚本
def main(playwright: Playwright) -> None:
    #browser = playwright.chromium.launch(headless=True)
    #browser = playwright.firefox.launch(headless=True)
    browser = playwright.webkit.launch(headless=True)
    context = browser.new_context()
    context.set_default_timeout(timeout)
    # Open new page
    page = context.new_page()
    js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        window.navigator.chrome = {
            runtime: {},
            // etc.
        };
        """
    page.add_init_script(js)
    
    run(page)
    context.close()
    browser.close()

def fill_hax_bot_code(page):
    global message
    try:
        # 这句换貌似没有用，还是要手动跳转的
        page.get_by_role("link", name="INPUT RENEW CODE").click()
        adsClear(page)
        delay()
        # 这里需要手动跳转下，playwright不会自己跳转
        openVpsRenewCodeUrl(page)
        delay()
        hax_bot_code_try_limit = 5
        present_hax_bot_code_try_times = 0
        while (True):
            present_hax_bot_code_try_times += 1
            logger.info("hax_bot_code页面-开始第" + str(present_hax_bot_code_try_times) + "次尝试")
            if reCAPTCHA2(page) == False:
                logger.error("hax_bot_code页面reCAPTCHA v2验证失败")
                if present_hax_bot_code_try_times >= hax_bot_code_try_limit:
                    logger.error("hax_bot_code页面尝试" + str(hax_bot_code_try_limit) + "次均为成功，程序退出")
                    sys.exit()
                else:
                    delay()
                    openVpsRenewCodeUrl(page)
            else:
                break
            
        delay()
        # 这里的name填标签包含的文本
        page.get_by_role("button", name="Renew VPS").click()
        loadingIndex = 0
        body = ""
        while True:
            body = page.evaluate('''()=>{return $('#response').text()}''')
            loading = "Loading" in body
            if loading:
                if loadingIndex <= 5:
                    loadingIndex += 1
                    time.sleep(5)
                else:
                    logger.warn("bark push body Load timeout")
                    return False
            else:
                break
        logger.info("续期结果:" + str(body))
        message = body
        return "Your VPS has been renewed" in body
    except Exception as e:
        logger.error("hax_bot_code页面浏览器操作出现异常:" + e)
        sys.exit()


def run(page):
    global message
    if reCAPTCHA(page) == False:
        loginRetry(page)
        sys.exit()
    # login
    try:
        logger.info("click login")
        with page.expect_response(re.compile(r"(/#)|(" + info_path + ")"), timeout=timeout*2) as result:
            page.get_by_role("button", name="Submit").click()
    except Exception as e:
        logger.error(e)
        loginRetry(page)
        sys.exit()
        
    checkInfo(page)
    # 验证码V3
    tokenCode = recaptchaV3(page)
    # Extend VPS link
    extendState = extend(page, tokenCode)    
    ###### 这里还要写下一步的hax_bot_code验证 ##############
    ## 第1步，点击  内容为INPUT RENEW CODE的按钮，页面跳转到 https://woiden.id/vps-renew-code

    ## 第2步  id="code" 的input中填入从redis中获取的hax_bot_code
    ##        id="captcha"的input中填入图形验证码，可以直接从html中获取
    ##        id="rc-anchor-container"的reCAPTCHA验证
    ##        点击name="submit_button"的按钮，提交续期

    ## 第3步  等待5秒左右，获取id="response"中的文本,
    ##        若类似"Your VPS has been renewed until February 21, 2023"，则续期成功，extendState2置为true
    
    extendState2 = False
    if extendState:
        # 下面函数执行完，如果返回true，则将extendState2置为true
        extendState2 = fill_hax_bot_code(page)
    else:
        logger.error("输入hax_bot_code前面的步骤没走完,程序退出!")
        sys.exit()
    
    if extendState2:
        if GITHUB:
            try:
                now = int(time.time())
                # 转换为其他日期格式，如："%Y-%m-%d %H:%M:%S"
                timeArr = time.localtime(now)
                other_StyleTime = time.strftime("%Y-%m-%d", timeArr)
                update=open('renewTime', 'w')
                update.write(other_StyleTime)
                update.close()
            except Exception as e:
                logger.error(e)
        logger.info("renew succeed")
        teleinfomsg = '''Renew Succeed👌
        
        {0}
        '''.format(message)
        send(teleinfomsg)
    else:
        logger.error("renew fail")
        if GITHUB:
            try:
                f=open('renewTime', 'r',encoding='utf-8')
                lastTime = f.read()
            # barkPush('[ERROR] renew fail')
                teleinfomsg = '''Renew Fail ‼
        Please try again or wait for the next automatic execution
        Last Renew Time {0}
        '''.format(lastTime)
                send(teleinfomsg)
                f.close()
            except Exception as e:
                logger.error(e)
            
        else:
            teleinfomsg = '''Renew Fail ‼
        Please try again or wait for the next automatic execution
        '''
            send(teleinfomsg)
            
def adsClear(page):
    logger.info("clear adsbygoogle")
    try:
        page.evaluate("$('ins.adsbygoogle').css('display','none');")
    except Exception as e:
        return
    
def checkInfo(page):
    logger.info(origin_host + "check info")
    try:
        page.goto('https://' + origin_host + info_path)
        page.locator('//div[@class="alert alert-warning"]').hover(timeout=3000)
    except:
        label = page.locator("//label[@class='col-sm-5 col-form-label' and text()='Status']/following::span[1]")
        if "ACTIVE" in label.inner_text():
            return
        else:
            logger.error("Your VPS is terminated, Please create a new one")
            teleinfomsg = '''Renew Fail ‼
            
        Your VPS is terminated, Please create a new one
            '''
            send(teleinfomsg)
            sys.exit()
    else:
        logger.error("You have no VPS yet, Please create a")
        teleinfomsg = '''Renew Fail ‼
        
        You have no VPS yet, Please create a
        '''
        send(teleinfomsg)
        sys.exit()

openLoginNum = 0
def openLoginUrl(page):
    global openLoginNum
    try:
        if origin_host == "woiden.id":
            logger.info("load woiden.id")
        elif origin_host == "hax.co.id":
            logger.info("load hax.co.id")
        else:
            logger.error("host erroe")
            teleinfomsg = '''HOST ERROR ‼
        
        Erreur de configuration de la host
        '''
            send(teleinfomsg)
            sys.exit()
        page.goto('https://' + origin_host + login_path)
        adsClear(page)
        logger.info("fill username")
        page.locator("input[id=\"text\"]").fill(telegramID_of_hax_or_woiden)
        logger.info("fill password")
        page.locator("input[id=\"password\"]").fill(password_of_hax_or_woiden)
        page.click('iframe[title="reCAPTCHA"]')
        page.click('iframe[title="reCAPTCHA"]')
    except Exception as e:
        logger.error("open login url fail")
        logger.error(e)
        if openLoginNum <= loginRetryNum + 1:
            openLoginNum += 1
            logger.info("try open login url " + str(openLoginNum))
            openLoginUrl(page)
        else:
            logger.error("open login url fail")
    else:
        openLoginNum = 0

def openVpsRenewCodeUrl(page):
    try:
        page.goto('https://' + origin_host + renew_code_path)
        time.sleep(12)
        #r = redis.Redis(host='eeeoa.com', port=8899, decode_responses=True)
        r = redis.Redis(host=redis_host, port=redis_port, username=redis_username, password=redis_password, decode_responses=True)
        hax_bot_code = r.get('hax_bot_code_' + telegramID_of_hax_or_woiden)
        print("redis中的hax_bot_code = " + hax_bot_code)  # 取出键 name 对应的值
        page.locator("input[id=\"code\"]").fill(hax_bot_code)
        page.locator("input[id=\"captcha\"]").fill(str(numCAPTCHA(page)))
        page.click('iframe[title="reCAPTCHA"]')
        page.click('iframe[title="reCAPTCHA"]')
    except Exception as e:
        logger.error("打开 vps renew code页面失败")
        logger.error(e)
    return

authRetry = 0
def loginRetry(page):
    global authRetry
    if authRetry >= loginRetryNum:
        logger.error("longin failed!")
        teleinfomsg = '''Longin Failed ‼
        
        Invalid Username / Password Or Validation of invalid ⁉
        '''
        send(teleinfomsg)
        sys.exit()
    else:
        authRetry += 1
        logger.warn("You have to log in!")
        logger.info("try login " + str(authRetry))
        run(page)

# 懂得可以试试  
def recaptchaV3(page):
    return None

extendRetry = 0

def extend(page, tokenCode):
    global extendRetry
    global message
    logger.info("click Extend VPS")
    try:
        page.goto('https://' + origin_host + renew_path)
    except Exception as e:
        logger.error("renew_path Timeout")
        logger.error(e)
        # 续订固定重试次数
        if extendState or loadingIndex>5:
            if extendRetryNum == 0:
                logger.info("After " + str(intervalTime) + " seconds try renew " + str(extendRetry))
                time.sleep(intervalTime)
                extend(page, tokenCode)
            else:
                extendRetry += 1
                if extendRetry >= extendRetryNum + 1:
                    return False
                logger.info("After " + str(intervalTime) + " seconds try renew " + str(extendRetry))
                time.sleep(intervalTime)
                if extend(page, tokenCode):
                    return True
        else:
            #message = body
            return True
      
    adsClear(page)
    if tokenCode != None:
        javacsript = """$("button[name='submit_button']").unbind('click').click(function(){$('#form-submit').prepend('<input type="hidden" name="token" value="{token}">');$('#form-submit').prepend('<input type="hidden" name="action" value="renew_vps">');$("html, body").animate({scrollTop:300},"slow");$("#response").html('<div class="progress" id="progress"><div class="progress-bar progress-bar-success progress-bar-striped" role="progressbar" aria-valuenow="40" aria-valuemin="0" aria-valuemax="100" style="width: 10%"><span class="sr-only">Loading.....</span></div></div>'),$(".progress-bar").animate({ width:"25%"}),$(".progress-bar").animate({width:"55%"}),$.ajax({ type:"POST",url:"/renew-vps-process/",data: $("form.submit").serialize(),success:function (a) {$(".progress-bar").animate({ width:"70%"}),$(".progress-bar").animate({width:"100%"}),$("#response").html(a),$("#form-submit").hide(1000)},error:function(){alert("Something wrong !")}})})""".replace("{token}",  tokenCode)
        page.evaluate(javacsript)
    else:
        logger.info("recaptchaV3 token is none")
    # input web address
    logger.info("fill web address")
    page.locator("input[id=\"web_address\"]").fill(origin_host)
    # captcha
    logger.info("do CAPTCHA")
    page.fill("#captcha", str(numCAPTCHA(page)))
    # page.locator("input[id=\"captcha\"]").fill(captcha.numCAPTCHA(page))
    delay()
    # agreement check
    logger.info("click agreement")
    page.click(".form-check-input")

    delay()
    logger.info("click Renew VPS")

    with page.expect_response(re.compile(r"renew-vps-process"), timeout=timeout) as result:
        page.query_selector("button[name=submit_button]").click()
    loadingIndex = 0
    body = ""

    while True:
        body = page.evaluate('''()=>{return $('#response').text()}''')
        loading = "Loading" in body
        if loading:
            if loadingIndex <= 5:
                loadingIndex += 1
                time.sleep(5)
            else:
                logger.warn("bark push body Load timeout")
                return False
        else:
            break

    login = "log" in body
    
    if login:
        loginRetry(page)
        sys.exit()
    
    extendState = "failed" in body

    # 续订固定重试次数
    if extendState or loadingIndex>5:
        if extendRetryNum == 0:
            logger.info("After " + str(intervalTime) + " seconds try renew " + str(extendRetry))
            time.sleep(intervalTime)
            extend(page, tokenCode)
        else:
            extendRetry += 1
            if extendRetry >= extendRetryNum + 1:
                return False
            logger.info("After " + str(intervalTime) + " seconds try renew " + str(extendRetry))
            time.sleep(intervalTime)
            if extend(page, tokenCode):
                return True
    else:
        return True

def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()


def mp3_change_pcm(audioFile):
    logger.info("Audio frequency transcoding")
    # outpath = os.getcwd() + "audio.pcm"
    outpath = os.getcwd() + '/audio.pcm' if '/' in os.getcwd() else os.getcwd() + '\\audio.pcm'
    ff = ffmpy3.FFmpeg(
        inputs={audioFile: '-y'},
        outputs={
            outpath.format(audioFile): '-acodec pcm_s16le -f s16le -ac 1 -ar 16000'}
    )
    ff.run()
    return outpath

def transform_mp3_to_wav(mp3Path):
    wavPath = os.getcwd() + '/audio.wav' if '/' in os.getcwd() else os.getcwd() + '\\audio.wav'
    sound = AudioSegment.from_file(mp3Path, format="mp3")
    sound.export(wavPath, format="wav")
    return wavPath

def audioToText(audioFile, url):
    ASR_CHOICE = None
    try:
        ASR_CHOICE = asr_choice
    except:
        logger.error("ASR_CHOICE is not set, skip ASR")
        return None
    try:
        if ASR_CHOICE == 'BAIDU':
            return baiduAPI(asr_baidu_app_id, asr_baidu_api_key, asr_baidu_secret_key, mp3_change_pcm(audioFile))

        elif ASR_CHOICE == 'IBM':
            return ibmAPI.asr(asr_ibm_key, asr_ibm_url, audioFile)

        elif ASR_CHOICE == 'TENCENT':
            return tencentAPI.asr(asr_tencent_secret_id, asr_tencent_secret_key, url)
        
        elif ASR_CHOICE == 'AZURE':
            wavPath = transform_mp3_to_wav(audioFile)
            delay()
            return azureAPI.asr_wav(asr_azure_key, asr_azure_region, wavPath)
        else :
            logger.warn("ASR_CHOICE setup error, skip ASR")
            return None
    except Exception as e:
        logger.error(e)
        return None
            

def baiduAPI(APP_ID, API_KEY, SECRET_KEY, audioFile):
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
    jsonResult = client.asr(get_file_content(audioFile), 'pcm', 16000, {'dev_pid': 1737,})
    result = jsonResult['result'][0]
    logger.info("udio verify code:" + str(jsonResult))
    return result

# 调2Captcha接口过图形验证码
def twoCaptcha(page):
    openLoginUrl(page)
    try:
        solver = TwoCaptcha(twoCaptcha_api_key)
        g_recaptcha = page.locator(".g-recaptcha")
        sitekey = g_recaptcha.get_attribute("data-sitekey")
        result = solver.recaptcha(
            # 这里注意下，再验证 hax_bot_code的那页，下面的login_path要不要改成
            sitekey=sitekey, url='https://' + origin_host + login_path)
        logger.info("recaptcha_res" + str(result))
        page.evaluate(
            """document.querySelector('[name="g-recaptcha-response"]').innerText='{}'""".format(result['code']))
        logger.info("reCAPTCHA picture done")

        page.evaluate(
            """$.each($('body>div'),function(index,e){a=$('body>div').eq(index);if(a.css('z-index')=='2000000000'){a.children('div').eq(0).click()}})""")

        return True
    except Exception as e:
        logger.error(e)
        return False

# 过reCAPTCHA验证码，先尝试腾讯语音验证，再尝试 调2Captcha接口过图形验证码
def reCAPTCHA(page):
    openLoginUrl(page)
    try:
        # 获取iframe中id="recaptcha-anchor"的span，判断其是否有recaptcha-checkbox-checked类样式，如果有，直接return True
        iframe_anchor = page.frame_locator("xpath=//iframe[starts-with(@src,'https://www.recaptcha.net/recaptcha/api2/anchor')]")
        #print("我将要打印#recaptcha-anchor--class属性:", iframe_anchor.locator('#recaptcha-anchor').get_attribute('class', timeout = 10000))
        if 'recaptcha-checkbox-checked' in iframe_anchor.locator('#recaptcha-anchor').get_attribute('class', timeout = 10000):
            return True

        iframe = page.frame_locator("xpath=//iframe[starts-with(@src,'https://www.recaptcha.net/recaptcha/api2/bframe')]")
        iframe.locator("#recaptcha-audio-button").click(timeout=10000)
        # get the mp3 audio file  http协议的网络资源
        src = iframe.locator("#audio-source").get_attribute("src", timeout = 10000)
        logger.info("Audio src:" + str(src))
        outPath = os.getcwd() + '/audio.mp3' if '/' in os.getcwd() else os.getcwd() + '\\audio.mp3'
        # download the mp3 audio file from the source
        urllib.request.urlretrieve(src, outPath)

        # Speech To Text Conversion
        key = audioToText(outPath, src)
        logger.info("Recaptcha Key:" + str(key))

        # key in results and submit
        audio_response = iframe.locator("#audio-response")
        audio_response.fill(key)
        # 模拟键盘按下回车
        audio_response.press('Enter')

        err = iframe.locator(".rc-audiochallenge-error-message")
        if err.get_attribute("text") == "" or err.is_visible() == False:
            logger.info("reCAPTCHA audio done")
            return True

    except Exception as e:
        logger.error(e)
        logger.warn(
            "Possibly blocked by google. Change IP,Use Proxy method for requests")
        logger.info("Audio verify fail,try picture fuck reCAPTCHA")
        return twoCaptcha(page)
    
# 调2Captcha接口过图形验证码
def twoCaptcha2(page):
    openVpsRenewCodeUrl(page)
    try:
        solver = TwoCaptcha(twoCaptcha_api_key)
        g_recaptcha = page.locator(".g-recaptcha")
        sitekey = g_recaptcha.get_attribute("data-sitekey")
        result = solver.recaptcha(
            # 这里注意下，再验证 hax_bot_code的那页，下面的login_path要不要改成
            sitekey=sitekey, url='https://' + origin_host + renew_code_path)
        logger.info("recaptcha_res" + str(result))
        page.evaluate(
            """document.querySelector('[name="g-recaptcha-response"]').innerText='{}'""".format(result['code']))
        logger.info("reCAPTCHA picture done")

        page.evaluate(
            """$.each($('body>div'),function(index,e){a=$('body>div').eq(index);if(a.css('z-index')=='2000000000'){a.children('div').eq(0).click()}})""")

        return True
    except Exception as e:
        logger.error(e)
        return False

def reCAPTCHA2(page):
    try:
        # 获取iframe中id="recaptcha-anchor"的span，判断其是否有recaptcha-checkbox-checked类样式，如果有，直接return True
        iframe_anchor = page.frame_locator("xpath=//iframe[starts-with(@src,'https://www.recaptcha.net/recaptcha/api2/anchor')]")
        #print("我将要打印#recaptcha-anchor--class属性:", iframe_anchor.locator('#recaptcha-anchor').get_attribute('class', timeout = 10000))
        if 'recaptcha-checkbox-checked' in iframe_anchor.locator('#recaptcha-anchor').get_attribute('class', timeout = 10000):
            return True
        
        iframe = page.frame_locator("xpath=//iframe[starts-with(@src,'https://www.recaptcha.net/recaptcha/api2/bframe')]")
        iframe.locator("#recaptcha-audio-button").click(timeout=10000)
        # get the mp3 audio file  http协议的网络资源
        src = iframe.locator("#audio-source").get_attribute("src", timeout = 10000)
        logger.info("Audio src:" + str(src))
        outPath = os.getcwd() + '/audio.mp3' if '/' in os.getcwd() else os.getcwd() + '\\audio.mp3'
        # download the mp3 audio file from the source
        urllib.request.urlretrieve(src, outPath)

        # Speech To Text Conversion
        key = audioToText(outPath, src)
        logger.info("Recaptcha Key:" + str(key))

        # key in results and submit
        audio_response = iframe.locator("#audio-response")
        audio_response.fill(key)
        # 模拟键盘按下回车
        audio_response.press('Enter')

        err = iframe.locator(".rc-audiochallenge-error-message")
        if err.get_attribute("text") == "" or err.is_visible() == False:
            logger.info("reCAPTCHA audio done")
            return True

    except Exception as e:
        logger.error(e)
        logger.warn(
            "Possibly blocked by google. Change IP,Use Proxy method for requests")
        logger.info("Audio verify fail,try picture fuck reCAPTCHA")
        return twoCaptcha2(page)

def numCAPTCHA(page):
    # 获取 captcha 图片链接
    number1 = int(page.query_selector(
        'xpath=//*[@id="form-submit"]/div[2]/div[1]/img[1]').get_attribute('src').split('-')[1][0])
    caculateMethod = re.sub(r"(\n)|(\t)", "", page.evaluate(
        '''() => {return $(".col-sm-3").text()}'''))[0:1]
    number2 = int(page.query_selector(
        'xpath=//*[@id="form-submit"]/div[2]/div[1]/img[2]').get_attribute('src').split('-')[1][0])

    if caculateMethod == '+':
        captcha_result = number1 + number2
    elif caculateMethod == '-':
        captcha_result = number1 - number2
    elif caculateMethod == 'X':
        captcha_result = number1 * number2
    elif caculateMethod == '/':
        captcha_result = number1 / number2

    logger.info("renewal verify code:" + str(number1) +
                str(caculateMethod) + str(number2) + '=' + str(captcha_result))
    return captcha_result


if __name__ == '__main__':
    with sync_playwright() as playwright:
        main(playwright)
