services:
  app:
    image: {{ app_image }}
    container_name: app
    environment:
      - MODE={{ mode }}
      - APP_PORT={{ app_port }}
      - APP_VERSION={{ version }}
    networks:
      - {{ network_name }}
    restart: unless-stopped
    expose:
      - "{{ app_port }}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{{ app_port }}/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    volumes:
      - logs:/app/logs

  nginx:
    image: {{ nginx_image }}
    container_name: nginx
    ports:
      - "{{ nginx_port }}:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    networks:
      - {{ network_name }}
    restart: unless-stopped

  opa:
    image: openpolicyagent/opa:latest
    container_name: opa
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "/policies"
    volumes:
      - ./policies:/policies:ro
    networks:
      - {{ network_name }}
    restart: unless-stopped
    ports:
      - "8181:8181"

networks:
  {{ network_name }}:
    driver: {{ network_driver }}

volumes:
  logs:
