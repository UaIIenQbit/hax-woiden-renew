
# Woiden And Hax Auto Extend <sup>💯</sup> 
**woiden.id 和 hax.co.id 自动续订，执行该脚本前请配置并运行本人的extend_vps_gethaxcode项目**



> **Note** `Github Action` 运行时所在的服务器IP可能被 `Google` ban 无法使用语音验证，因为公共的服务器被别人用过，IP被识别为机器人，可能上个人刚好也调用了 `Google reCaptcha` ，所以 `Google reCaptcha` 的语音验证调用能否成功随缘，使用 `2Captcha` 和 `YesCaptcha` 的图片验证不受此影响稳如老狗，甚至加载不出来图片也可以验证通过，建议语音图片两个同时使用即稳定也不费钱，或者[托管自己服务器](https://docs.github.com/cn/actions/hosting-your-own-runners/about-self-hosted-runners)，登陆时脚本是先执行语音验证，验证失败再执行图片验证，语音验证频繁调用会被ben ( 没几次就会被ben，不用担心应该就ben一两个小时左右 )，自己服务器使用语音验证最好时间间隔久点


### 环境要求：
 - python：3.9及以上，需要带ssl模块；pip3
 - 系统： windwos/macos/debian 11/ubuntu 20+
 - 硬件： 建议2C2G，脚本运行无头浏览器非常吃计算资源，配置低的vps无法执行成功
 - 网络：干净的外国ip，可以用warp，但是warp对docker容器失效


### 配置文件
文件位置: `config/config.json`，其中参数请自行按照模板更改。`origin_host`的取值范围是`hax.co.id`和`woiden.id`；`asr_choice`属性的取值范围有`TENCENT`,`IBM`,`BAIDU`,`AZURE`；https://app.redislabs.com/ 可以免费领取30M内存的redis。
``` json
{
  "origin_host": "woiden.id",
  "telegramID_of_hax_or_woiden": "",
  "password_of_hax_or_woiden": "",
  "telegram_bot_token_to_send_result": "",
  "telegramID_to_receive_result": "",
  "pushplus_token_to_send_result": "",
  "redis": {
    "host": "",
    "username": "",
    "password": "",
    "port": ""
  },
  "asr_choice": "",
  "asr_tencent": {
    "secret_id": "",
    "secret_key": ""
  },
  "asr_ibm": {
    "ibm_url": "",
    "ibm_key": ""
  },
  "asr_baidu": {
    "app_id": "",
    "api_key": "",
    "secret_key": ""
  },
  "asr_azure": {
    "key": "",
    "region": ""
  },
  "twoCaptcha_api_key": ""
}

```


### linux命令执行
```
 1. apt install ffmpeg -y 
 2. pip3 install --no-cache-dir -r requirements.txt
 3. playwright install --with-deps
 4. 配置config/config.json
 5. python3 main.py
```

### docker执行
``` shell
mkdir woiden_extend_temp
cd woiden_extend_temp
# 这里的config.json请自己补充内容
touch config.json

docker run -it --rm  \
    -v $PWD/:/app/config \
    --name woiden_extend_temp \
    mrzyang/woiden_extend:v230219

```
