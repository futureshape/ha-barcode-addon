ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    evtest python3 py3-pip\ 
    py3-sqlalchemy py3-requests \
    py3-beautifulsoup4 py3-flask kbd \
    py3-pillow py3-qrcode py3-cairosvg \
    nodejs npm

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

COPY barcode.py /
COPY make_label.py /
COPY DMMono-Medium.ttf /

COPY webapp/ /webapp/

# pynput isn't packaged in Alpine Linux
# Not worried about  --break-system-packages because we're inside a container
RUN pip3 install --break-system-packages pynput

RUN npm i -g @mmote/niimblue-node

# change to persistent data directory so the cached products database isn't destroyed with upgrades
WORKDIR /data

CMD [ "/run.sh" ]