FROM python:3.11

ENV name "GPIO"
ENV port 8642
ENV gpio ""

RUN cd /etc
RUN mkdir app
WORKDIR /etc/app
ADD *.py /etc/app/
ADD requirements.txt /etc/app/.
RUN pip install -r requirements.txt


CMD python /etc/app/run_server.py $name $port $gpio
RUN /bin/bash



