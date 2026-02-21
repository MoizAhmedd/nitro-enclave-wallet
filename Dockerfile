FROM amazonlinux:2023

RUN yum install -y python3 python3-pip
RUN pip3 install cryptography pycryptodome

COPY app.py /app.py

CMD ["python3", "/app.py"]
