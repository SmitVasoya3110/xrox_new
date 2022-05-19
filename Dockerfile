FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY ./requirements.txt /code/
RUN apt update
RUN apt -y upgrade
RUN apt install -y libreoffice
RUN apt-get install libmagic1
RUN pip3 install -r req.txt
COPY . /code/

EXPOSE 8000
CMD ["python", "app.py"]
