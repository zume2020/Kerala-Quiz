FROM ubuntu
ADD . /opt/
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get -y install curl
RUN apt-get -y install python3 python3-pip build-essential gcc musl-dev postgresql-contrib libpq-dev autoconf libtool pkg-config python-opengl python-pil python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev libssl-dev
RUN pip3 install -r /opt/requirements.txt
WORKDIR /opt/
CMD ["python3", "bot.py"]
