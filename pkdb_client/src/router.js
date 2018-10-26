import Vue from 'vue';
import Router from 'vue-router';

/* Home */
import Home from './components/Home';

/* TableViews */
import Studies from './components/Studies';
import Groups from './components/Groups';
import Individuals from './components/Individuals';
import Interventions from './components/Interventions';
import Outputs from './components/Outputs';
import Timecourses from './components/Timecourses';
import References from './components/References';

/* DetailViews */
import Study from './components/Study';
import Group from './components/Group';
import Individual from './components/Individual';
import Intervention from './components/Intervention';
import Output from './components/Output';
import Timecourse from './components/Timecourse';
import Reference from './components/Reference';

/* About */
import Curation from './components/Curation';
import About from './components/About';

/* Account */
import Account from './components/auth/Account';


Vue.use(Router);

export default new Router({
  // mode: 'history',
  // base: process.env.VUE_APP_API_BASE,
  routes: [
      {
          path: '/',
          name: 'Home',
          component: Home
      },
      {
          path: '/studies',
          name: 'Studies',
          component: Studies
      },
      {
          path: '/groups',
          name: 'Groups',
          component: Groups
      },
      {
          path: '/individuals',
          name: 'Individuals',
          component: Individuals
      },
      {
          path: '/interventions',
          name: 'Interventions',
          component: Interventions
      },
      {
          path: '/outputs',
          name: 'Outputs',
          component: Outputs
      },
      {
          path: '/timecourses',
          name: 'Timecourses',
          component: Timecourses
      },
      {
          path: '/references',
          name: 'References',
          component: References
      },
      {
          path: '/about',
          name: 'About',
          component: About
      },
      {
          path: '/curation',
          name: 'Curation',
          component: Curation
      },
      {
          path: '/account',
          name: 'Account',
          component: Account
      },

      {
          path:"/studies/:id",
          name:"Study",
          component:Study,
          props: true
      },
      {
          path:"/groups/:id",
          name:"Group",
          component:Group,
          props: true
      },
      {
          path:"/individuals/:id",
          name:"Individual",
          component:Individual,
          props: true
      },
      {
          path:"/interventions/:id",
          name:"Intervention",
          component:Intervention,
          props: true
      },
      {
          path: "/outputs/:id",
          name: "Output",
          component: Output,
          props: true
      },
      {
          path: "/timecourses/:id",
          name: "Timecourse",
          component: Timecourse,
          props: true
      },
      {
          path: "/references/:id",
          name: "Reference",
          component: Reference,
          props: true
      },
  ],
    scrollBehavior (to, from, savedPosition) {
        return { x: 0, y: 0 }
    }

})
