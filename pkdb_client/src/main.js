import Vue from 'vue'
import BootstrapVue from 'bootstrap-vue/dist/bootstrap-vue.esm';
import VueRouter from 'vue-router'
import App from './App.vue'
import router from './router'
import VueResource from 'vue-resource';

// Import the styles directly. (Or you could add them via script tags.)
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';

Vue.use(BootstrapVue);


Vue.config.productionTip = false
Vue.use(VueRouter)
Vue.use(VueResource)

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')

//new Vue({
//    el: '#app',
//    router,
//    template: '<App/>',
//    components: { App }
//})