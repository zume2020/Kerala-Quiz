FROM python:3.8.0
ADD . /opt/
RUN pip install -r /opt/requirements.txt
WORKDIR /opt/
CMD ["python", "bot.py"]
