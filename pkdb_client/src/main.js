import Vue from 'vue';
import VueRouter from 'vue-router';
import App from './App.vue';
import router from './router';
import VueResource from 'vue-resource';
import VueMaterial from 'vue-material';

import 'vue-material/dist/vue-material.min.css';
import 'vue-material/dist/theme/default.css'

import { library } from '@fortawesome/fontawesome-svg-core';
import { faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical,
    faFileMedicalAlt, faShareSquare, faChartLine, faChartBar, faInfoCircle, faCode, faLaptopCode, faTablet, faTablets,
    faCube, faCubes, faUserCog, faUserEdit
} from '@fortawesome/free-solid-svg-icons';
import { faGithub } from '@fortawesome/free-brands-svg-icons';
import { FontAwesomeIcon, FontAwesomeLayers, FontAwesomeLayersText } from '@fortawesome/vue-fontawesome';
library.add(faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical, faFileMedicalAlt,
    faShareSquare, faChartLine, faChartBar, faInfoCircle, faGithub, faCode, faLaptopCode, faTablet, faTablets, faCube, faCubes,
    faUserCog, faUserEdit);

import Vuex from 'vuex'

Vue.component('font-awesome-icon', FontAwesomeIcon);
Vue.component('font-awesome-layers', FontAwesomeLayers);
Vue.component('font-awesome-layers-text', FontAwesomeLayersText);

Vue.config.productionTip = false;
Vue.use(VueRouter);
Vue.use(VueResource);
Vue.use(VueMaterial);


// import VueAxios from 'vue-axios'
// import jwt_decode from 'jwt-decode'

/**
 -------------------------------
 Vuex store
 -------------------------------
 */
Vue.use(Vuex);
// Vue.use(VueAxios, axios);

const backend_domain = 'http://127.0.0.1:8000';
// const backend_domain = 'https://pk-db.com',
// const backend_domain = 'https://develop.pk-db.com',

const store = new Vuex.Store({
    state: {
        // vue_domain is frontend server domain!, django_domain is backend server domain!
        django_domain: backend_domain,

        endpoints: {
            api: backend_domain + '/api/v1',
            obtainAuthToken: backend_domain + '/api-token-auth/'
        },

        username: localStorage.getItem('username'),
        token: localStorage.getItem('token'),

    },
    mutations: {
        setToken(state, token){
            localStorage.setItem('token', token);
            state.token = token;
        },
        clearToken(state){
            localStorage.removeItem('token');
            state.token = null;
        },
        setUsername(state, username){
            localStorage.setItem('username', username);
            state.username = username;
        },
        clearUsername(state){
            localStorage.removeItem('username');
            state.username = null;
        },
    },
    actions:{
        login(context, payload){
            // const payload = {username: username, token: token}
            this.commit('setToken', payload.token);
            this.commit('setUsername', payload.username);
        },
        logout(context){
            this.commit('clearToken');
            this.commit('clearUsername');
        },
    }
});

new Vue({
    router,
    // provide the store using the "store" option.
    // this will inject the store instance to all child components.
    store,
    render: h => h(App)
}).$mount('#app');

