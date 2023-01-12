# ------------------
# xresearch.pk-db.com
# ------------------
access_log /var/www/logs/xresearch.pk-db.com_access.log;
error_log /var/www/logs/xresearch.pk-db.com_error.log;

server {
    listen 80;
    listen [::]:80;

    server_name xresearch.pk-db.com;

    # letsencrypt webroot authenticator
    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/letsencrypt;
    }

    # https redirects
    location = / {
        return 301 https://xresearch.pk-db.com$request_uri;
     }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name develop.pk-db.com;
    ssl_certificate     /etc/letsencrypt/live/xresearch.pk-db.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xresearch.pk-db.com/privkey.pem;

    return 301 https://xresearch.pk-db.com$request_uri;
}

server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        server_name xresearch.pk-db.com;

        ssl_certificate     /etc/letsencrypt/live/xresearch.pk-db.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/xresearch.pk-db.com/privkey.pem;
        include /etc/nginx/snippets/ssl.conf;

        client_max_body_size 100m;
        proxy_connect_timeout       900;
        proxy_send_timeout          900;
        proxy_read_timeout          900;
        send_timeout                900;


        location / {
                # return 200 "ssl on proxy";
                proxy_pass http://192.168.0.60:8888;
                proxy_set_header HOST $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-for $remote_addr;
                proxy_set_header X-Forwarded-Proto https;
                port_in_redirect off;
        }
}