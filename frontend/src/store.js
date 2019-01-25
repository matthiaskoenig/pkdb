import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex);


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
export default new Vuex.Store({
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
})