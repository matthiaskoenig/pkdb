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
```
# vue create pkdb-client
cd pkdb-client
npm run serve 
```

## deploying
https://cli.vuejs.org/guide/deployment.html
```
npm run build
```

## Project setup
```
npm install
```

### Compiles and hot-reloads for development
```
npm run serve
```

### Compiles and minifies for production
```
npm run build
```

### Lints and fixes files
```
npm run lint
```
# Bootstrap
https://alligator.io/vuejs/using-bootstrap4/  
https://bootstrap-vue.js.org/docs/

vue-bootstrap’s current roster of components includes most of the interactive Bootstrap 4 components: Alert, Badge, Breadcrumb, Button, Button group, Card, Collapse, Dropdown, The Usual Form Elements, Jumbotron, List group, Modal, Nav, Navbar, Pagination, Popover, Progress, Table and Tabs

# FontAwesome
https://fontawesome.com/how-to-use/on-the-web/using-with/vuejs
https://blog.logrocket.com/full-guide-to-using-font-awesome-icons-in-vue-js-apps-5574c74d9b2d