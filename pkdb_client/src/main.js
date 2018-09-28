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



// TODO: define the api endpoints once in a store

// domain: "http://127.0.0.1:8000",
// api: "http://127.0.0.1:8000/api/v1"
// domain: "https://pk-db.com",
// api: "https://pk-db.com/api/v1"

Vue.component('font-awesome-icon', FontAwesomeIcon);
Vue.component('font-awesome-layers', FontAwesomeLayers);
Vue.component('font-awesome-layers-text', FontAwesomeLayersText);

Vue.config.productionTip = false;
Vue.use(VueRouter);
Vue.use(VueResource);
Vue.use(VueMaterial);

import axios from 'axios'
// import VueAxios from 'vue-axios'
// import jwt_decode from 'jwt-decode'

/**
 -------------------------------
 Vuex store
 -------------------------------
 */
Vue.use(Vuex);
// Vue.use(VueAxios, axios);


const store = new Vuex.Store({
    state: {
        domain: 'http://127.0.0.1:8000',
        endpoints: {
            api: 'http://127.0.0.1:8000/api/v1',
            obtainAuthToken: 'http://127.0.0.1:8000/api-token-auth/',
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
            localStorage.removeItem('token');
            state.token = null;
        },
    },
    actions:{
        login(context, payload){
            // const payload = {username: username, password: password}
            console.log(payload);

            axios.post(this.state.endpoints.obtainAuthToken, payload)
                .then((response)=>{
                    this.commit('setToken', response.data.token);
                    this.commit(setUsername, payload['username']);
                })
                .catch((error)=>{
                    console.log(error);
                })
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

