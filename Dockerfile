FROM quay.fortaleza.ce.gov.br/citinova/python:3.12-rhel9 as builder

WORKDIR /www

COPY requirements.txt .

# Cria um virtualenv
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

# Adiciona o app no mesmo diretório do venv
ENV PATH="/opt/venv/bin:$PATH"

FROM quay.fortaleza.ce.gov.br/citinova/python:3.12-rhel9

RUN groupadd -r citinova && useradd -r -m -g citinova citinova

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /www /www

# Garante que as permissões estão corretas
RUN chown -R citinova:citinova /www

ENV PATH="/opt/venv/bin:$PATH"
RUN rm -rf /www/requirements.txt
WORKDIR /www
USER citinova

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "1000", "--log-level", "debug", "run:app"]
