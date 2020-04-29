# ------------------
# develop.pk-db.com
# ------------------
access_log /var/www/logs/develop.pk-db.com_access.log;
error_log /var/www/logs/develop.pk-db.com_error.log;

server {
    listen 80;
    listen [::]:80;

    server_name develop.pk-db.com;
    return 301 https://develop.pk-db.com$request_uri;
}

server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        server_name develop.pk-db.com;

        ssl_certificate     /etc/letsencrypt/live/pk-db.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/pk-db.com/privkey.pem;
        include /etc/nginx/snippets/ssl.conf;

        client_max_body_size 100m;

        location / {
                # return 200 "ssl on proxy";
                proxy_pass http://172.107.0.1:8888;
                proxy_set_header HOST $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-for $remote_addr;
                proxy_set_header X-Forwarded-Proto https;
                port_in_redirect off;
        }
}