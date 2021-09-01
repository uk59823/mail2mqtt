FROM python:3.8-alpine

ENV TZ=Europe/Berlin
ENV MQTT_BROKER=localhost
ENV MQTT_PORT=1883
ENV MQTT_QOS=2
ENV MQTT_RETAIN=True
ENV MQTT_TOPIC=main_uk/mail
ENV MQTT_USER= 
ENV MQTT_PASSWORD= 
ENV MQTT_CLIENTID=mail_mqtt

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ADD mail2mqtt.py /
ADD ./ini/mail2mqtt.ini /ini/

CMD [ "python", "./mail2mqtt.py" ]
