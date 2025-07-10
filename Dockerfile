FROM python:3.12
ENV PYTHONUNBUFFERED=1
WORKDIR /src

COPY /src/requirements.txt .
RUN pip --no-cache-dir install -r requirements.txt
ENTRYPOINT ["python",  "main.py"]
