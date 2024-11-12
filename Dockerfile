FROM python:alpine as base

FROM base as build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base
COPY --from=build /install /usr/local
ADD *.py ./
ADD gatus_config.yml ./
ENTRYPOINT ["python3"]
CMD ["-u","app.py"]