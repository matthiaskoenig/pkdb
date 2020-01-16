import '@babel/polyfill'
import Vue from 'vue'
import './plugins/vuetify'
import './plugins/vuetify'

import VueResource from 'vue-resource';
import App from './App.vue'
import router from './router'
import store from './store'

import './assets/pkdb.css';
import './stylus/main.styl'

Vue.use(VueResource);
import VueAuthImage from 'vue-auth-image';

Vue.use(VueAuthImage);
/** --------------------------------------------------------------
 *  FontAwesome
 *  -------------------------------------------------------------- */
import {library} from '@fortawesome/fontawesome-svg-core';
import {FontAwesomeIcon, FontAwesomeLayers, FontAwesomeLayersText} from '@fortawesome/vue-fontawesome';

import {
    faCoffee,
    faFileAlt,
    faUser,
    faUsers,
    faFemale,
    faMale,
    faCapsules,
    faProcedures,
    faFileMedical,
    faFileMedicalAlt,
    faShareSquare,
    faChartLine,
    faChartBar,
    faInfoCircle,
    faCode,
    faLaptopCode,
    faTablet,
    faTablets,
    faCube,
    faCubes,
    faUserCog,
    faUserEdit,
    faEnvelope,
    faTicketAlt,
    faCheckCircle,
    faTimesCircle,
    faBookReader,
    faTrashAlt,
    faCommentAlt,
    faAlignLeft,
    faFileExcel,
    faFileCsv,
    faFilePdf
} from '@fortawesome/free-solid-svg-icons';
import {faGithub} from '@fortawesome/free-brands-svg-icons';

library.add(faCoffee, faFileAlt, faUser, faUsers, faFemale, faMale, faCapsules, faProcedures, faFileMedical, faFileMedicalAlt,
    faShareSquare, faChartLine, faChartBar, faInfoCircle, faGithub, faCode, faLaptopCode, faTablet, faTablets, faCube, faCubes,
    faUserCog, faUserEdit, faEnvelope, faTicketAlt, faCheckCircle, faTimesCircle, faBookReader, faTrashAlt, faCommentAlt,
    faAlignLeft, faFileExcel, faFileCsv, faFilePdf);

Vue.component('font-awesome-icon', FontAwesomeIcon);
Vue.component('font-awesome-layers', FontAwesomeLayers);
Vue.component('font-awesome-layers-text', FontAwesomeLayersText);


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
import HeadingToolbar from './components/lib/HeadingToolbar';

import GetData from './components/api/GetData';
import GetPaginatedData from './components/api/GetPaginatedData';

// chips
import SubstanceChip from './components/detail/SubstanceChip';
import FileChip from './components/detail/FileChip';
import KeywordChip from './components/detail/KeywordChip';
import InterventionChip from './components/detail/InterventionChip';
import Footer from './components/Footer';

import TextHighlight from 'vue-text-highlight';
import axios from 'axios';

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
Vue.component('HeadingToolbar', HeadingToolbar);

Vue.component('GetData', GetData);
Vue.component('GetPaginatedData', GetPaginatedData);

Vue.component('SubstanceChip', SubstanceChip);
Vue.component('FileChip', FileChip);
Vue.component('KeywordChip', KeywordChip);
Vue.component('InterventionChip', InterventionChip);

Vue.component('text-highlight', TextHighlight);

//import { lookup_icon} from "./icons";


Vue.config.productionTip = false;


new Vue({
    router,
    store,
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