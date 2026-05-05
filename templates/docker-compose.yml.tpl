version: "3.8"

services:

  app:

    image: {{ services.image }}

    environment:

      - MODE={{ services.mode }}

      - APP_VERSION={{ services.version }}

      - APP_PORT={{ services.port }}

    networks:

      - {{ network.name }}

    restart: always

    healthcheck:

      test: ["CMD", "curl", "-f", "http://localhost:{{ services.port }}/healthz"]

      interval: 10s

      retries: 5

  nginx:

    image: {{ nginx.image }}

    ports:

      - "{{ nginx.port }}:80"

    volumes:

      - ./nginx.conf:/etc/nginx/nginx.conf:ro

    depends_on:

      - app

    networks:

      - {{ network.name }}

networks:

  {{ network.name }}:

    driver: {{ network.driver_type }}

volumes:

  logs: