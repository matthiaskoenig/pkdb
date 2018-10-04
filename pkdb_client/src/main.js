import '@babel/polyfill'
import Vue from 'vue';
import './plugins/vuetify'
import Vuex from 'vuex'
import VueRouter from 'vue-router';
import VueResource from 'vue-resource';
import App from './App.vue';
import router from './router';


Vue.config.productionTip = false;
Vue.use(VueRouter);
Vue.use(VueResource);
Vue.use(Vuex);

/** --------------------------------------------------------------
 *  FontAwesome
 *  -------------------------------------------------------------- */
import { library } from '@fortawesome/fontawesome-svg-core';
import { FontAwesomeIcon, FontAwesomeLayers, FontAwesomeLayersText } from '@fortawesome/vue-fontawesome';

import { faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical,
    faFileMedicalAlt, faShareSquare, faChartLine, faChartBar, faInfoCircle, faCode, faLaptopCode, faTablet, faTablets,
    faCube, faCubes, faUserCog, faUserEdit, faEnvelope
} from '@fortawesome/free-solid-svg-icons';
import { faGithub } from '@fortawesome/free-brands-svg-icons';

library.add(faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical, faFileMedicalAlt,
    faShareSquare, faChartLine, faChartBar, faInfoCircle, faGithub, faCode, faLaptopCode, faTablet, faTablets, faCube, faCubes,
    faUserCog, faUserEdit, faEnvelope);

Vue.component('font-awesome-icon', FontAwesomeIcon);
Vue.component('font-awesome-layers', FontAwesomeLayers);
Vue.component('font-awesome-layers-text', FontAwesomeLayersText);


/** --------------------------------------------------------------
 *  Library components
 *  -------------------------------------------------------------- */
import JsonButton from '@/components/lib/JsonButton';
import LinkButton from '@/components/lib/LinkButton';
import Comments from '@/components/lib/Comments';
import Descriptions from '@/components/lib/Descriptions';
import UserAvatar from '@/components/lib/UserAvatar';
import Heading from '@/components/lib/Heading';
import GroupInfo from '@/components/detail/GroupInfo';
import IndividualInfo from '@/components/detail/IndividualInfo';

Vue.component('JsonButton', JsonButton);
Vue.component('LinkButton', LinkButton);
Vue.component('Comments', Comments);
Vue.component('Descriptions', Descriptions);
Vue.component('UserAvatar', UserAvatar);
Vue.component('Heading', Heading);
Vue.component('GroupInfo', GroupInfo);
Vue.component('IndividualInfo', IndividualInfo);


/** --------------------------------------------------------------
 *  Domain
 *  -------------------------------------------------------------- */
//  read from .env.template file
var backend_domain = process.env.VUE_APP_API_BASE;
if (!backend_domain){
    // running in develop, no environment variable set
    console.warn('No PKDB backend set via environment variable: VUE_APP_API_BASE');
    backend_domain = 'http://127.0.0.1:8000';
}
console.log('PKDB backend: ' + backend_domain);

/** --------------------------------------------------------------
 *  Vuex store
 *  -------------------------------------------------------------- */
const store = new Vuex.Store({
    state: {
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

/** --------------------------------------------------------------
 *  App
 *  -------------------------------------------------------------- */
new Vue({
    router,
    // provide the store using the "store" option.
    // this will inject the store instance to all child components.
    store,
    render: h => h(App)
}).$mount('#app');
