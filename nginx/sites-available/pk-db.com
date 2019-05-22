# local nginx configuration for port forwarding

# https
server {
        listen 80;
        server_name develop.pk-db.com;

        client_max_body_size 100m;
        location / {
                proxy_pass http://127.0.0.1:8888;
                proxy_set_header HOST $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-for $remote_addr;
                proxy_set_header X-Forwarded-Proto https;
                port_in_redirect off;
        }
}
