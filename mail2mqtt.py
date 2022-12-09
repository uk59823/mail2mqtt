import imaplib
import smtplib
import email
import configparser
import json
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.message import MIMEMessage
import urllib.request
import os
import time
import datetime
import paho.mqtt.client as mqtt
import cgi
import sys

broker = 'localhost'
inifile = 'ini/mail2mqtt.ini'

# MQTT-Settings
mqtt_ipaddress = os.getenv('MQTT_BROKER', broker)
mqtt_user = os.getenv('MQTT_USER', '')
mqtt_pass = os.getenv('MQTT_PASSWORD', '')
mqtt_topic = os.getenv('MQTT_TOPIC', 'main_uk/mail')
mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
mqtt_qos = int(os.getenv('MQTT_QOS', '2'))
mqtt_retain = eval(os.getenv('MQTT_RETAIN', 'True'))
mqtt_clientid = os.getenv('MQTT_CLIENTID', 'mail_mqtt')

postboxes = []
filters = []


def readIniValues():
    # read settings from mail2mqtt.ini
    ApplicationDir = os.path.dirname(os.path.abspath(__file__))
    ReadSettings = os.path.join(ApplicationDir, inifile)
    Settings = configparser.ConfigParser()
    Settings.read(ReadSettings, 'UTF-8')
    # existing postboxes
    global interval, setseen
    try:
        interval = int(Settings.get("General", "interval"))
    except:
        interval = 5
    try:
        setseen = eval(Settings.get("General", "do_seen"))
    except:
        setseen = True

    # existing postboxes
    global postboxes
    pboxes = Settings.items("POSTBOX")

    for id in pboxes:
        postbox = {}
        postbox['postboxname'] = str(id[1])
        postbox['username'] = Settings.get(str(id[1]), "username")
        postbox['password'] = Settings.get(str(id[1]), "password")
        postbox['imapserver'] = Settings.get(str(id[1]), "imapserver")
        try:
            postbox['smtpserver'] = Settings.get(str(id[1]), "smtpserver")
        except:
            postbox['smtpserver'] = ""
        try:
            postbox['smtpport'] = int(Settings.get(str(id[1]), "smtpport"))
        except:
            postbox['smtpport'] = int(25)

        postboxes.append(postbox)

    # existing filters
    global filters
    filter = Settings.items("FILTER")
    for id in filter:
        idfilter = {}
        idfilter['filtername'] = str(id[1])
        try:
            idfilter['filterPostbox'] = Settings.get(
                str(id[1]), "filter_postbox")
        except:
            idfilter['filterPostbox'] = ''
        try:
            idfilter['filterSubject'] = Settings.get(
                str(id[1]), "filter_subject")
        except:
            idfilter['filterSubject'] = ''
        try:
            idfilter['filterFrom'] = Settings.get(str(id[1]), "filter_from")
        except:
            idfilter['filterFrom'] = ''
        try:
            idfilter['moveTo'] = Settings.get(str(id[1]), "do_moveTo")
        except:
            idfilter['moveTo'] = ''
        if idfilter['moveTo'] == '':
            try:
                if eval(Settings.get(str(id[1]), "do_delete")) == True:
                    idfilter['moveTo'] = "INBOX.Trash"
            except:
                idfilter['moveTo'] = ''
        try:
            idfilter['sendTo'] = Settings.get(
                str(id[1]), "do_sendTo")
        except:
            idfilter['sendTo'] = ''
        try:
            idfilter['forward'] = eval(Settings.get(
                str(id[1]), "do_forward"))
        except:
            idfilter['forward'] = True
        filters.append(idfilter)


def checkFilter(pbox, subject, From):
    res = {}
    filter = []
    for filter in filters:
        r1 = False
        r2 = False
        r3 = False
        if (filter['filterPostbox'] != ''):
            for s in filter['filterPostbox'].lower().split('|'):
                if s in pbox.lower():
                    r1 = True
        else:
            r1 = True
        if (filter['filterSubject'] != ''):
            for s in filter['filterSubject'].lower().split('|'):
                if (s in subject.lower()):
                    r2 = True
        else:
            r2 = True
        if (filter['filterFrom'] != ''):
            for s in filter['filterFrom'].lower().split('|'):
                if s in From.lower():
                    r3 = True
        else:
            r3 = True

        if (r1 and r2 and r3):
            res = filter
    return res


def forwardPreText(msg):
    cRow = '\r\n<TR><TH valign="BASELINE" nowrap="nowrap" align="RIGHT">{name}</TH><TD>{value}</TD></TR>'
    info = {}
    if msg['subject'] != None:
        tRow = cRow
        info['subject'] = tRow.replace("{name}", "Betreff:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['subject']))))
    if msg['Date'] != None:
        tRow = cRow
        info['date'] = tRow.replace("{name}", "Datum:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['Date']))))
    if msg['From'] != None:
        tRow = cRow
        info['from'] = tRow.replace("{name}", "Von:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['From']))))

    if msg['to'] != None:
        tRow = cRow
        info['to'] = tRow.replace("{name}", "An:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['to']))))
    if msg['Reply-To'] == None:
        info['reply-to'] = ""
    else:
        tRow = cRow
        info['reply-to'] = tRow.replace("{name}", "Antwort an:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['Reply-To']))))
    if msg['Organization'] == None:
        info['organization'] = ""
    else:
        tRow = cRow
        info['organization'] = tRow.replace("{name}", "Organisation:").replace(
            "{value}", cgi.html.escape(decodeElement(decode_header(msg['Organization']))))

    preText = '----- Weitergeleitete Nachricht -----' + '\r\n<TABLE>' + \
        info['subject'] + info['date'] + info['from'] + info['reply-to'] + \
        info['organization'] + info['to'] + '\r\n</TABLE>'

    return preText


def connect():
    host = 'http://google.com'
    try:
        urllib.request.urlopen(host)  # Python 3.x
        return True
    except:
        return False


def on_connect(client, userdata, flags, rc):
    # Connect to MQTT-Broker
    if rc != 0:
        print("Connection Error to broker using Paho with result code " + str(rc))


def send_mqtt_paho(message, topic):
    count = 0
    while count < 5:
        try:
            # send MQTT message
            mqttclient = mqtt.Client(mqtt_clientid)
            mqttclient.on_connect = on_connect
            if mqtt_user != "":
                mqttclient.username_pw_set(mqtt_user, mqtt_pass)
            mqttclient.connect(mqtt_ipaddress, mqtt_port, 60)
            mqttclient.loop_start()
            mqttpub = mqttclient.publish(
                topic, payload=message, qos=mqtt_qos, retain=mqtt_retain)
            mqttclient.loop_stop()
            mqttclient.disconnect()
            return True
        except:
            count += 1
            time.sleep(1)
    print("MQTT-Broker not reachable!")
    return False


def decodeElement(element_list):
    try:
        sub_list = []
        for element in element_list:
            if element[1]:
                element = (element[0].decode(element[1]))
            elif type(element[0]) == bytes:
                element = element[0].decode('utf-8')
            else:
                element = element[0]
            sub_list.append(element)

        element = ''.join(sub_list)
        return element
    except:
        print('Error in decodeElement: ' + element_list)


def formatISO8601(inDate):
    month = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
             'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    inDate = inDate.split(', ')[1]
    d = '{:02d}'.format(int(inDate.split(' ')[0]))
    M = '{:02d}'.format(month.index(inDate.split(' ')[1]) + 1)
    y = inDate.split(' ')[2]
    t = inDate.split(' ')[3]
    if len(inDate.split(' ')[4]) == 5:
        z = inDate.split(' ')[4][:3] + ':' + inDate.split(' ')[4][3:]
    else:
        z = '+' + inDate.split(' ')[4][:2] + ':' + inDate.split(' ')[4][2:]
    ISO8601 = y + '-' + M + '-' + d + 'T' + t + z
    return ISO8601


def main():
    dt = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    if connect() != True:
        print("[" + dt + "] - No internet connection")
        if send_mqtt_paho('408 Request Timeout (Internet connection)',
                          mqtt_topic + "/internet_response") == False:
            return
        return "[" + dt + "] - Exit Connection"
    else:
        if send_mqtt_paho('200 OK', mqtt_topic + "/internet_response") == False:
            return

    for postbox in postboxes:

        sum = []

        subtopic = "/" + postbox['postboxname']
        imap = imaplib.IMAP4_SSL(postbox['imapserver'])

        try:
            # authenticate
            imap.login(postbox['username'], postbox['password'])
        except imap.error as e:
            print("[" + dt + "] - " + postbox['postboxname'] +
                  " - Error: " + str(e))
            if send_mqtt_paho(str(e), mqtt_topic + subtopic + "/error") == False:
                return
            return "[" + dt + "] - Exit imap.login"

        # select a mailbox (in this case, the inbox mailbox)
        status, messages = imap.select("INBOX")
        status_unseen, messages_unseen = imap.search(None, 'UNSEEN')

        # total number of emails
        messages_total = int(messages[0])

        if send_mqtt_paho(interval, mqtt_topic + subtopic + "/interval") == False:
            return
        if send_mqtt_paho(messages_total, mqtt_topic + subtopic + "/total") == False:
            return
        if send_mqtt_paho(
                len(messages_unseen[0].split()), mqtt_topic + subtopic + "/unread") == False:
            return
        if send_mqtt_paho(dt, mqtt_topic + "/update") == False:
            return

        for i in messages_unseen[0].split():

            try:
                #                res, msg = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT FLAGS)])")
                res, msg = imap.fetch(
                    i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT)])")
            except imap.error as e:
                print("[" + dt + "] - " + postbox['postboxname'] +
                      " - Error Fetch (BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT)]): " + str(e))
                if send_mqtt_paho(postbox['postboxname'] + " - Error Fetch (BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT)]): " + str(e), mqtt_topic + subtopic + "/error") == False:
                    return
                continue

            for response in msg:
                if isinstance(response, tuple):

                    subject = ""
                    From = ""
                    mail = ""
                    sent = ""
                    body = None
                    toFolder = ""

                    msg = email.message_from_string(
                        response[1].decode('utf-8'))

                    # decode the email subject
                    subject_list = decode_header(msg['subject'])
                    subject = decodeElement(subject_list)

                    # decode email-From sender
                    from_list = decode_header(msg['from'])
                    From = decodeElement(from_list)

                    # decode email-Address sender
                    try:
                        mail_list = decode_header(msg['to'])
                        mail = decodeElement(mail_list)
                    except:
                        mail = "<NONE>"
                        print("[" + dt + "] - " + postbox['postboxname'] + " - Fehler, kein To-Attribut im Message von: '" +
                              From + "' -> '" + subject + "'")

                    # decode the email send date
                    try:
                        sent = decode_header(msg['Date'])[0][0]
                    except:
                        sent = ""
                        print("[" + dt + "] - " + postbox['postboxname'] + " - Fehler, kein Date-Attribut im Message von: '" +
                              From + "' -> '" + subject + "'")

                    filter = checkFilter(
                        postbox['postboxname'], subject, From)

                    if filter != {}:
                        try:
                            # fetch the email message by ID
                            res, msg = imap.fetch(
                                i, "(BODY.PEEK[])")
                        except imap.error as e:
                            print("[" + dt + "] - " + postbox['postboxname'] +
                                  " - Error Fetch (BODY.PEEK[]): " + str(e))
                            if send_mqtt_paho(postbox['postboxname'] + " - Error Fetch (BODY.PEEK[]): " + str(e), mqtt_topic + subtopic + "/error") == False:
                                return
                            continue

                        for response in msg:
                            if isinstance(response, tuple):

                                body = None
                                toFolder = ""

                                # parse a bytes email into a message object
                                msg = email.message_from_bytes(response[1])

                                # decode the email receive date
                                received = decode_header(msg['Received'])[
                                    0][0].split('; ')[1]

                                # if the email message is multipart
                                if msg.is_multipart():

                                    # iterate over email parts
                                    for part in msg.walk():
                                        try:
                                            # get the email body
                                            if body != None:
                                                body = body + '\n\n' + \
                                                    part.get_payload(
                                                        decode=True).decode()
                                            else:
                                                body = part.get_payload(
                                                    decode=True).decode()
                                        except:
                                            pass
                                else:
                                    body = msg.get_payload(
                                        decode=True).decode()

                                if setseen == True:
                                    imap.store(i, '+FLAGS', '\Seen')

                                if filter['sendTo'] != "":
                                    to_addr = filter['sendTo']

                                    if filter['forward'] != True:
                                        # create a Message instance from the email data
                                        msgTransfer = msg
                                        # replace headers (could do other processing here)
                                        msgTransfer.replace_header(
                                            "From", postbox['username'])
                                        msgTransfer.replace_header(
                                            "To", to_addr)
                                    else:

                                        # create a Message instance from the email data
                                        msgTransfer = MIMEMultipart(
                                            "mixed")
                                        msgTransfer.add_header(
                                            "From", postbox['username'])
                                        msgTransfer.add_header(
                                            "To", to_addr)
                                        msgTransfer.add_header(
                                            "subject", "WG: " + subject)

                                        # Turn these into plain/html MIMEText objects
                                        part1 = MIMEText(
                                            forwardPreText(msg), "html", "utf-8")
                                        part2 = MIMEMessage(msg)

                                        # Add HTML/plain-text parts to MIMEMultipart message
                                        # The email client will try to render the last part first
                                        msgTransfer.attach(part1)
                                        msgTransfer.attach(part2)

                                    # open authenticated SMTP connection and send message with
                                    # specified envelope from and to addresses
                                    smtp = smtplib.SMTP(
                                        postbox['smtpserver'], postbox['smtpport'])

                                    smtp.starttls()
                                    smtp.login(
                                        postbox['username'], postbox['password'])

                                    smtp.send_message(
                                        msgTransfer, postbox['username'], to_addr)

                                    smtp.quit()

                                if filter['moveTo'] != "":
                                    apply_msg = imap.copy(i, filter['moveTo'])
                                    if apply_msg[0] == 'OK':
                                        imap.store(i, '+FLAGS', '\Deleted')
#                                        imap.expunge()

                                paho = {}
                                paho['filter'] = filter['filtername']
                                paho['from'] = From
                                paho['mail'] = mail
                                paho['subject'] = subject
                                paho['body'] = body
                                paho['sent'] = formatISO8601(sent)
                                paho['received'] = formatISO8601(received)

                                sum.append(paho)

        imap.expunge()

        count = len(sum)
        if sum != []:
            print("[" + dt + "] - gefilterte Mail von '" +
                  postbox['postboxname'] + "': " + str(count))
        if send_mqtt_paho(count, mqtt_topic + subtopic + "/count") == False:
            return
        if send_mqtt_paho(json.dumps(sum), mqtt_topic + subtopic + "/found") == False:
            return

        # close the connection and logout
        imap.close()
        imap.logout()
        send_mqtt_paho('', mqtt_topic + subtopic + "/error")

    if send_mqtt_paho(dt, mqtt_topic + "/update") == False:
        return
    return "[" + dt + "] - Search ended"


if __name__ == '__main__':
    print("mail2mqtt started")
    readIniValues()

    while 1:
        dtStart = datetime.datetime.now()
        r = main()
        if r != None:
            print(r)
        dtEnd = datetime.datetime.now()
        sleeptime = (60 * interval) - (dtEnd - dtStart).total_seconds()
        if sleeptime < 0:
            sleeptime = 60 * interval
        time.sleep(sleeptime)
