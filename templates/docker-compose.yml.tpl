version: "3.8"

services:

  app:

    build: ./app

    container_name: app

    networks:

      - {{ network.name }}

  nginx:

    image: {{ nginx.image }}

    ports:

      - "{{ nginx.port }}:80"

    volumes:

      - ./nginx.conf:/etc/nginx/nginx.conf

    depends_on:

      - app

    networks:

      - {{ network.name }}

  opa:

    image: openpolicyagent/opa:latest

    command: ["run", "--server", "/policies"]

    volumes:

      - ./policies:/policies

    networks:

      - {{ network.name }}

networks:

  {{ network.name }}:

    driver: {{ network.driver_type }}