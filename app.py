#coding=utf-8
from flask import Flask
from flask import request
from WXBizDataCrypt import WXBizDataCrypt
from flask import jsonify
import redis
import requests
import logging
import json
import uuid
app = Flask(__name__)
appId='wx3367d21c68cea6a0'
secret='6b53aedd3052e2651cff4d006d26e1ef'
logPath='/root/jys/flask.log'
redisobj = redis.StrictRedis(host='172.27.0.2', port='6379', db=0, password='jys1006@txy')

@app.route('/')
def hello_world():
    logging.debug('test')
    redisobj.set('2222', 'jiaoyishuo houtai!')
    logging.debug('test222')
    return 'jiaoyishuo houtai!'

@app.route('/login', methods=['POST'])
def login():
    #code换session
    res = json.loads(request.data)
    session =jscode2session(res['code'])
    logging.debug(session)
    dic_session =json.loads(session)

    #保存用户id、openid，和session
    user_uuid = str(uuid.uuid4())  # 暴露给小程序端的用户标示
    redisobj.set('u:'+user_uuid, session)
    logging.debug('key:'+user_uuid+'value:'+str(session))

    return user_uuid

@app.route('/viewList', methods=['POST'])
def viewList():

    #保存用户id、openid，和session
    viewLists={'articles':[
        {'title':'贵州茅台','type':'买入预警','readNum':4836,'image':'https://pic2.zhimg.com//v2-62b554158b8e8f4453486e9cca52ca49.jpg'},
        {'title': '小米集团', 'type': '实时买入信号', 'readNum': 9765,'image': 'https://pic2.zhimg.com//v2-62b554158b8e8f4453486e9cca52ca49.jpg'}]}

    return jsonify(viewLists)
@app.route('/tip', methods=['POST'])
def gettip():
    #code换session
    res = json.loads(request.data)
    logging.debug('============u:'+res['uid'])
    uinfo_s=redisobj.get('u:' + res['uid'])
    uinfo=json.loads(uinfo_s)

    wxRetTmp =sendTipMsg(uinfo['openid'],res['formId'] )

    return 'success'

@app.route('/formId', methods=['POST'])
def formId():
    #code换session
    res = json.loads(request.data)
    logging.debug('============u:'+res['uid'])

    redisobj.lpush('u:' + res['uid'] + ':formId', res['formId'])

    return 'success'

#获取手机号
@app.route('/phone', methods=['POST'])
def setphone():
    res = json.loads(request.data)
    logging.debug(res)
    logging.debug('============u:'+res['uid'])
    uinfo_s=redisobj.get('u:' + res['uid'])
    uinfo=json.loads(uinfo_s)
    logging.debug(uinfo)

    pc = WXBizDataCrypt(appId, uinfo['session_key'])

    phoneinfo=pc.decrypt(res['encryptedData'], res['iv'])
    logging.debug(phoneinfo)
    logging.debug(phoneinfo['purePhoneNumber'])

    redisobj.set('ph:' + phoneinfo['purePhoneNumber']+':uid',res['uid'])

    return 'success'

#发送消息
@app.route('/msg', methods=['POST'])
def sendmsg():
    res = json.loads(request.data)
    uid=redisobj.get('ph:' +res['phone']+':uid').decode()
    logging.debug('============111:')
    logging.debug(uid)
    logging.debug('============222:')
    uinfo_s = redisobj.get('u:' + uid).decode()
    logging.debug(uinfo_s)
    logging.debug('============333:')
    uinfo = json.loads(uinfo_s)
    formId=redisobj.rpop('u:' + uid + ':formId').decode()
    logging.debug(formId)
    logging.debug('============444:')

    sendMsgRemote(uinfo['openid'], formId,res['data'])
    logging.debug('============msg:')


    return 'success'


#code换session
def jscode2session(code):
    url = ('https://api.weixin.qq.com/sns/jscode2session?'+ 'appid={}&secret={}&js_code={}&grant_type=authorization_code').format(appId ,secret, code)
    r = requests.get(url)
    return r.content.decode()

#发送模板消息
def sendTipMsg(openid,form_id):
    payload = { 'grant_type': 'client_credential', 'appid': appId, 'secret':secret }
    requests.packages.urllib3.disable_warnings()
    req = requests.get('https://api.weixin.qq.com/cgi-bin/token', params=payload, timeout=3, verify=False)
    access_token = req.json().get('access_token')

    data = {
        "touser": openid,
        "template_id": 'qF-C0-Z1AHWHCElmKPqekJj2OlY29spIcehbWW97I2c',
        "page": 'pages/index/index',
        "form_id": form_id,
        "data": {
            'keyword1': { 'value': '[沪深300]前高点[3506.24][7月16],[3520]买入,上涨[0.8%]，ATR[65.0]止损金额[3.9万]左宽[12]天,右宽[5]天收盘[3492.89]期指[3458.6]价差[-34.0' },
            'keyword2': { 'value': '沪深300' }
        },
        "emphasis_keyword": ''
    }
    push_url = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token={}'.format(access_token)
    r =requests.post(push_url, json=data, timeout=3, verify=False)
    return r.content.decode()

#发送模板消息
def sendMsgRemote(openid,form_id,senddata):
    payload = { 'grant_type': 'client_credential', 'appid': appId, 'secret':secret }
    requests.packages.urllib3.disable_warnings()
    req = requests.get('https://api.weixin.qq.com/cgi-bin/token', params=payload, timeout=3, verify=False)
    access_token = req.json().get('access_token')

    data = {
        "touser": openid,
        "template_id": 'qF-C0-Z1AHWHCElmKPqekJj2OlY29spIcehbWW97I2c',
        "page": 'pages/index/index',
        "form_id": form_id,
        "data": {
            'keyword1': { 'value':senddata },
            'keyword2': { 'value': '沪深300' }
        },
        "emphasis_keyword": ''
    }
    push_url = 'https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token={}'.format(access_token)
    r =requests.post(push_url, json=data, timeout=3, verify=False)
    return r.content.decode()

if __name__ == '__main__':
    app.run()

if __name__ != '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', filename='/root/jys/flask.log', filemode='w')
