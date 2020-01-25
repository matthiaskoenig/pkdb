import Vue from 'vue'
import Vuex from 'vuex'
import VuexPersist from 'vuex-persist';

Vue.use(Vuex);
Vue.config.devtools = true;


/** --------------------------------------------------------------
 *  Domain
 *  -------------------------------------------------------------- */
//  read from .env.template file
const backend_domain = process.env.VUE_APP_API_BASE;


if (!backend_domain) {
    // running in develop, no environment variable set
    console.error('No PKDB backend set via environment variable: VUE_APP_API_BASE');
}
console.log('PKDB backend: ' + backend_domain);

const vuexLocalStorage = new VuexPersist({
    key: 'vuex', // The key to store the state on in the storage provider.
    storage: window.localStorage, // or window.sessionStorage or localForage
    // Function that passes the state and returns the state with only the objects you want to store.
    // reducer: state => state,
    // Function that passes a mutation and lets you decide if it should update the state in localStorage.
    // filter: mutation => (true)
    reducer: state => ({
        token: state.token,
        user: state.user,

        // keepThisModuleToo: state.keepThisModuleToo
        // getRidOfThisModule: state.getRidOfThisModule (No one likes it.)
    })
});

/** --------------------------------------------------------------
 *  Vuex store
 *  -------------------------------------------------------------- */
export default new Vuex.Store({
    plugins: [vuexLocalStorage.plugin],
    state: {
        django_domain: backend_domain,

        endpoints: {
            api: backend_domain + '/api/v1/',
            obtainAuthToken: backend_domain + '/api-token-auth/',
            // FIXME: are these endpoints used?
            register: backend_domain + '/accounts/register/',
            verify: backend_domain + '/accounts/verify-email/',
            request_password_reset: backend_domain + '/accounts/request-password-reset/',
            password_reset: backend_domain + '/accounts/reset-password/',
        },

        username: localStorage.getItem('username'),
        token: localStorage.getItem('token'),
    },
    mutations: {
        setToken(state, token) {
            localStorage.setItem('token', token);
            state.token = token;
        },
        clearToken(state) {
            localStorage.removeItem('token');
            state.token = null;
        },
        setUsername(state, username) {
            localStorage.setItem('username', username);
            state.username = username;
        },
        clearUsername(state) {
            localStorage.removeItem('username');
            state.username = null;
        },
    },
    actions: {
        login(context, payload) {
            // const payload = {username: username, token: token}
            this.commit('setToken', payload.token);
            this.commit('setUsername', payload.username);
        },
        logout() {
            this.commit('clearToken');
            this.commit('clearUsername');
        },
    }
})