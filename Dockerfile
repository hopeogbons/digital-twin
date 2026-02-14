# Stage 1: Build Next.js static export
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# Stage 2: Python backend + static files
FROM python:3.12-slim
WORKDIR /app/backend

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source and data
COPY backend/ ./

# Copy built frontend into static directory
COPY --from=frontend-build /app/frontend/out ./static

# Create persistent directories
RUN mkdir -p /data/memory /data/chroma_db

# HF Spaces requires UID 1000
RUN useradd -m -u 1000 user
RUN chown -R user:user /app /data
USER user

EXPOSE 7860

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
