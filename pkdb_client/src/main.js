import Vue from 'vue'
import VueRouter from 'vue-router'
import App from './App.vue'
import router from './router'
import VueResource from 'vue-resource';

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