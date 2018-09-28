# pkdb-client

# Installation
## node.js
https://tecadmin.net/install-latest-nodejs-npm-on-ubuntu/
```
# node.js > 8.x
sudo apt-get install curl python-software-properties
curl -sL https://deb.nodesource.com/setup_10.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v 
```

## vue client
https://cli.vuejs.org/
```
# vue/cli > 3.0
sudo npm install -g @vue/cli
sudo npm install vue-router
sudo npm install axios --save 
sudo npm install bootstrap-vue bootstrap --save
sudo npm install vue-tables-2

sudo npm i --save @fortawesome/fontawesome-svg-core \
  npm i --save @fortawesome/free-solid-svg-icons \
  npm i --save @fortawesome/vue-fontawesome
sudo npm i --save @fortawesome/free-regular-svg-icons
sudo npm i --save @fortawesome/free-brands-svg-icons
```

## vue project
### Setup
```
cd pkdb-client
npm install
```

### Compile and hot-reloads for development
```
npm run serve
```

### Compile and minifies for production
https://cli.vuejs.org/guide/deployment.html
```
npm run build
```

### Lints and fixes files
```
npm run lint
```

# FontAwesome
https://fontawesome.com/how-to-use/on-the-web/using-with/vuejs
https://blog.logrocket.com/full-guide-to-using-font-awesome-icons-in-vue-js-apps-5574c74d9b2d