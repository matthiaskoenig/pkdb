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

// Initial search values
const initial_queries = {
    //studies
    studies__sid__in: [],

    // interventions
    interventions__substance_sid__in: [],
    interventions__route_sid__in: [],
    interventions__measurement_type_sid__in: [],
    interventions__application_sid__in: [],
    interventions__form_sid__in: [],

    // outputs
    outputs__substance_sid__in: [],
    outputs__tissue_sid__in: [],
    outputs__measurement_type_sid__in: [],
    outputs__method_sid__in: [],
}
const initial_queries_users =
    {
    studies__creator__in: [],
    studies__curators__in: [],
    }
const initial_subjects_boolean =
    {
        groups_query: true,
        individuals_query: true,
    }

const initial_subjects_queries = {
    choice_sid__in: [],
    measurement_type_sid__in: [],
}

/** --------------------------------------------------------------
 *  Vuex store
 *  -------------------------------------------------------------- */
export default new Vuex.Store({
    plugins: [vuexLocalStorage.plugin],
    state: {

        //for search detail display
        detail_display: false,
        detail_info: {},
        show_type: "help",

        // for data detail display
        data_info: {},
        data_info_type: "study",

        // search queries
        queries: initial_queries,
        subjects_boolean: initial_subjects_boolean,
        subjects_queries: initial_subjects_queries,
        queries_users: initial_queries_users,

        // search results (synchronization between search & results)
        results: {
            studies: {"hash": "", "count": 0},
            interventions: {"hash": "", "count": 0},
            groups: {"hash": "", "count": 0},
            individuals: {"hash": "", "count": 0},
            outputs: {"hash": "", "count": 0},
            timecourses: {"hash": "", "count": 0},
        },

        // global highlighting
        highlight:  "",

        // API
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
        resetQuery(state){
            Object.assign(state.queries,  initial_queries)
            Object.assign(state.subjects_boolean,  initial_subjects_boolean)
            Object.assign(state.subjects_queries,  initial_subjects_queries)
            Object.assign(state.queries_users,  initial_queries_users)
        },
        // update search
        updateQuery (state, obj) {
            state[obj.query_type][obj.key] = obj.value
        },

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
        updateQueryAction (context, obj) {
            this.commit('updateQuery', obj);

        }

    }
})