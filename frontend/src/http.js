/** Same-origin browser sessions. No bearer credentials are retained by the UI. */
import axios from 'axios';

export const apiBase = (process.env.VUE_APP_API_BASE || '').replace(/\/$/, '');
let csrfToken = null;
let csrfRequest = null;

export function clearCsrf() { csrfToken = null; }
export function errorMessage(error) {
    const data = error.response && error.response.data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.detail)) return data.detail.map(item => item.msg).join('; ');
    if (data && data.non_field_errors) return data.non_field_errors.join(' ');
    return 'The request could not be completed. Please try again.';
}
export function configureHttp(store) {
    // Remove credentials persisted by older versions, including Vuex copies.
    ['token', 'username', 'vuex'].forEach(key => window.localStorage.removeItem(key));
    axios.interceptors.request.use(async config => {
        const target = new URL(config.url, window.location.href);
        const backend = new URL(apiBase || '/', window.location.href);
        if (target.origin !== backend.origin) return config;
        config.withCredentials = true;
        if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
            if (!csrfToken) {
                if (!csrfRequest) csrfRequest = axios.get(apiBase + '/api/v1/auth/csrf')
                    .then(response => { csrfToken = response.data.csrf_token; })
                    .finally(() => { csrfRequest = null; });
                await csrfRequest;
            }
            config.headers = Object.assign({}, config.headers, {'X-CSRF-Token': csrfToken});
        }
        return config;
    });
    axios.interceptors.response.use(response => response, error => {
        if (error.response && error.response.status === 401) store.commit('setProfile', null);
        if (error.response && error.response.data && error.response.data.code === 'csrf_failed') clearCsrf();
        return Promise.reject(error);
    });
}
