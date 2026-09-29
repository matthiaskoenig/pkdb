# ------------------
# beta.pk-db.com
# ------------------
# TLS edge proxy on the gateway host. It forwards all traffic to the PK-DB
# application host, where nginx/pkdb.conf serves the frontend and the API.
# Install as /etc/nginx/sites-available/beta.pk-db.com and nginx/ssl.conf as
# /etc/nginx/snippets/ssl.conf; see docs/deployment.md.

upstream pkdb_beta {
    server 192.168.0.176:18083;
    keepalive 16;
}

server {
    listen 80;
    listen [::]:80;

    server_name beta.pk-db.com;
    access_log /var/www/logs/beta.pk-db.com_access.log;
    error_log /var/www/logs/beta.pk-db.com_error.log;

    # letsencrypt webroot authenticator
    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/letsencrypt;
    }

    # https redirects
    location / {
        return 301 https://beta.pk-db.com$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name beta.pk-db.com;
    access_log /var/www/logs/beta.pk-db.com_access.log;
    error_log /var/www/logs/beta.pk-db.com_error.log;

    ssl_certificate     /etc/letsencrypt/live/beta.pk-db.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beta.pk-db.com/privkey.pem;
    include /etc/nginx/snippets/ssl.conf;

    # Study uploads and dataset exports can be large and slow.
    client_max_body_size 100m;
    proxy_connect_timeout 900;
    proxy_send_timeout    900;
    proxy_read_timeout    900;
    send_timeout          900;

    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    # Replace any client-supplied chain; the application host trusts this value.
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_redirect off;

    # MCP responses are streamed.
    location /mcp/ {
        proxy_pass http://pkdb_beta;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://pkdb_beta;
    }
}
