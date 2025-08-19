FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Default port
ENV PORT=9090

# Run Wattson
CMD ["python", "main.py"]
