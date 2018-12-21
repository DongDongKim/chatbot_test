import json
import os
import re
import urllib.request
from random import *

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template

app = Flask(__name__)

slack_token = ""
slack_client_id = ""
slack_client_secret = ""
slack_verification = ""
sc = SlackClient(slack_token)

words = []
cont = []
dic = {}
latest = ''


def first():
    # URL 데이터를 가져올 사이트 url 입력
    # url = "http://terms.tta.or.kr/dictionary/dictionarySisaList.do"
    prot = "https://terms.naver.com/list.nhn?cid=59277&categoryId=59283&page="
    home = "https://terms.naver.com"
    # URL 주소에 있는 HTML 코드를 soup에 저장합니다.
    global words
    words = []
    global dic
    dic = {}
    global cont
    cont = []

    for n in range(1, 10):
        url = prot + str(n)
        url.replace('\n', '')
        soup = BeautifulSoup(urllib.request.urlopen(url).read(), "html.parser")
        for i in soup.find_all("ul", class_="content_list"):
            for j in i.find_all("strong", class_="title"):
                words.append("*"+j.find("a").get_text()+"*")
                tmp = j.find("a").get_text().split('[')
                tmp2 = tmp[0]
                tmp2 = tmp2[:-1]
                tmp2 = tmp2.replace(' ', '')
                cont.append(tmp2)
                (key, value) = "*"+j.find("a").get_text()+"*", (home + j.find("a")["href"])
                dic[key] = value

def setLatest(url):
    global latest
    latest = url

def getLatest():
    global latest
    return latest

# 크롤링 함수 구현하기
def _search_word(text):
    l = text.split()
    que = u''.join(l[1:])
    st = ''
    for s in que:
        st += s +''
    answer = []
    exp =''
    atth = [{}]
    imgurl = ''

    if '퇴근' in st:
        return '집에 갑니다ㅠㅠㅠㅠㅠㅠ', atth
    elif '자세히' in st:
        soup2 = BeautifulSoup(urllib.request.urlopen(getLatest()).read(), "html.parser")
        exp = soup2.find_all("p", class_="txt")
        string =''
        for i in exp:
            string += (i.get_text())
        return string, atth
    elif '모두' in st:
        string ="저는 "
        for word in cont:
            string +=word+", "

        string += "등을 알아요~"
        return string, atth
    elif '추천' in st:
        random = randrange(0, len(words))
        url2 = dic[words[random]]
        exp = "추천 단어는 "+words[random] + ' 입니다\n'
        soup2 = BeautifulSoup(urllib.request.urlopen(url2).read(), "html.parser")
        exp += soup2.find("dl", class_="summary_area").get_text().replace('요약', '').strip() + '\n'
        exp += """자세히 알고싶다면 "자세히"를 입력해주세요 """ + '\n'
        imgurl = soup2.find("div", class_="thmb c").find("img")["origin_src"]
        atth = [{"title":"How does this look?","image_url": imgurl}]
        print(imgurl)
        setLatest(url2)
        return exp, atth

    elif "안녕" in st:
        say = """안녕하세요. mydic입니다. 
제가 알고있는 내용이 궁금하시다면 "모두"를 입력해 주세요.
지식 추천을 받고 싶으시면 "추천"을 입력해 주세요."""
        atth = [
            {

                "fallback": "You are unable to choose a game",
                "callback_id": "button",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "select",
                        "text": "모두",
                        "type": "button",
                        "value": "all"
                    },
                    {
                        "name": "select",
                        "text": "추천",
                        "type": "button",
                        "value": "reco"
                    },
                    {
                        "name": "select",
                        "text": "퇴근",
                        "type": "button",
                        "style": "danger",
                        "value": "end"
                    }
                ]
            },



        ]
        return say, atth
    print(st)
    for i in range(len(cont)):
        if cont[i] in st:
            answer.append(words[i])
            break
        if i == (len(cont) - 1) :
            break
        # print(cont[i], st, words[i])


    for a in answer:
        url2 = dic[a]
        exp += a + '\n'
        soup2 = BeautifulSoup(urllib.request.urlopen(url2).read(), "html.parser")
        exp += soup2.find("dl", class_="summary_area").get_text().replace('요약', '').strip() +'\n'
        exp += """자세히 알고싶다면 "자세히"를 입력해주세요 """ + '\n'
        imgurl = soup2.find("div", class_="thmb c").find("img")["origin_src"]

        setLatest(url2)
    if len(answer) == 0:
        return '공부 열심히 할께요ㅠㅠ', atth
    elif len(answer) ==1:
        atth = [{"title": "How does this look?", "image_url": imgurl}]

    return exp, atth


# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    print(slack_event["event"])

    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]

        keywords, attachment = _search_word(text)
        sc.api_call(
            "chat.postMessage",
            channel=channel,
            text=keywords,
            attachments = attachment
        )

        return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    first()
    slack_event = json.loads(request.data)
    print(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":
                                                                 "application/json"
                                                             })

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/button", methods=["GET", "POST"])
def btn_event():
    print(request.form["payload"])
    temp = request.form["payload"]
    temp = json.loads(temp)
    print(type(temp))
    temp2 = temp["actions"]
    value = temp2[0]["value"]
    print(temp2[0]["value"])

    if value=="all":
        string = "저는 "
        for word in cont:
            string += word + ", "

        string += "등을 알아요~"
        return string
    elif value=="reco":
        random = randrange(0, len(words))
        url2 = dic[words[random]]
        exp = "추천 단어는 "+words[random] + ' 입니다\n'
        soup2 = BeautifulSoup(urllib.request.urlopen(url2).read(), "html.parser")
        exp += soup2.find("dl", class_="summary_area").get_text().replace('요약', '').strip() + '\n'
        exp +="""자세히 알고싶다면 "자세히"를 입력해주세요 """+'\n'
        setLatest(url2)
        exp += "\n"+imgurl


    elif value=="end":
        return '집에 갑니다ㅠㅠㅠㅠㅠㅠ'

    return "????"

@app.route("/", methods=["GET"])
def index():

    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
