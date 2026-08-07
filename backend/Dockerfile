# Base on Ubuntu for flexibility
FROM ubuntu:24.04

# Install system deps intelligently (minimal, no recommends)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pyenv
ENV PYENV_ROOT /root/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash \
    && pyenv install 3.12.7 \
    && pyenv install 3.13.0 \
    && pyenv install 3.14.0  # Assuming 3.14 released; adjust if needed \
    && pyenv global 3.13.0  # Default to 3.13 with free-threading

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

# Run with uvicorn async
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]  # Workers leverage free-threading