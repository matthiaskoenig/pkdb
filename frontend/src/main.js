import '@fortawesome/fontawesome-free/css/all.css'

import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'

import VueAuthImage from 'vue-auth-image';
import TextHighlight from 'vue-text-highlight';
import VueResource from 'vue-resource';

import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios';


/** --------------------------------------------------------------
 *  Library components
 *  -------------------------------------------------------------- */
import JsonButton from './components/lib/JsonButton';
import LinkButton from './components/lib/LinkButton';
import FileButton from './components/lib/FileButton';
import ExportFormatButton from './components/lib/ExportFormatButton';
import Comments from './components/lib/Comments';
import Descriptions from './components/lib/Descriptions';
import Annotations from './components/lib/Annotations';
import UserAvatar from './components/lib/UserAvatar';
import UserRating from './components/lib/UserRating';
import Heading from './components/lib/Heading';
import GetData from './components/api/GetData';
import GetPaginatedData from './components/api/GetPaginatedData';
import SubstanceChip from './components/detail/SubstanceChip';
import FileChip from './components/detail/FileChip';
import KeywordChip from './components/detail/KeywordChip';
import InterventionChip from './components/detail/InterventionChip';
import Footer from './components/Footer';


Vue.component('Footer', Footer);
Vue.component('ExportFormatButton', ExportFormatButton);
Vue.component('JsonButton', JsonButton);
Vue.component('LinkButton', LinkButton);
Vue.component('FileButton', FileButton);
Vue.component('Comments', Comments);
Vue.component('Descriptions', Descriptions);
Vue.component('Annotations', Annotations);
Vue.component('UserAvatar', UserAvatar);
Vue.component('UserRating', UserRating);
Vue.component('Heading', Heading);
Vue.component('GetData', GetData);
Vue.component('GetPaginatedData', GetPaginatedData);
Vue.component('SubstanceChip', SubstanceChip);
Vue.component('FileChip', FileChip);
Vue.component('KeywordChip', KeywordChip);
Vue.component('InterventionChip', InterventionChip);
Vue.component('text-highlight', TextHighlight);


Vue.config.productionTip = false;

const opts = {
    icons: {
        iconfont: 'fa'
    }
};
Vue.use(Vuetify)
Vue.use(VueAuthImage);
Vue.use(VueResource);

new Vue({
    router,
    store,
    vuetify: new Vuetify(opts),
    render: h => h(App)
}).$mount('#app');


axios.interceptors.request.use(function (config) {
    const token = store.state.token;
    if (token) {
        axios.defaults.headers.common['Authorization'] = 'Token ' + localStorage.getItem('token')
    }
    return config;
}, function (err) {
    return Promise.reject(err);
});