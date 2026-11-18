# Runs the web app in one container, for example on Render's free plan.
# With no API key it starts in the offline demo. Visitors can bring their own key.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Run as a normal user, not as root
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/home/user/app/models
WORKDIR /home/user/app

# Install first, so code changes do not reinstall every package
COPY --chown=user requirements.txt setup.sh .env.example ./
RUN bash setup.sh

COPY --chown=user . .

# Build the search index, download the reranker and build the demo database now,
# so the models live inside the image and the first visitor does not wait
RUN .venv/bin/python main.py index

# The host tells the app its port in PORT. Without one it uses 7860.
EXPOSE 7860
CMD .venv/bin/python main.py serve --host 0.0.0.0 --port ${PORT:-7860}
