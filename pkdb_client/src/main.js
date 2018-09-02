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
    faFileMedicalAlt, faShareSquare, faChartLine, faChartBar, faInfoCircle, faCode, faLaptopCode, faTablet, faTablets
} from '@fortawesome/free-solid-svg-icons'

import { faGithub, faGithubAlt, faGit } from '@fortawesome/free-brands-svg-icons'



import { FontAwesomeIcon, FontAwesomeLayers, FontAwesomeLayersText } from '@fortawesome/vue-fontawesome'

library.add(faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical, faFileMedicalAlt,
    faShareSquare, faChartLine, faChartBar, faInfoCircle, faGithub, faCode, faLaptopCode, faTablet, faTablets)

Vue.component('font-awesome-icon', FontAwesomeIcon)
Vue.component('font-awesome-layers', FontAwesomeLayers)
Vue.component('font-awesome-layers-text', FontAwesomeLayersText)


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