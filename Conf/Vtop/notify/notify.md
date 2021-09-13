# pushplus

Post

`http://www.pushplus.plus/send`
```
{
  "token": `xxxxxxxxxxxxxxxxxxxx`,
  "title": `$title$`,
  "content": `$body$\n$url$`,
  "Content-Type": `application/json`
}
```
# telegram

## [TG 反代国内机免翻墙](https://github.com/Oreomeow/VIP/blob/main/Conf/Vtop/notify/TGNginx.md#elecv2p-%E4%BD%BF%E7%94%A8-tg-%E9%80%9A%E7%9F%A5tg-%E5%8F%8D%E4%BB%A3%E5%9B%BD%E5%86%85%E6%9C%BA%E5%85%8D%E7%BF%BB%E5%A2%99)

Post

`https://api.telegram.org/botxxxxxxxxxx/`

```
{
  "method": "sendMessage",
  "chat_id": xxxxxxxxxx,
  "text": `$title$\n$body$\n$url$`
}
```

# dingtalk

Post

`https://oapi.dingtalk.com/robot/send?access_token=XXXXXX`

```
{ 
 "msgtype": "markdown", 
 "markdown": { 
 "title": `$title$`, 
 "text": `$title$ \n> $body$\n$url$`  
 } 
}
```

# server 酱

Post
 
`https://sc.ftqq.com/[SCKEY(登入后可见)].send`  
or  
`https://sctapi.ftqq.com/SENDKEY.send`

```
{
  "text": `$title$`,
  "desp": `$body$可以随便加点自定义文字[链接]($url$)`
}
```

# 企业微信

``` js
// 通知触发的 JS，在 webUI->SETTING 中进行添加
// 功能:
//   - 过滤通知
//   - 自定义个性化通知
//   - 其他 JS 能做的事
//
// 默认带有三个变量 $title$, $body$, $url$
// 通过通知触发的 JS 除 $feed.push 函数不可用之外（防止循环调用），其他默认参数/环境变量都可以直接使用（具体查看: https://github.com/elecV2/elecV2P-dei/tree/master/docs/04-JS.md）

const axios = require("axios");
const corpid = "这里要改";
const corpsecret = "这里要改";

  // 这里过滤不通知的title关键字
var $sz = /^((?!stopped|start|deleted|更新订阅|本次阅读完成).)*$/;

if((typeof $title$ !== "undefined") &&($sz.test($title$))){
  console.log('脚本获取到的通知内容:', $title$, $body$, $url$)
  mynotify1($title$, $body$, $url$)
  // 简单过滤
  if (/重要/.test($title$)) {
    // 使用 $enable$ 强制发送通知 
    $feed.bark('$enable$【重要通知】 ' + $title$, $body$, $url$)
  } else if (/userid/.test($title$)) {
    $feed.cust('$enable$特别的通知给特别的你', $title$ + $body$, $url$)
  } else if (/测试/.test($title$)) {
    $message.success(`一条网页消息 -来自通知触发的 JS\n【标题】 ${$title$} 【内容】 ${$body$}\n${$url$}`, 0)
  }

  if (/elecV2P/.test($body$)) {
    // 对通知内容进行修改
    $body$ = $body$.replace('elecV2P', 'https://github.com/elecV2/elecV2P')
    // 然后通过自定义通知发送
    mynotify1($title$, $body$, $url$)
  }
} else {
  console.log('没有 $title$', '该 JS 应该由通知自动触发执行')
}


function mynotify1(title, body, url) {
     return new Promise(async (resolve) => {
        try {
            if (corpid && corpsecret) {
                let gurl = `https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=${corpid}&corpsecret=${corpsecret}`
                let res = await axios.get(gurl)
                access_token = res.data.access_token
                let turl = `https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${access_token}`
                let text = {
                    "touser": "@all",
                    "msgtype": "text",
                    "agentid": 1000002,
                    "text": {
                        "content": `【elecv2p通知】${title}\n\n${body}`
                    },
                    "safe": 0
                }
      
       let data =text
                let tres = await axios.post(turl,data)
                if (tres.data.errcode == 0) {
                    console.log("企业微信:发送成功");
                } else {
                    console.log("企业微信:发送失败");
                    console.log(tres.data.errmsg);
                }
            } else {
                console.log("企业微信:你还没有填写corpsecret和corpid呢，推送个锤子🔨");
            }
        } catch (err) {
            console.log("企业微信：发送接口调用失败");
            console.log(err);
        }
        resolve();
    });
}
```

# template of notify.js

``` js
if (typeof $title$ !== "undefined") {
    botNotify($title$, $body$, $url$)
}
```
or
``` js
if (typeof $title$ !== "undefined") {
    botNotify1($title$, $body$, $url$)
    botNotify2($title$, $body$, $url$)
}
```
and
``` js
function botNotify(title, body, url) {
if (body=== "undefined"){body=""}
if (url==="undefined"){url=""}
  let req = {
      url: 'https://api.telegram.org/botxxxxxxxxxx/',
      headers: {
        'Content-Type': 'application/json; charset=UTF-8'
      },
      method: 'post',
      data: {
        "method": "sendMessage",
        "chat_id": 'xxxxxxxxxx',
        "text": `${title}\n${body}\n${url}`
      }
    }
  $axios(req).then(res=>{
    console.log('mynotify1 通知结果', res.data)
  }).catch(e=>{
    console.error('mynotify1 通知失败', e.message)
  })
}

```
> 参考：https://github.com/elecV2/elecV2P/blob/master/script/JSFile/notify.js

# elecV2P-dei 官方文档

> https://github.com/elecV2/elecV2P-dei/blob/master/docs/07-feed%26notify.md#%E9%80%9A%E7%9F%A5%E6%96%B9%E5%BC%8F
