import imaplib
import email
from email.header import decode_header
import urllib.request
import os
import time
import datetime
import paho.mqtt.client as mqtt


# account credentials
username = os.getenv('MAIL_USER', '')
password = os.getenv('MAIL_PASSWORD', '')
imapserver = os.getenv('MAIL_SERVER', '')
interval = int(os.getenv('MAIL_INTERVAL', '60'))
setseen = eval(os.getenv('MAIL_SEEN', 'True'))
setdelete = eval(os.getenv('MAIL_DELETE', 'False'))

# MQTT-Settings
mqtt_ipaddress = os.getenv('MQTT_BROKER', 'localhost')
mqtt_user = os.getenv('MQTT_USER', '')
mqtt_pass = os.getenv('MQTT_PASSWORD', '')
mqtt_topic = os.getenv('MQTT_TOPIC', 'main_uk/mail')
mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
mqtt_qos = int(os.getenv('MQTT_QOS', '2'))
mqtt_retain = eval(os.getenv('MQTT_RETAIN', 'True'))
mqtt_clientid = os.getenv('MQTT_CLIENTID', 'mail_mqtt')

# Filter
filterSubject = os.getenv('FILTER_SUBJECT', '')
filterFrom = os.getenv('FILTER_FROM', '')


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


def decodeElement(element_list):
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


def main():
    # create an IMAP4 class with SSL, use your email provider's IMAP server

    dt = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    send_mqtt_paho(dt, mqtt_topic + "/update")

    if connect() != True:
        print("[" + dt + "] - No internet connection")
        send_mqtt_paho('408 Request Timeout (Internet connection)',
                       mqtt_topic + "/internet_response")
        return "[" + dt + "] - Exit Connection"
    else:
        send_mqtt_paho('200 OK', mqtt_topic + "/internet_response")

    imap = imaplib.IMAP4_SSL(imapserver)

    try:
        # authenticate
        imap.login(username, password)
    except imap.error as e:
        print("[" + dt + "] - " + "Error: " + str(e))
        send_mqtt_paho(str(e), mqtt_topic + "/error")
        return "[" + dt + "] - Exit imap.login"

    # select a mailbox (in this case, the inbox mailbox)
    # use imap.list() to get the list of mailboxes
    status, messages = imap.select("INBOX")
    status_unseen, messages_unseen = imap.search(None, 'UNSEEN')

    # total number of emails
    messages_total = int(messages[0])

    send_mqtt_paho(interval, mqtt_topic + "/interval")
    send_mqtt_paho(messages_total, mqtt_topic + "/total")
    send_mqtt_paho(len(messages_unseen[0].split()), mqtt_topic + "/unread")

    for i in messages_unseen[0].split():
        # fetch the email message by ID
        res, msg = imap.fetch(i, "BODY.PEEK[]")
        for response in msg:
            if isinstance(response, tuple):

                subject = ""
                From = ""
                mail = ""
                body = None

                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])

                # decode the email subject
                subject_list = decode_header(msg['subject'])
                subject = decodeElement(subject_list)

                # decode email-From sender
                from_list = decode_header(msg.get("From"))
                From = decodeElement(from_list)

                # decode email-Address sender
                mail_list = decode_header(msg.get("Return-Path"))
                mail = decodeElement(mail_list)

                if (subject in filterSubject) or ((filterFrom != '') and (filterFrom in From)):

                    # if the email message is multipart
                    if msg.is_multipart():

                        # iterate over email parts
                        for part in msg.walk():
                            # extract content type of email
                            content_type = part.get_content_type()
                            content_disposition = str(
                                part.get("Content-Disposition"))
                            try:
                                # get the email body
                                if body != None:
                                    body = body + '\n\n' + \
                                        part.get_payload(decode=True).decode()
                                else:
                                    body = part.get_payload(
                                        decode=True).decode()
                            except:
                                pass
                    else:

                        # extract content type of email
                        content_type = msg.get_content_type()
                        # get the email body
                        body = msg.get_payload(decode=True).decode()

                    if setseen == True:
                        imap.store(i, '+FLAGS', '\Seen')
                    if setdelete == True:
                        imap.store(mail, "+FLAGS", "\Deleted")

                    print(dt + " - gefilterte Mail von '" + From + "'")
                    send_mqtt_paho(From, mqtt_topic + "/from")
                    send_mqtt_paho(mail, mqtt_topic + "/mail")
                    send_mqtt_paho(subject, mqtt_topic + "/subject")
                    send_mqtt_paho(body, mqtt_topic + "/body")

    # close the connection and logout
    imap.close()
    imap.logout()
    return "[" + dt + "] - Search ended"


if __name__ == '__main__':
    print("mail2mqtt started")
    while 1:

        dtStart = datetime.datetime.now()
        r = main()
        print(r)
        dtEnd = datetime.datetime.now()
        sleeptime = interval - (dtEnd - dtStart).total_seconds()
        if sleeptime < 0:
            sleeptime = interval
        time.sleep(sleeptime)
