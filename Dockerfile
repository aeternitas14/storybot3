FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y \
    google-chrome-stable \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Install Playwright and its dependencies
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p alert_states && \
    mkdir -p /app/__pycache__ && \
    chmod -R 777 /app/__pycache__

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run_bot.py
ENV PORT=443
ENV PYTHONPATH=/app

# Expose port 443 for Fly.io
EXPOSE 443

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:443", "--timeout", "120", "--keep-alive", "5", "run_bot:app"]

