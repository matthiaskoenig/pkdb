import '@babel/polyfill'
import Vue from 'vue'
import './plugins/vuetify'

import VueResource from 'vue-resource';
import App from './App.vue'
import router from './router'
import store from './store'

import './assets/pkdb.css';

Vue.use(VueResource);

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
import JsonButton from './components/lib/JsonButton';
import LinkButton from './components/lib/LinkButton';
import Comments from './components/lib/Comments';
import Descriptions from './components/lib/Descriptions';
import Annotations from './components/lib/Annotations';

import UserAvatar from './components/lib/UserAvatar';
import Heading from './components/lib/Heading';
import GroupInfo from './components/detail/GroupInfo';
import IndividualInfo from './components/detail/IndividualInfo';
import GetData from './components/api/GetData';
import GetPaginatedData from './components/api/GetPaginatedData';

Vue.component('JsonButton', JsonButton);
Vue.component('LinkButton', LinkButton);
Vue.component('Comments', Comments);
Vue.component('Descriptions', Descriptions);
Vue.component('Annotations', Annotations);

Vue.component('UserAvatar', UserAvatar);
Vue.component('Heading', Heading);
Vue.component('GroupInfo', GroupInfo);
Vue.component('IndividualInfo', IndividualInfo);

Vue.component('GetData', GetData);
Vue.component('GetPaginatedData', GetPaginatedData);


Vue.config.productionTip = false;


new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');
