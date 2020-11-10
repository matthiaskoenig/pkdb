# ------------------
# PK-DB
# ------------------
access_log /var/www/logs/pk-db.com_access.log;
error_log /var/www/logs/pk-db.com_error.log;

server {
    listen 80;
    listen [::]:80;

    server_name pk-db.com pk-db.de www.pk-db.com www.pk-db.de;

    # letsencrypt webroot authenticator
    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/letsencrypt;
    }

    # https redirects
    location = / {
        return 301 https://pk-db.com$request_uri;
     }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name www.pk-db.com pk-db.de www.pk-db.de;
    ssl_certificate     /etc/letsencrypt/live/pk-db.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pk-db.com/privkey.pem;

    return 301 https://pk-db.com$request_uri;
}

server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        server_name pk-db.com;

        ssl_certificate     /etc/letsencrypt/live/pk-db.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/pk-db.com/privkey.pem;
        include /etc/nginx/snippets/ssl.conf;

        client_max_body_size 100m;
        proxy_connect_timeout       600;
        proxy_send_timeout          600;
        proxy_read_timeout          600;
        send_timeout                600;

        location / {
                # return 200 "ssl on proxy";
                proxy_pass http://192.168.0.184:8888;
                proxy_set_header HOST $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-for $remote_addr;
                proxy_set_header X-Forwarded-Proto https;
                port_in_redirect off;
        }
}
