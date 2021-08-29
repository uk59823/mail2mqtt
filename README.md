# mail2mqtt
Check the mailbox according to criteria and send to MQTT

# functionality
The script searches the unread messages in the INBOX at intervals according to defined criteria and sends the messages found via MQTT.
The script is intended for use in a Docker container, so that the Docker environment variables are used to control the script https://hub.docker.com/repository/docker/ukrae/mail2mqtt

## environment variables
* MQTT_BROKER: IP-Address (or FQN) of your MQTT Broker (*default: 'localhost'*)
* MQTT_PORT: Port for your Broker (*default: 1883*)
* MQTT_QOS: QOS-level for the message (*default: 2*)
* MQTT_RETAIN: True/False for telling the MQTT-server to retain the message or discard it (*default: True*)
* MQTT_TOPIC: MQTT topic for the JSON (*default: 'main_uk/mail'*)
* MQTT_USER: Username for the broker (*leave empty for anonymous call*)
* MQTT_PASSWORD: Password for the broker (*leave empty for anonymous call*)
* MQTT_CLIENTID: ClientID for the broker to avoid parallel connections (*default: 'mail_mqtt'*)

* MAIL_USER: mail-address of the email account
* MAIL_PASSWORD: password of the email account 
* MAIL_SERVER: address of the IMAP-Server
* MAIL_SEEN: Flag whether a found mail is set to 'seen' (*default: True*)
* MAIL_DELETE: Flag whether a found mail should be 'deleted' (*default: False*)
* MAIL_INTERVAL: Interval (in seconds) in which the account is checked (*default: 60*)

* FILTER_SUBJECT: Subject filter (or parts of it)
* FILTER_FROM: Filter of sender addresses
