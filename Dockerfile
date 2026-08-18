FROM ghcr.io/home-assistant/base:latest

# Install requirements for add-on
RUN \
  apk add --no-cache \
    evtest python3 py3-pip git \
    py3-sqlalchemy py3-requests \
    py3-beautifulsoup4 py3-flask kbd \
    py3-pillow py3-qrcode py3-cairosvg 

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

COPY barcode.py /
COPY printer_adapter.py /
COPY make_label.py /
COPY DMMono-Medium.ttf /

COPY webapp/ /webapp/

ENV PYTHONPATH=/

# pynput isn't packaged in Alpine Linux
# Install runtime dependencies not available in apk and the Qutie BLE printer library.
RUN pip3 install --break-system-packages pynput 'git+https://github.com/futureshape/qutie-printer.git'

# change to persistent data directory so the cached products database isn't destroyed with upgrades
WORKDIR /data

CMD [ "/run.sh" ]