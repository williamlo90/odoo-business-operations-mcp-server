FROM odoo:19.0@sha256:dd9013e669caaa23d26765dc55814655eaeecca7cfc2c265dbabae913bce22fd
COPY addons /opt/ops-addons
COPY runtime.py seed.py /opt/ops/
ENTRYPOINT ["python3", "/opt/ops/runtime.py"]
CMD ["serve"]
