import Vue from 'vue'
import BootstrapVue from 'bootstrap-vue/dist/bootstrap-vue.esm';
import VueRouter from 'vue-router'
import App from './App.vue'
import router from './router'
import VueResource from 'vue-resource';

// Import the styles directly. (Or you could add them via script tags.)
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';
import ClientTable from 'vue-tables-2';

import { library } from '@fortawesome/fontawesome-svg-core'
import { faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical,
    faFileMedicalAlt, faShareSquare} from '@fortawesome/free-solid-svg-icons'
import {  } from '@fortawesome/free-regular-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'

import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

library.add(faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faGithub, faProcedures, faFileMedical, faFileMedicalAlt, faShareSquare)

Vue.component('font-awesome-icon', FontAwesomeIcon)


Vue.use(BootstrapVue);

Vue.config.productionTip = false
Vue.use(VueRouter)
Vue.use(VueResource)
Vue.use(ClientTable, {}, false, 'bootstrap3', 'default');


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