# build stage
FROM node:lts-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 8080
CMD npm run serve

# RUN npm run build
# RUN mkdir -p /usr/share/nginx/html
# COPY --from=build-stage /app/dist /usr/share/nginx/html

