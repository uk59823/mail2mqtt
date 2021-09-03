# mail2mqtt
Check the mailbox according to criteria and send to MQTT

## functionality
The script searches the unread messages in the INBOX of one or meore mailboxes defined in an ini-file. In intervals according to defined criteria the script sends the messages found via MQTT.
The script is intended for use in a Docker container, so that the Docker environment variables are used to control the mqtt-part, the part to control the mailboxes are defined in the ini-file also the defined filter.

The docker container you can find [here](https://hub.docker.com/repository/docker/ukrae/mail2mqtt "mail2mqtt on docker").

## docker environment variables
* MQTT_BROKER: IP-Address (or FQN) of your MQTT Broker (*default: 'localhost'*)
* MQTT_PORT: Port for your Broker (*default: 1883*)
* MQTT_QOS: QOS-level for the message (*default: 2*)
* MQTT_RETAIN: True/False for telling the MQTT-server to retain the message or discard it (*default: True*)
* MQTT_TOPIC: MQTT topic for the JSON (*default: 'main_uk/mail'*)
* MQTT_USER: Username for the broker (*leave empty for anonymous call*)
* MQTT_PASSWORD: Password for the broker (*leave empty for anonymous call*)
* MQTT_CLIENTID: ClientID for the broker to avoid parallel connections (*default: 'mail_mqtt'*)

## mail2mqtt.ini
The file is stored in the subdirectory 'ini' 
```
[General]
interval: 5
todo_seen: True
```
* interval: defines the interval in minutes between the search (*default: 5*)
* todo_seen: switch, boolean (if True) to set the message 'SEEN' after filtering (*default: True*)
```
[POSTBOX]
1: Postbox_A
2: Postbox_B
```
* section to define the postboxes, here are two mailbox defined
```
[Postbox_A]
username: 
password: 
server: 
```
* one section for each mailbox
```
[FILTER]
1: MissedCall
2: INFO_Paypal
```
* section to define the filters, here defined two filter see below
```
[MissedCall]
filter_subject: Ein verpasster Anruf liegt vor
todo_delete: False

[INFO_Paypal]
filter_postbox: Postbox_B
filter_from: service@paypal.de|paypal@mail.paypal.de
todo_delete: False
```
* you can combine three parts *'filter_postbox'*, *'filter_subject'* and *'filter_from'*. If defined the parts AND linked. it it possible to give more than one value per part if you split it with an pipi '|'
* filter_postbox: allowed are values defined in section 'POSTBOX'
* filter_subject: the subject of the message
* filter_from: one or more email-address
* todo_delete: switch, boolean (if True) to delete the message after filtering (*default: False*)

## output on your mqtt broker
    MQTT_TOPIC/update
    MQTT_TOPIC/internet_response
    MQTT_TOPIC/subtopic/total
    MQTT_TOPIC/subtopic/unread
    MQTT_TOPIC/subtopic/count
    MQTT_TOPIC/subtopic/found
* **MQTT_TOPIC** is defined in the docker environment, **subtopic** is the name of the postbox defined in the inifile.
* ../total: total number of messages in the postbox
* ../unread: number of unread messages 
* ../count: number of messages that were filtered 
* ../found: list of filtered messages as JSON dump (including: filtername, from, mail, subject, body, received, sent)
 
(all dates ISO8601 formatted)
