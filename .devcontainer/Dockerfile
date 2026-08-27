FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

WORKDIR /workspaces/eduanimate
COPY requirements.txt /tmp/eduanimate-requirements.txt
RUN pip install --no-cache-dir -r /tmp/eduanimate-requirements.txt
