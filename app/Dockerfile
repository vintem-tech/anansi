FROM python:3.8

ENV PIP_DISABLE_PIP_VERSION_CHECK=on
RUN pip install poetry
WORKDIR /app
COPY poetry.lock pyproject.toml entrypoint.sh /app/
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev -n
COPY . /app
RUN chmod +x entrypoint.sh
CMD ["sh", "entrypoint.sh"]