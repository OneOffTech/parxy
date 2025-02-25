FROM python:3.9.17-slim-bullseye as build-image

WORKDIR /app

# install requirements
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN python -m venv --copies /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.9.17-slim-bullseye AS runtime-image

LABEL maintainer="OneOffTech <info@oneofftech.xyz>" \
  org.label-schema.name="OneOffTech/parxy" \
  org.label-schema.description="Docker image for the Parxy service. A PDF parser gateway." \
  org.label-schema.schema-version="1.0" \
  org.label-schema.vcs-url="https://github.com/OneOffTech/parxy"

RUN apt-get update -yqq && \
    apt-get install -yqq --no-install-recommends tini \
    && apt-get install -y --no-install-recommends libmagic1 \
    && apt-get autoremove -yq --purge \
    && apt-get autoclean -yq \
    && apt-get clean \
    && rm -rf /var/cache/apt/ /var/lib/apt/lists/* /var/log/* /tmp/* /var/tmp/* /usr/share/doc /usr/share/doc-base /usr/share/groff/* /usr/share/info/* /usr/share/linda/* /usr/share/lintian/overrides/* /usr/share/locale/* /usr/share/man/* /usr/share/locale/* /usr/share/gnome/help/*/* /usr/share/doc/kde/HTML/*/* /usr/share/omf/*/*-*.emf

# switch to app workdir
WORKDIR /app

# copy dependency form build-image
COPY --from=build-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"


COPY text_extractor_api/ text_extractor_api/
COPY text_extractor/ text_extractor/
COPY root.py uvicorn.sh ./

RUN chmod +x ./uvicorn.sh

EXPOSE 5000/tcp

ENTRYPOINT ["tini", "--"]

CMD ["/app/uvicorn.sh"]